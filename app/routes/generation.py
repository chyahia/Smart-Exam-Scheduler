from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
import threading
import queue
import time
from collections import defaultdict
from app.database import get_db_connection
from app.services.algorithms import (
    _run_initial_subject_placement, run_subject_optimization_phase, clean_string_for_matching, # <-- أضفنا استدعاء الدوال هنا
    complete_schedule_with_guards, run_unified_lns_optimizer,
    run_large_neighborhood_search, run_variable_neighborhood_search, run_tabu_search
)
import uuid
import random

def calculate_balanced_distribution(total_large, total_other, num_profs, w_large, w_other):
    """
    تحسب التوزيع المثالي (العادل) للحصص بناءً على عدد الأساتذة وعدد القاعات ومعامل العبء.
    """
    if num_profs == 0: return []
    total_workload = (total_large * w_large) + (total_other * w_other)
    target_workload = total_workload / num_profs
    
    distribution = []
    base_large = total_large // num_profs
    remainder_large = total_large % num_profs
    
    for i in range(num_profs):
        large_count = base_large + 1 if i < remainder_large else base_large
        rem_workload = target_workload - (large_count * w_large)
        other_count = max(0, round(rem_workload / w_other))
        distribution.append({
            'large': large_count, 
            'other': other_count, 
            'total_workload': (large_count * w_large) + (other_count * w_other)
        })
    return distribution

def generate_balance_report(prof_stats, prof_targets):
    """
    تقارن التوزيع الفعلي في الجدول مع التوزيع المستهدف وتولد تقرير الانحراف والنسبة المئوية.
    """
    patterns = defaultdict(int)
    for stats in prof_stats.values():
        patterns[(stats['large'], stats['other'])] += 1
        
    target_patterns = defaultdict(int)
    if prof_targets:
        for target in prof_targets.values():
            target_patterns[(target['large'], target['other'])] += 1

    report_details = []
    all_keys = sorted(list(set(patterns.keys()) | set(target_patterns.keys())))
    total_deviation = 0
    
    for key in all_keys:
        actual = patterns.get(key, 0)
        target = target_patterns.get(key, 0)
        deviation = actual - target
        total_deviation += abs(deviation)
        report_details.append({
            'pattern': f"{key[0]} كبيرة + {key[1]} أخرى", 
            'target_count': target, 
            'actual_count': actual, 
            'deviation': deviation
        })

    # حساب مؤشر التوازن كنسبة مئوية (تبدأ من 100 وتنقص كلما زاد الانحراف)
    balance_score = max(0, 100 - (total_deviation * 2))
    return {'details': report_details, 'balance_score': round(balance_score)}


generation_bp = Blueprint('generation', __name__)

# الطوابير والخيوط العالمية للإدارة
log_queue = queue.Queue()
stop_event = threading.Event()
generation_thread = None

@generation_bp.route('/api/stream-logs')
def stream_logs():
    def generate():
        while True:
            try:
                message = log_queue.get(timeout=2)
                if message.startswith("DONE:"):
                    yield f"data: {message}\n\n"
                    break
                yield f"data: {message}\n\n"
            except queue.Empty:
                # إرسال نبضة لمنع المتصفح من إغلاق الاتصال
                yield ": keep-alive\n\n"
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@generation_bp.route('/api/stop-generation', methods=['POST'])
def stop_algorithm():
    stop_event.set()
    log_queue.put("... تم إرسال إشارة إيقاف الخوارزمية، جاري إنهاء العمليات ...")
    return jsonify({'success': True})

@generation_bp.route('/api/generate-schedule', methods=['POST'])
def generate_schedule():
    global stop_event, generation_thread
    data = request.json
    
    # 🌟 التعديل هنا: استقبال مصفوفة الخوارزميات من الواجهة 🌟
    algorithm_choices = data.get('algorithms', ['lns']) 
    algo_params = data.get('params', {})
    
    stop_event.clear()
    with log_queue.mutex: log_queue.queue.clear()
        
    # 🌟 تمرير المصفوفة للدالة التي تعمل في الخلفية 🌟
    generation_thread = threading.Thread(target=_background_generation, args=(algorithm_choices, algo_params))
    generation_thread.start()
    
    return jsonify({'success': True, 'message': 'بدأت عملية التوليد المتسلسل.'})

def _background_generation(algorithm_choices, algo_params):
    try:
        log_queue.put("جاري جلب البيانات من قاعدة البيانات وتنسيقها...")
        conn = get_db_connection()
        
        row_main = conn.execute("SELECT value FROM settings WHERE key = 'main_settings'").fetchone()
        main_settings = json.loads(row_main['value']) if row_main else {}

        # 💡 حقن إعدادات الخوارزميات المأخوذة من الواجهة لتتجاوز الافتراضية
        if algo_params:
            main_settings['lnsUnifiedIterations'] = int(algo_params.get('unifiedIter', 300))
            main_settings['lnsUnifiedDestroyFraction'] = float(algo_params.get('unifiedDestroy', 0.2))
            main_settings['lnsIterations'] = int(algo_params.get('lnsIter', 100))
            main_settings['lnsDestroyFraction'] = float(algo_params.get('lnsDestroy', 0.2))
            main_settings['vnsIterations'] = int(algo_params.get('vnsIter', 100))
            main_settings['vnsMaxK'] = int(algo_params.get('vnsK', 25))
            main_settings['tabuIterations'] = int(algo_params.get('tabuIter', 200))
            main_settings['tabuNeighborhoodSize'] = int(algo_params.get('tabuSize', 100))
            main_settings['tabuTenure'] = int(algo_params.get('tabuTenure', 20))
        
        row_sched = conn.execute("SELECT value FROM settings WHERE key = 'exam_schedule'").fetchone()
        exam_schedule = json.loads(row_sched['value']) if row_sched else {}
        
        all_professors = [r['name'] for r in conn.execute("SELECT name FROM professors").fetchall()]
        all_subjects_list = [dict(r) for r in conn.execute("SELECT s.id as subj_id, s.name as subj_name, l.name as level_name FROM subjects s JOIN levels l ON s.level_id = l.id").fetchall()]
        all_levels_list = [r['name'] for r in conn.execute("SELECT name FROM levels").fetchall()]
        all_halls_list = [dict(r) for r in conn.execute("SELECT id, name, type FROM halls").fetchall()]
        
        assign_rows = conn.execute('''
            SELECT p.name as prof_name, s.name as subj_name, l.name as level_name 
            FROM professor_subject ps JOIN professors p ON ps.professor_id = p.id JOIN subjects s ON ps.subject_id = s.id JOIN levels l ON s.level_id = l.id
        ''').fetchall()
        
        assignments = defaultdict(list)
        for r in assign_rows: assignments[r['prof_name']].append({'subj_name': r['subj_name'], 'level_name': r['level_name']})
            
        lh_rows = conn.execute('''
            SELECT l.name as level_name, h.id as hall_id
            FROM level_halls lh JOIN levels l ON lh.level_id = l.id JOIN halls h ON lh.hall_id = h.id
        ''').fetchall()
        level_halls = [dict(r) for r in lh_rows]
        conn.close()

        if not exam_schedule:
            log_queue.put("DONE:{\"success\": false, \"message\": \"الرجاء إعداد جدول الامتحانات في المرحلة 4 أولاً.\"}")
            return

        # ==============================================================
        # 🛠️ تنسيق البيانات لتطابق الخوارزميات الأصلية
        # ==============================================================
        
        # 1. تجهيز إعدادات الجدول
        settings_for_placement = dict(main_settings)
        settings_for_placement['examSchedule'] = exam_schedule
        
        # 2. تجهيز القاعات الخاصة بالمستويات: {'السنة الأولى': ['قاعة 1', 'قاعة 2']}
        halls_map = {h['id']: h['name'] for h in all_halls_list}
        level_hall_assignments = defaultdict(list)
        for lh in level_halls:
            if lh['hall_id'] in halls_map:
                level_hall_assignments[lh['level_name']].append(halls_map[lh['hall_id']])
        settings_for_placement['levelHallAssignments'] = dict(level_hall_assignments)
        
        # 3. تجهيز قائمة المواد: [{'name': 'رياضيات', 'level': 'السنة الأولى'}]
        formatted_subjects = [{'name': s['subj_name'], 'level': s['level_name']} for s in all_subjects_list]
        
        # 4. تجهيز ملاك المواد: {('رياضيات', 'السنة الأولى'): 'الأستاذ أحمد'}
        subject_owners = {}
        for prof, subjs in assignments.items():
            for subj in subjs:
                subject_owners[(clean_string_for_matching(subj['subj_name']), clean_string_for_matching(subj['level_name']))] = prof
                
        # 5. تجهيز قائمة القاعات: [{'name': 'قاعة 1', 'type': 'كبيرة'}]
        formatted_halls = [{'name': h['name'], 'type': h['type']} for h in all_halls_list]

        # ==============================================================
        # 🚀 تشغيل مرحلة التوزيع الأولي للمواد (المرحلة 1 والمرحلة 1.5)
        # ==============================================================
        # التحقق مما إذا كان هناك جدول مثبت يدوياً
        conn = get_db_connection()
        pinned_row = conn.execute("SELECT value FROM settings WHERE key = 'pinned_subject_schedule'").fetchone()
        conn.close()

        if pinned_row and pinned_row['value']:
            log_queue.put("--- 📌 تم العثور على مخطط مواد يدوي (مُثبت)، سيتم اعتماده كلياً وتخطي التوزيع التلقائي للمواد ---")
            subject_schedule = json.loads(pinned_row['value'])
            group_mappings = {} # لا نحتاجه لأن المواد موزعة أصلاً
        else:
            log_queue.put(">>> بناء جدول المواد المبدئي وتوزيع القاعات (تلقائياً)...")
            subject_schedule, group_mappings = _run_initial_subject_placement(
                settings_for_placement, formatted_subjects, all_levels_list, subject_owners, formatted_halls
            )
            
            # تفعيل المرحلة 1.5 (تجميع المواد) فقط إذا لم يكن هناك جدول يدوي
            if main_settings.get('groupSubjects', False):
                subject_schedule = run_subject_optimization_phase(
                    subject_schedule, assignments, all_levels_list, subject_owners, 
                    settings_for_placement, log_queue, group_mappings, stop_event=stop_event
                )

        # ... (قفل الحراس)
        locked_guards = set()
        sorted_dates = sorted(exam_schedule.keys())
        date_map = {date: i for i, date in enumerate(sorted_dates)}
        duty_patterns = main_settings.get('dutyPatterns', {})

        # 💡 الحل هنا: إعطاء معرف فريد (UUID) لكل امتحان قبل محاولة قفله
        for day in subject_schedule.values():
            for slot in day.values():
                for exam in slot:
                    if 'uuid' not in exam:
                        exam['uuid'] = str(uuid.uuid4())

        if main_settings.get('assignOwnerAsGuard', False):
            prof_last_exam = {}
            for day in subject_schedule.values():
                for slot in day.values():
                    for exam in slot:
                        owner = exam.get('professor')
                        if owner and owner != "غير محدد":
                            exam_date_time_str = f"{exam['date']} {exam['time'].split('-')[0]}"
                            if owner not in prof_last_exam or exam_date_time_str > prof_last_exam[owner]['datetime_str']:
                                prof_last_exam[owner] = {'exam': exam, 'datetime_str': exam_date_time_str}
            
            unavailable_days = main_settings.get('unavailableDays', {})
            for owner, data in prof_last_exam.items():
                exam_to_lock = data['exam']
                if exam_to_lock['date'] not in unavailable_days.get(owner, []):
                    locked_guards.add((exam_to_lock['uuid'], owner))

        # ==============================================================
        # ⚙️ تشغيل سلسلة الخوارزميات (Pipeline)
        # ==============================================================
        
        
        # 1. إكمال الجدول بالحراس الوهميين (نقص) مرة واحدة فقط قبل بدء السلسلة
        current_schedule = complete_schedule_with_guards(
            subject_schedule, main_settings, all_professors, assignments, 
            all_levels_list, duty_patterns, date_map, all_subjects_list, locked_guards, stop_event, log_queue
        )
        
        best_schedule = current_schedule
        
        # 2. تمرير الجدول من خوارزمية إلى التي تليها
        for algo in algorithm_choices:
            if stop_event and stop_event.is_set(): break
            
            log_queue.put(f"\n==========================================")
            log_queue.put(f"🚀 بدء تشغيل مرحلة: {algo.upper()}")
            log_queue.put(f"==========================================")
            
            if algo == 'unified':
                best_schedule, _ = run_unified_lns_optimizer(best_schedule, main_settings, all_professors, assignments, duty_patterns, date_map, all_subjects_list, log_queue, all_levels_list, locked_guards, stop_event)
            elif algo == 'lns':
                best_schedule, _, _, _ = run_large_neighborhood_search(best_schedule, main_settings, all_professors, duty_patterns, date_map, log_q=log_queue, locked_guards=locked_guards, stop_event=stop_event)
            elif algo == 'vns':
                best_schedule, _, _, _ = run_variable_neighborhood_search(best_schedule, main_settings, all_professors, duty_patterns, date_map, log_q=log_queue, locked_guards=locked_guards, stop_event=stop_event)
            elif algo == 'tabu':
                best_schedule, _, _, _ = run_tabu_search(best_schedule, main_settings, all_professors, duty_patterns, date_map, log_q=log_queue, locked_guards=locked_guards, stop_event=stop_event)

        if best_schedule:
            log_queue.put("\n✓ انتهت سلسلة الخوارزميات بالكامل. جاري حساب الإحصائيات النهائية...")

            # --- 🌟 تشغيل فريق الطوارئ لسد النقص المتبقي 🌟 ---
            from app.services.algorithms import desperation_repair_pass, calculate_cost, format_cost_tuple
            
            log_queue.put(">>> جاري تفعيل فريق الطوارئ (جبر النقص الأخير)...")
            
            # 1. تنفيذ جبر النقص
            best_schedule = desperation_repair_pass(best_schedule, main_settings, all_professors, duty_patterns, date_map)
            
            # 2. حساب التكلفة الجديدة بعد الإصلاح
            final_cost = calculate_cost(best_schedule, main_settings, all_professors, duty_patterns, date_map)
            
            # 3. طباعة النتيجة النهائية للشاشة السوداء
            log_queue.put(f"✓ اكتمل جبر النقص. النتيجة النهائية: {format_cost_tuple(final_cost)}")
            
            # --- حساب الإحصائيات للوحة المعلومات ---
            all_exams_flat = [exam for day in best_schedule.values() for slot in day.values() for exam in slot]
            prof_stats = {p: {'large': 0, 'other': 0} for p in all_professors}
            shortage_reports = []
            duties_per_day = defaultdict(int)
            
            guards_large_hall = int(main_settings.get('guardsLargeHall', 4))
            for exam in all_exams_flat:
                # 1. تسجيل النقص وعدد الورديات اليومية
                for guard in exam.get('guards', []):
                    if guard == "**نقص**":
                        shortage_reports.append(f"{exam['subject']} ({exam['level']})")
                    else:
                        duties_per_day[exam['date']] += 1
                
                # 2. الفرز الدقيق للحصص (كبيرة مقابل أخرى)
                guards_copy = [g for g in exam.get('guards', []) if g != "**نقص**"]
                large_guards_needed = sum(guards_large_hall for h in exam.get('halls', []) if h.get('type') == 'كبيرة')
                
                for guard in guards_copy[:large_guards_needed]:
                    if guard in prof_stats: prof_stats[guard]['large'] += 1
                for guard in guards_copy[large_guards_needed:]:
                    if guard in prof_stats: prof_stats[guard]['other'] += 1

            total_large = sum(s['large'] for s in prof_stats.values())
            total_other = sum(s['other'] for s in prof_stats.values())
            total_duties = total_large + total_other
            num_profs = len(all_professors)
            
            # --- 1. حسابات العبء وأكثر يوم مزدحم (لا نحذفها) ---
            large_weight = float(main_settings.get('largeHallWeight', 3.0))
            other_weight = float(main_settings.get('otherHallWeight', 1.0))
            prof_workload = {p: (s['large'] * large_weight) + (s['other'] * other_weight) for p, s in prof_stats.items() if (s['large']+s['other']) > 0}
            sorted_profs = sorted(prof_workload.items(), key=lambda item: item[1])

            busiest_day_date = max(duties_per_day, key=duties_per_day.get) if duties_per_day else 'N/A'
            busiest_day_duties = duties_per_day[busiest_day_date] if duties_per_day else 0

            # --- 2. ⚖️ حساب تقرير التوازن (مع دعم الأنماط اليدوية الذكية) ---
            enable_custom_targets = main_settings.get('enableCustomTargets', False)
            custom_target_patterns = main_settings.get('customTargetPatterns', [])
            
            prof_targets_map = {}
            
            if num_profs > 0:
                # إذا قام المستخدم بتفعيل الأنماط المخصصة وأدخل أنماطاً بالفعل
                if enable_custom_targets and custom_target_patterns:
                    prof_targets_list = []
                    
                    # 1. بناء قائمة الأهداف بناءً على الأنماط اليدوية
                    for pattern in custom_target_patterns:
                        count = int(pattern.get('count', 0))
                        for _ in range(count): 
                            prof_targets_list.append({
                                'large': int(pattern.get('large', 0)), 
                                'other': int(pattern.get('other', 0))
                            })
                    
                    # 2. حساب عدد الأساتذة المتبقين الذين لم يشملهم التوزيع اليدوي
                    num_to_fill = num_profs - len(prof_targets_list)
                    
                    # 3. تكملة الباقي تلقائياً بالعدل
                    if num_to_fill > 0:
                        rem_large = total_large - sum(p['large'] for p in prof_targets_list)
                        rem_other = total_other - sum(p['other'] for p in prof_targets_list)
                        
                        if rem_large >= 0 and rem_other >= 0:
                            prof_targets_list.extend(
                                calculate_balanced_distribution(rem_large, rem_other, num_to_fill, large_weight, other_weight)
                            )
                    
                    # 4. خلط أسماء الأساتذة وربطهم بالأهداف
                    shuffled_profs = list(all_professors) # نستخدم قائمة all_professors الحالية
                    random.shuffle(shuffled_profs)
                    prof_targets_map = {prof: prof_targets_list[i] for i, prof in enumerate(shuffled_profs) if i < len(prof_targets_list)}
                    
                else:
                    # التوزيع التلقائي بالكامل (في حال عدم تفعيل التحديد اليدوي)
                    prof_targets_list = calculate_balanced_distribution(
                        total_large, total_other, num_profs, large_weight, other_weight
                    )
                    
                    if prof_targets_list: 
                        prof_targets_map = {prof: prof_targets_list[i % len(prof_targets_list)] for i, prof in enumerate(sorted(all_professors))}

            # 3. نولد التقرير النهائي باستخدام الأهداف الدقيقة
            balance_report_data = generate_balance_report(prof_stats, prof_targets_map)

            # --- تجميع كل البيانات في القاموس النهائي ---
            
            # --- 4. تجهيز تقرير المواد التي لم يتم جدولتها ---
            scheduled_subject_keys = {(exam['subject'], exam['level']) for day in best_schedule.values() for slot in day.values() for exam in slot}
            unscheduled_subjects = []
            for subj in all_subjects_list:
                if (subj['subj_name'], subj['level_name']) not in scheduled_subject_keys:
                    unscheduled_subjects.append(f"{subj['subj_name']} ({subj['level_name']})")

            # --- 5. تجهيز بيانات الرسم البياني ---
            chart_data = {
                'labels': [],
                'datasets': [
                    {'label': 'حصص القاعات الأخرى', 'data': [], 'backgroundColor': 'rgba(54, 162, 235, 0.7)'},
                    {'label': 'حصص القاعة الكبيرة', 'data': [], 'backgroundColor': 'rgba(255, 99, 132, 0.7)'}
                ]
            }
            for prof_name in sorted(prof_stats.keys()):
                chart_data['labels'].append(prof_name)
                chart_data['datasets'][0]['data'].append(prof_stats[prof_name]['other'])
                chart_data['datasets'][1]['data'].append(prof_stats[prof_name]['large'])

            # --- تجميع كل البيانات في القاموس النهائي ---
            # --- تجميع كل البيانات في القاموس النهائي ---
            stats_dashboard = {
                'total_large_duties': total_large,
                'total_other_duties': total_other,
                'total_duties': total_duties,
                'avg_duties_per_prof': total_duties / num_profs if num_profs > 0 else 0,
                'busiest_day': {'date': busiest_day_date, 'duties': busiest_day_duties},
                'least_burdened_profs': [{'name': p[0], 'workload': round(p[1], 2)} for p in sorted_profs[:3]],
                'most_burdened_profs': [{'name': p[0], 'workload': round(p[1], 2)} for p in sorted_profs[-3:]][::-1],
                'shortage_reports': shortage_reports,
                'unscheduled_subjects_report': unscheduled_subjects,
                'chart_data': chart_data,
                'balance_report_data': balance_report_data 
            }

            # 👇 توليد تقرير الأخطاء والملاحظات 👇
            from app.services.algorithms import generate_violation_report
            violations_report = generate_violation_report(best_schedule, main_settings, all_professors)

            # إرسال الجدول، الإحصائيات، والتقرير معاً للواجهة
            result_json = json.dumps({
                "success": True, 
                "schedule": best_schedule, 
                "stats": stats_dashboard,
                "violations": violations_report  # 👈 إضافة التقرير هنا
            })
            log_queue.put(f"DONE:{result_json}")
        else:
            log_queue.put("DONE:{\"success\": false, \"message\": \"فشل إيجاد حل أو تم الإيقاف.\"}")

    except Exception as e:
        log_queue.put(f"خطأ فادح: {str(e)}")
        log_queue.put("DONE:{\"success\": false, \"message\": \"حدث خطأ داخلي في الخادم.\"}")