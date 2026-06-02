import os
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

load_dotenv()


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _database_settings():
    database_url = os.getenv('DATABASE_URL', '').strip()

    if database_url:
        parsed = urlparse(database_url)
        if parsed.scheme not in {'mysql', 'mysql+pymysql'}:
            raise ValueError('DATABASE_URL must use a MySQL scheme')

        return {
            'host': parsed.hostname or '127.0.0.1',
            'port': parsed.port or 3306,
            'user': unquote(parsed.username or ''),
            'password': unquote(parsed.password or ''),
            'database': (parsed.path or '/').lstrip('/'),
        }

    return {
        'host': os.getenv('DB_HOST', '127.0.0.1'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'nagarikapi'),
    }


def _resolve_ssl_ca():
    ssl_ca = os.getenv('SSL_CA', '').strip()
    if not ssl_ca:
        default_ca = os.path.join(BASE_DIR, 'ca.pem')
        return default_ca if os.path.exists(default_ca) else ''

    if os.path.isabs(ssl_ca):
        return ssl_ca

    return os.path.join(BASE_DIR, ssl_ca)


MYSQL_SETTINGS = _database_settings()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    MYSQL_HOST = MYSQL_SETTINGS['host']
    MYSQL_PORT = MYSQL_SETTINGS['port']
    MYSQL_USER = MYSQL_SETTINGS['user']
    MYSQL_PASSWORD = MYSQL_SETTINGS['password']
    MYSQL_DATABASE = MYSQL_SETTINGS['database']
    MYSQL_SSL_CA = _resolve_ssl_ca()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Build SQLALCHEMY_DATABASE_URI from MySQL settings if available
    if MYSQL_USER or MYSQL_PASSWORD or MYSQL_HOST or MYSQL_DATABASE:
        user = MYSQL_USER or ''
        password = MYSQL_PASSWORD or ''
        auth = f"{user}:{password}@" if user or password else ''
        host = MYSQL_HOST or '127.0.0.1'
        port = f":{MYSQL_PORT}" if MYSQL_PORT else ''
        database = MYSQL_DATABASE or ''
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{auth}{host}{port}/{database}"
    else:
        SQLALCHEMY_DATABASE_URI = ''