from flask import Flask
from .database import init_db

def create_app():
    app = Flask(__name__)
    app.secret_key = 'exam_invigilation_secret_key'

    init_db()

    # تسجيل مسارات المرحلة الأولى
    from .routes.basic_data import basic_data_bp
    app.register_blueprint(basic_data_bp)

    # 🚀 تسجيل مسارات المرحلة الثانية (إدارة البيانات)
    from .routes.manage_data import manage_data_bp
    app.register_blueprint(manage_data_bp)

    # 🚀 تسجيل مسارات المرحلة الثالثة (الإسناد والقاعات)
    from .routes.assignments import assignments_bp
    app.register_blueprint(assignments_bp)

    # 🚀 تسجيل مسارات المرحلة الرابعة (الأيام والأوقات)
    from .routes.times import times_bp
    app.register_blueprint(times_bp)

    # 🚀 تسجيل مسارات المرحلة الخامسة (القيود والشروط)
    from .routes.conditions import conditions_bp
    app.register_blueprint(conditions_bp)

    # 🚀 تسجيل مسارات المرحلة السادسة (التوليد)
    from .routes.generation import generation_bp
    app.register_blueprint(generation_bp)

    # 🚀 تسجيل مسارات المرحلة السابعة (الحفظ)
    from .routes.backup import backup_bp
    app.register_blueprint(backup_bp)

    from .routes.export import export_bp
    app.register_blueprint(export_bp)

    @app.route('/')
    def index():
        from flask import render_template
        return render_template('index.html')

    return app