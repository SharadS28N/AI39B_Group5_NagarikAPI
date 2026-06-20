import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _database_settings():
    database_url = os.getenv('DATABASE_URL', '').strip()

    if database_url:
        return database_url

    host = os.getenv('MYSQL_HOST', os.getenv('DB_HOST', 'localhost'))
    port = int(os.getenv('MYSQL_PORT', os.getenv('DB_PORT', 3306)))
    user = os.getenv('MYSQL_USER', os.getenv('DB_USER', 'root'))
    password = os.getenv('MYSQL_PASSWORD', os.getenv('DB_PASSWORD', ''))
    database = os.getenv('MYSQL_DATABASE', os.getenv('DB_NAME', 'nagarikapi'))
    ssl_ca = os.getenv('SSL_CA', '')

    if user and password and host and database:
        if ssl_ca:
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?ssl_ca={ssl_ca}"
        else:
            return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    
    # Fallback to SQLite
    return f"sqlite:///{os.path.join(BASE_DIR, 'nagarikapi.db')}"


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = _database_settings()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'google_vision.json')
    APP_URL = os.getenv('APP_URL', 'http://localhost:5000')
    
    # For compatibility with app/database.py
    MYSQL_HOST = os.getenv('MYSQL_HOST', os.getenv('DB_HOST', ''))
    MYSQL_PORT = os.getenv('MYSQL_PORT', os.getenv('DB_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', os.getenv('DB_USER', ''))
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', os.getenv('DB_PASSWORD', ''))
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE', os.getenv('DB_NAME', ''))
    SQLITE_PATH = os.path.join(BASE_DIR, 'nagarikapi.db')
