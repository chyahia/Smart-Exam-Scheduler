import sqlite3
import os
import sys

# اسم مجلد برنامجك في الـ AppData (يمكنك تغييره كما تشاء)
APP_FOLDER_NAME = "SmartExamScheduler"
DB_NAME = "exams_database.db"

def get_db_path():
    """
    دالة ذكية لتحديد مسار قاعدة البيانات:
    تحاول أولاً الكتابة بجانب البرنامج، وإن فشلت تذهب إلى AppData.
    """
    # 1. تحديد مسار المجلد الذي يعمل منه البرنامج حالياً
    if getattr(sys, 'frozen', False):
        # إذا كان البرنامج محولاً إلى exe
        base_dir = os.path.dirname(sys.executable)
    else:
        # إذا كان يعمل كسكربت بايثون عادي
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    local_db_path = os.path.join(base_dir, DB_NAME)

    # 2. اختبار صلاحية الكتابة في هذا المسار
    try:
        # نحاول فتح/إنشاء الملف في وضع الإلحاق (Append) لاختبار الصلاحية
        with open(local_db_path, 'a') as f:
            pass
        return local_db_path # نجحنا! المسار محلي ومسموح الكتابة فيه
        
    except (PermissionError, OSError):
        # 3. الخطة البديلة: المسار محمي (مثل Program Files)، ننتقل لـ AppData
        appdata_dir = os.environ.get('APPDATA')
        if not appdata_dir:
            # احتياطي في حال لم يتم العثور على APPDATA
            appdata_dir = os.path.expanduser('~')
            
        app_data_path = os.path.join(appdata_dir, APP_FOLDER_NAME)
        
        # إنشاء المجلد في Roaming إذا لم يكن موجوداً
        if not os.path.exists(app_data_path):
            os.makedirs(app_data_path)
            
        return os.path.join(app_data_path, DB_NAME)

def get_db_connection():
    """إنشاء اتصال بقاعدة البيانات وإرجاعه"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON') # تفعيل دعم المفاتيح الأجنبية
    return conn

def init_db():
    """تهيئة قاعدة البيانات وإنشاء الجداول بالبنية الجديدة"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. الأساتذة
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # 2. القاعات (مع تصنيف النوع)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS halls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('صغيرة', 'متوسطة', 'كبيرة'))
        )
    ''')

    # 3. المستويات الدراسية (جدول جديد ومهم جداً)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS levels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # 4. المواد (مربوطة بجدول المستويات)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            level_id INTEGER NOT NULL,
            FOREIGN KEY(level_id) REFERENCES levels(id) ON DELETE CASCADE,
            UNIQUE(name, level_id) -- منع تكرار نفس المادة في نفس المستوى
        )
    ''')

    # --- باقي الجداول ستبقى كما هي للمراحل القادمة ---

    # جدول ربط الأساتذة بالمواد (إسناد المواد)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professor_subject (
            professor_id INTEGER,
            subject_id INTEGER,
            FOREIGN KEY(professor_id) REFERENCES professors(id) ON DELETE CASCADE,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
            PRIMARY KEY (professor_id, subject_id)
        )
    ''')

    # جدول ربط المستويات بالقاعات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS level_halls (
            level_id INTEGER NOT NULL,
            hall_id INTEGER,
            FOREIGN KEY(level_id) REFERENCES levels(id) ON DELETE CASCADE,
            FOREIGN KEY(hall_id) REFERENCES halls(id) ON DELETE CASCADE,
            PRIMARY KEY (level_id, hall_id)
        )
    ''')

    # الأيام والأوقات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS exam_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_order INTEGER NOT NULL,
            date_text TEXT NOT NULL,
            morning_slots INTEGER DEFAULT 0,
            afternoon_slots INTEGER DEFAULT 0
        )
    ''')

    # القيود والشروط
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()