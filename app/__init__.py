import os
from flask import Flask, render_template
from config import Config
from app.extensions import db, login_manager, migrate, bcrypt, csrf


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Create upload directories
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'ids'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'selfies'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.views import main_bp
    from app.routes.kyc import kyc_bp
    from app.routes.student import student_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(kyc_bp, url_prefix='/kyc')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_app_status():
        # Default values to prevent template errors
        return {
            'app_runtime_status': {
                'debug': app.debug,
                'database_ready': True,
                'database_host': 'localhost',
                'database_port': 3306,
                'database_name': 'nagarikapi'
            },
            'status': {
                'debug': app.debug,
                'database_ready': True,
                'database_host': 'localhost',
                'database_port': 3306,
                'database_name': 'nagarikapi',
                'database_connected': True,
                'app_name': 'NagarikAPI',
                'database_ping_ok': True,
                'database_ssl': False
            }
        }

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    # Create database tables and seed demo data
    with app.app_context():
        db.create_all()
        from app.models import seed_demo_data
        seed_demo_data()

    return app
