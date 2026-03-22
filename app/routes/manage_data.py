from flask import Blueprint, request, jsonify
import sqlite3
from app.database import get_db_connection

manage_data_bp = Blueprint('manage_data', __name__)

# ==========================================
# 🗑️ دوال الحذف (Delete) - مع التنظيف الشامل
# ==========================================
@manage_data_bp.route('/api/delete-<entity>/<int:id>', methods=['DELETE'])
def delete_entity(entity, id):
    allowed_entities = {
        'professor': 'professors',
        'hall': 'halls',
        'level': 'levels',
        'subject': 'subjects'
    }
    
    if entity not in allowed_entities:
        return jsonify({'success': False, 'message': 'كيان غير صالح'})

    table = allowed_entities[entity]
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 1. جلب اسم العنصر قبل حذفه لتنظيف إعدادات المرحلة 5 لاحقاً
        cursor.execute(f"SELECT name FROM {table} WHERE id = ?", (id,))
        row = cursor.fetchone()
        
        if row:
            entity_name = row['name']
            
            # 2. الحذف من الجدول الأساسي (سيحذف الإسنادات في المرحلة 3 تلقائياً بفضل CASCADE)
            cursor.execute(f"DELETE FROM {table} WHERE id = ?", (id,))
            
            # 3. التنظيف الشامل: مسح أي قيود أو شروط في المرحلة 5 تحمل اسم هذا العنصر المحذوف
            # (مثل: أنماط الحراسة للأستاذ، أو الأيام غير المتاحة له)
            cursor.execute("DELETE FROM settings WHERE key LIKE ?", (f"%{entity_name}%",))
            
        conn.commit()
        success = True
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()
        
    return jsonify({'success': success})

# ==========================================
# ✏️ دوال التعديل (Edit)
# ==========================================
@manage_data_bp.route('/api/edit-professor/<int:id>', methods=['PUT'])
def edit_professor(id):
    name = request.json.get('name').strip()
    conn = get_db_connection()
    try:
        conn.execute("UPDATE professors SET name = ? WHERE id = ?", (name, id))
        conn.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'هذا الاسم موجود مسبقاً'})
    finally:
        conn.close()

@manage_data_bp.route('/api/edit-hall/<int:id>', methods=['PUT'])
def edit_hall(id):
    name = request.json.get('name').strip()
    hall_type = request.json.get('type')
    conn = get_db_connection()
    try:
        conn.execute("UPDATE halls SET name = ?, type = ? WHERE id = ?", (name, hall_type, id))
        conn.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'هذه القاعة موجودة مسبقاً'})
    finally:
        conn.close()

@manage_data_bp.route('/api/edit-level/<int:id>', methods=['PUT'])
def edit_level(id):
    name = request.json.get('name').strip()
    conn = get_db_connection()
    try:
        conn.execute("UPDATE levels SET name = ? WHERE id = ?", (name, id))
        conn.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'هذا المستوى موجود مسبقاً'})
    finally:
        conn.close()

@manage_data_bp.route('/api/edit-subject/<int:id>', methods=['PUT'])
def edit_subject(id):
    name = request.json.get('name').strip()
    conn = get_db_connection()
    try:
        conn.execute("UPDATE subjects SET name = ? WHERE id = ?", (name, id))
        conn.commit()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'هذه المادة موجودة مسبقاً'})
    finally:
        conn.close()