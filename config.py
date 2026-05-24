import os
from dotenv import load_dotenv

load_dotenv()


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL:
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT')
        db_name = os.getenv('DB_NAME')

        if all([db_user, db_password, db_host, db_port, db_name]):
            SQLALCHEMY_DATABASE_URI = (
                f"mysql+pymysql://{db_user}:{db_password}"
                f"@{db_host}:{db_port}/{db_name}"
            )
        else:
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'nagarikapi.db')}"

    SQLALCHEMY_ENGINE_OPTIONS = {}
    if SQLALCHEMY_DATABASE_URI.startswith('mysql'):
        ca_path = os.path.join(BASE_DIR, 'ca.pem')
        if os.path.exists(ca_path):
            SQLALCHEMY_ENGINE_OPTIONS = {
                'connect_args': {
                    'ssl': {
                        'ca': ca_path
                    }
                }
            }
    SQLALCHEMY_TRACK_MODIFICATIONS = False