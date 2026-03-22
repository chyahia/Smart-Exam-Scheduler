from flask import Blueprint, request, jsonify
import sqlite3
from app.database import get_db_connection

basic_data_bp = Blueprint('basic_data', __name__)

# ==========================================
# 🔍 دوال جلب البيانات (Get Data) للمعاينة الفورية
# ==========================================

@basic_data_bp.route('/api/get-professors', methods=['GET'])
def get_professors():
    """جلب قائمة كل الأساتذة"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM professors ORDER BY name")
    professors = cursor.fetchall()
    conn.close()
    # تحويل sqlite3.Row إلى قائمة قواميس (JSON)
    return jsonify([dict(row) for row in professors])

@basic_data_bp.route('/api/get-halls', methods=['GET'])
def get_halls():
    """جلب قائمة كل القاعات"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, type FROM halls ORDER BY type, name")
    halls = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in halls])

@basic_data_bp.route('/api/get-levels', methods=['GET'])
def get_levels():
    """جلب قائمة كل المستويات الدراسية"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM levels ORDER BY name")
    levels = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in levels])

@basic_data_bp.route('/api/get-subjects', methods=['GET'])
def get_subjects():
    """جلب قائمة المواد، اختيارياً مربوطة بـ level_id"""
    level_id = request.args.get('level_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if level_id:
        cursor.execute("SELECT id, name FROM subjects WHERE level_id = ? ORDER BY name", (level_id,))
    else:
        cursor.execute("SELECT subjects.id, subjects.name, levels.name as level_name FROM subjects JOIN levels ON subjects.level_id = levels.id ORDER BY levels.name, subjects.name")
        
    subjects = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in subjects])


# ==========================================
# ➕ دوال إضافة البيانات (Add Data)
# ==========================================

@basic_data_bp.route('/api/add-professors', methods=['POST'])
def add_professors():
    """إضافة عدة أساتذة مرة واحدة"""
    data = request.json
    names = data.get('names', [])
    conn = get_db_connection()
    cursor = conn.cursor()
    added, duplicates = 0, 0
    
    for name in names:
        name = name.strip()
        if name:
            try:
                cursor.execute("INSERT INTO professors (name) VALUES (?)", (name,))
                added += 1
            except sqlite3.IntegrityError: duplicates += 1
                
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'added': added, 'duplicates': duplicates})

@basic_data_bp.route('/api/add-halls', methods=['POST'])
def add_halls():
    """إضافة عدة قاعات مرة واحدة"""
    data = request.json
    hall_type = data.get('type')
    halls = data.get('halls', [])
    
    if hall_type not in ['صغيرة', 'متوسطة', 'كبيرة']:
        return jsonify({'success': False, 'message': 'نوع القاعة غير صالح'})
        
    conn = get_db_connection()
    cursor = conn.cursor()
    added, duplicates = 0, 0
    
    for hall in halls:
        hall = hall.strip()
        if hall:
            try:
                cursor.execute("INSERT INTO halls (name, type) VALUES (?, ?)", (hall, hall_type))
                added += 1
            except sqlite3.IntegrityError: duplicates += 1
                
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'added': added, 'duplicates': duplicates})

# دالة جديدة لإضافة المستويات
@basic_data_bp.route('/api/add-levels', methods=['POST'])
def add_levels():
    """إضافة عدة مستويات دراسية مرة واحدة"""
    data = request.json
    levels = data.get('levels', [])
    conn = get_db_connection()
    cursor = conn.cursor()
    added, duplicates = 0, 0
    
    for level in levels:
        level = level.strip()
        if level:
            try:
                cursor.execute("INSERT INTO levels (name) VALUES (?)", (level,))
                added += 1
            except sqlite3.IntegrityError: duplicates += 1
                
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'added': added, 'duplicates': duplicates})

@basic_data_bp.route('/api/add-subjects', methods=['POST'])
def add_subjects():
    """إضافة عدة مواد لمستوى معين"""
    data = request.json
    level_id = data.get('level_id')
    subjects = data.get('subjects', [])
    
    if not level_id:
        return jsonify({'success': False, 'message': 'لا بد من تحديد المستوى أولاً من القائمة'})
        
    conn = get_db_connection()
    cursor = conn.cursor()
    added, duplicates = 0, 0
    
    for subj in subjects:
        subj = subj.strip()
        if subj:
            try:
                cursor.execute("INSERT INTO subjects (name, level_id) VALUES (?, ?)", (subj, level_id))
                added += 1
            except sqlite3.IntegrityError: duplicates += 1
                
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'added': added, 'duplicates': duplicates})