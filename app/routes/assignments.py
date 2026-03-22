from flask import Blueprint, request, jsonify
import sqlite3
from app.database import get_db_connection

assignments_bp = Blueprint('assignments', __name__)

# ==========================================
# 👨‍🏫 أ. إسناد المواد للأساتذة
# ==========================================

@assignments_bp.route('/api/assignments/professors', methods=['GET'])
def get_professor_assignments():
    """جلب قائمة الإسنادات مجمعة حسب الأستاذ"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id as prof_id, p.name as prof_name, s.id as subj_id, s.name as subj_name, l.name as level_name
        FROM professor_subject ps
        JOIN professors p ON ps.professor_id = p.id
        JOIN subjects s ON ps.subject_id = s.id
        JOIN levels l ON s.level_id = l.id
        ORDER BY p.name, l.name, s.name
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    # تجميع البيانات
    data = {}
    for r in rows:
        pid = r['prof_id']
        if pid not in data:
            data[pid] = {'prof_id': pid, 'prof_name': r['prof_name'], 'subjects': []}
        data[pid]['subjects'].append({
            'subj_id': r['subj_id'], 
            'subj_name': r['subj_name'], 
            'level_name': r['level_name']
        })
        
    return jsonify(list(data.values()))

@assignments_bp.route('/api/assignments/professors', methods=['POST'])
def assign_subjects_to_professor():
    """إسناد عدة مواد لأستاذ واحد"""
    data = request.json
    prof_id = data.get('professor_id')
    subj_ids = data.get('subject_ids', [])
    
    if not prof_id or not subj_ids:
        return jsonify({'success': False, 'message': 'البيانات غير مكتملة'})
        
    conn = get_db_connection()
    cursor = conn.cursor()
    added = 0
    for sid in subj_ids:
        try:
            cursor.execute("INSERT INTO professor_subject (professor_id, subject_id) VALUES (?, ?)", (prof_id, sid))
            added += 1
        except sqlite3.IntegrityError:
            pass # تجاهل إذا كانت المادة مسندة مسبقاً لنفس الأستاذ
            
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'added': added})

@assignments_bp.route('/api/assignments/professors/<int:prof_id>/<int:subj_id>', methods=['DELETE'])
def remove_professor_subject(prof_id, subj_id):
    """حذف مادة معينة من أستاذ"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM professor_subject WHERE professor_id = ? AND subject_id = ?", (prof_id, subj_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@assignments_bp.route('/api/assignments/professors/<int:prof_id>/all', methods=['DELETE'])
def remove_all_professor_subjects(prof_id):
    """إلغاء إسناد كل المواد لأستاذ معين (للنقر المزدوج)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM professor_subject WHERE professor_id = ?", (prof_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@assignments_bp.route('/api/assignments/subjects/<int:subj_id>', methods=['DELETE'])
def remove_subject_assignment(subj_id):
    """إلغاء إسناد مادة معينة من أي أستاذ (للنقر المزدوج)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM professor_subject WHERE subject_id = ?", (subj_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ==========================================
# 🏫 ب. تحديد قاعات الامتحانات لكل مستوى
# ==========================================

@assignments_bp.route('/api/assignments/levels', methods=['GET'])
def get_level_assignments():
    """جلب قائمة القاعات مجمعة حسب المستوى"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT l.id as level_id, l.name as level_name, h.id as hall_id, h.name as hall_name, h.type as hall_type
        FROM level_halls lh
        JOIN levels l ON lh.level_id = l.id
        JOIN halls h ON lh.hall_id = h.id
        ORDER BY l.name, h.type, h.name
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    data = {}
    for r in rows:
        lid = r['level_id']
        if lid not in data:
            data[lid] = {'level_id': lid, 'level_name': r['level_name'], 'halls': []}
        data[lid]['halls'].append({
            'hall_id': r['hall_id'], 
            'hall_name': r['hall_name'], 
            'hall_type': r['hall_type']
        })
        
    return jsonify(list(data.values()))

@assignments_bp.route('/api/assignments/levels', methods=['POST'])
def assign_halls_to_level():
    """تخصيص عدة قاعات لمستوى واحد"""
    data = request.json
    level_id = data.get('level_id')
    hall_ids = data.get('hall_ids', [])
    
    if not level_id or not hall_ids:
        return jsonify({'success': False, 'message': 'البيانات غير مكتملة'})
        
    conn = get_db_connection()
    cursor = conn.cursor()
    added = 0
    for hid in hall_ids:
        try:
            cursor.execute("INSERT INTO level_halls (level_id, hall_id) VALUES (?, ?)", (level_id, hid))
            added += 1
        except sqlite3.IntegrityError:
            pass
            
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'added': added})

@assignments_bp.route('/api/assignments/levels/<int:level_id>/<int:hall_id>', methods=['DELETE'])
def remove_level_hall(level_id, hall_id):
    """إزالة قاعة من مستوى"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM level_halls WHERE level_id = ? AND hall_id = ?", (level_id, hall_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@assignments_bp.route('/api/assignments/levels/bulk', methods=['POST'])
def bulk_update_level_halls():
    """حفظ قاعات كل المستويات دفعة واحدة"""
    data = request.json # سيستقبل { "level_id": [hall_id1, hall_id2] }
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for level_id_str, hall_ids in data.items():
        level_id = int(level_id_str)
        # مسح القاعات القديمة لهذا المستوى
        cursor.execute("DELETE FROM level_halls WHERE level_id = ?", (level_id,))
        # إدراج القاعات الجديدة المحددة
        for hid in hall_ids:
            cursor.execute("INSERT INTO level_halls (level_id, hall_id) VALUES (?, ?)", (level_id, hid))
            
    conn.commit()
    conn.close()
    return jsonify({'success': True})