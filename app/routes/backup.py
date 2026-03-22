from flask import Blueprint, request, jsonify, send_file
import json
import io
from app.database import get_db_connection
import os
import signal

backup_bp = Blueprint('backup', __name__)

@backup_bp.route('/api/backup', methods=['GET'])
def backup_data():
    conn = get_db_connection()
    tables = ['professors', 'halls', 'levels', 'subjects', 'professor_subject', 'level_halls', 'settings']
    backup_dict = {}
    
    for table in tables:
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        backup_dict[table] = [dict(row) for row in rows]
        
    conn.close()
    
    json_string = json.dumps(backup_dict, ensure_ascii=False, indent=4)
    buffer = io.BytesIO(json_string.encode('utf-8'))
    
    return send_file(buffer, as_attachment=True, download_name="exam_guard_backup.json", mimetype="application/json")

@backup_bp.route('/api/restore', methods=['POST'])
def restore_data():
    backup_data = request.get_json()
    tables = ['professors', 'halls', 'levels', 'subjects', 'professor_subject', 'level_halls', 'settings']
    
    if not all(table in backup_data for table in tables): 
        return jsonify({"error": "ملف النسخة الاحتياطية غير صالح أو تالف."}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # مسح البيانات الحالية بترتيب عكسي لتجنب مشاكل المفاتيح الأجنبية
        for table in reversed(tables):
            cursor.execute(f"DELETE FROM {table}")
            
        # إدراج البيانات الجديدة
        for table in tables:
            rows = backup_data[table]
            if rows:
                columns = ', '.join(rows[0].keys())
                placeholders = ', '.join(['?' for _ in rows[0]])
                insert_query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                
                data_to_insert = [tuple(row.values()) for row in rows]
                cursor.executemany(insert_query, data_to_insert)
                
        conn.commit()
        conn.close()
    except Exception as e: 
        return jsonify({"error": f"حدث خطأ أثناء استعادة البيانات: {e}"}), 500
        
    return jsonify({"success": True, "message": "تم استعادة البيانات بنجاح. سيتم إعادة تحميل الصفحة."})

@backup_bp.route('/api/reset-all', methods=['POST'])
def reset_all_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        tables = ['professors', 'halls', 'levels', 'subjects', 'professor_subject', 'level_halls', 'settings']
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "تم مسح جميع البيانات بنجاح. سيتم إعادة تحميل الصفحة."})
    except Exception as e: 
        return jsonify({"error": f"حدث خطأ أثناء مسح البيانات: {e}"}), 500

@backup_bp.route('/api/shutdown', methods=['POST'])
def shutdown_server():
    try:
        # إرسال إشارة إيقاف للخادم لإنهائه بأمان
        os.kill(os.getpid(), signal.SIGINT)
        return jsonify({"success": True, "message": "جاري إيقاف الخادم..."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500    
