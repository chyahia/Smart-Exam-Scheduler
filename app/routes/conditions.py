from flask import Blueprint, request, jsonify
import sqlite3
import json
from app.database import get_db_connection

conditions_bp = Blueprint('conditions', __name__)

@conditions_bp.route('/api/settings', methods=['GET'])
def get_settings():
    """جلب كل إعدادات وقيود البرنامج المحفوظة"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'main_settings'")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify(json.loads(row['value']))
    return jsonify({})

@conditions_bp.route('/api/settings', methods=['POST'])
def save_settings():
    """حفظ إعدادات وقيود البرنامج"""
    settings_data = request.json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
        ('main_settings', json.dumps(settings_data))
    )
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'تم حفظ القيود والشروط بنجاح.'})