import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from sqlalchemy.engine import make_url
import pymysql
from config import Config

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


def _seed_demo_data():
    from app.models import Company, KYCRequest, User

    if User.query.first():
        return

    company = Company(
        name='Bank Nepal',
        registration_number='BN-001',
        api_key='demo-bank-nepal'
    )

    admin = User(
        email='admin@nagarikapi.com',
        full_name='Superuser Admin',
        role='admin'
    )
    admin.set_password('Admin123')

    company_admin = User(
        email='hr@banknepal.com',
        full_name='Company Admin',
        role='company_admin'
    )
    company_admin.set_password('CompanyAdmin123')

    end_user = User(
        email='user@example.com',
        full_name='End User',
        role='user'
    )
    end_user.set_password('User123')

    db.session.add(company)
    db.session.flush()
    company_admin.company = company
    end_user.company = company

    sample_request = KYCRequest(
        user=end_user,
        organization=company,
        document_type='national_id',
        status='approved'
    )

    db.session.add_all([admin, company_admin, end_user, sample_request])
    db.session.commit()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    database_uri = app.config['SQLALCHEMY_DATABASE_URI']
    sqlite_fallback_used = False

    if database_uri.startswith('mysql'):
        try:
            url = make_url(database_uri)
            connection = pymysql.connect(
                host=url.host,
                user=url.username,
                password=url.password,
                database=url.database,
                port=url.port or 3306,
                connect_timeout=2,
            )
            connection.close()
        except Exception:
            sqlite_fallback_used = True
            fallback_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'nagarikapi.db')
            app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.abspath(fallback_path)}"
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)


    from app.routes.views import main
    from app.routes.auth import auth
    from app.models import User
    
    app.register_blueprint(main)
    app.register_blueprint(auth)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()

        should_seed_demo_data = (
            sqlite_fallback_used
            or os.getenv('SEED_DEMO_DATA', '').strip().lower() in {'1', 'true', 'yes', 'on'}
        )

        if should_seed_demo_data:
            _seed_demo_data()

    return app
