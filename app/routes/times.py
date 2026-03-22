from flask import Blueprint, request, jsonify
import sqlite3
import json
from app.database import get_db_connection

times_bp = Blueprint('times', __name__)

@times_bp.route('/api/exam-schedule', methods=['GET'])
def get_exam_schedule():
    """جلب جدول الامتحانات المحفوظ مسبقاً"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'exam_schedule'")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify(json.loads(row['value']))
    return jsonify({})

@times_bp.route('/api/exam-schedule', methods=['POST'])
def save_exam_schedule():
    """حفظ هيكل جدول الامتحانات (الأيام، الفترات، والمستويات)"""
    schedule_data = request.json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    # استخدام INSERT OR REPLACE لتحديث القيمة إذا كانت موجودة
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
        ('exam_schedule', json.dumps(schedule_data))
    )
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم حفظ هيكل جدول الامتحانات بنجاح.'})