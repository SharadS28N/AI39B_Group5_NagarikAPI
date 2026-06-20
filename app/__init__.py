import os

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from config import Config
from app.database import ensure_schema, preflight_database_check

bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['DEBUG'] = True
    app.debug = True

    bcrypt.init_app(app)
    login_manager.init_app(app)

    from app.routes.auth import auth
    from app.routes.views import main
    from app.routes.api import api
    from app.models import User, seed_demo_data

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(api)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.get_by_id(int(user_id))
        except (TypeError, ValueError):
            return None

    @app.context_processor
    def inject_runtime_status():
        return {
            'app_runtime_status': {
                'debug': True,
                'database_ready': bool(app.config.get('DATABASE_READY')),
                'database_host': app.config.get('MYSQL_HOST'),
                'database_name': app.config.get('MYSQL_DATABASE'),
                'database_port': app.config.get('MYSQL_PORT'),
                'database_ssl': bool(app.config.get('MYSQL_SSL_CA')),
            }
        }

    with app.app_context():
        connected, message = preflight_database_check()
        app.config['DATABASE_READY'] = connected

        if connected:
            try:
                ensure_schema()
                
                # Initialize KYC and Token tables
                from app.models.kyc import KYC
                from app.models.token import TokenManager
                from app.models.api_key import APIKeyManager
                
                KYC.create_table()
                TokenManager.create_table()
                APIKeyManager.create_table()

                if os.getenv('SEED_DEMO_DATA', '').strip().lower() in {'1', 'true', 'yes', 'on'}:
                    seed_demo_data()
            except Exception as exc:
                app.config['DATABASE_READY'] = False
                app.logger.warning('Skipping database initialization: %s', exc)
        else:
            app.logger.warning('Database preflight failed: %s', message)

    return app
