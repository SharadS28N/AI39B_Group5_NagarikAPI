import os
import socket
from contextlib import contextmanager

import pymysql
from flask import current_app
from pymysql.cursors import DictCursor


def _connection_kwargs():
    config = current_app.config
    kwargs = {
        'host': config['MYSQL_HOST'],
        'port': int(config['MYSQL_PORT']),
        'user': config['MYSQL_USER'],
        'password': config['MYSQL_PASSWORD'],
        'database': config['MYSQL_DATABASE'],
        'charset': 'utf8mb4',
        'cursorclass': DictCursor,
        'autocommit': False,
    }

    ssl_ca = config.get('MYSQL_SSL_CA', '')
    if ssl_ca and os.path.exists(ssl_ca):
        kwargs['ssl'] = {'ca': ssl_ca}

    return kwargs


@contextmanager
def get_connection():
    connection = pymysql.connect(**_connection_kwargs())
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def fetch_all(query, params=None):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()


def fetch_one(query, params=None):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchone()


def execute(query, params=None):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.lastrowid


def ping_database():
    try:
        row = fetch_one('SELECT 1 AS ok')
        return True, row.get('ok') == 1 if row else False, None
    except socket.gaierror as exc:
        return False, False, (
            'MySQL host could not be resolved. Check DB_HOST in .env and verify DNS/network access. '
            f'Details: {exc}'
        )
    except Exception as exc:
        return False, False, (
            'MySQL connection failed. Check DB_HOST, DB_PORT, credentials, and SSL_CA. '
            f'Details: {exc}'
        )


def preflight_database_check():
    connected, ping_ok, error = ping_database()
    if connected and ping_ok:
        return True, 'Database connection verified.'

    return False, error or 'Database connection check failed.'


def executemany(query, params_list):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(query, params_list)
            return cursor.rowcount


def ensure_schema():
    statements = [
        """
        CREATE TABLE IF NOT EXISTS companies (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            registration_number VARCHAR(50) NOT NULL UNIQUE,
            api_key VARCHAR(64) UNIQUE,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(120) NOT NULL UNIQUE,
            password_hash VARCHAR(128) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'user',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            company_id INT NULL,
            INDEX idx_users_company_id (company_id),
            CONSTRAINT fk_users_company
                FOREIGN KEY (company_id) REFERENCES companies(id)
                ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
        """
        CREATE TABLE IF NOT EXISTS kyc_requests (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            company_id INT NULL,
            document_type VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            ocr_data JSON NULL,
            verification_date DATETIME NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_kyc_requests_user_id (user_id),
            INDEX idx_kyc_requests_company_id (company_id),
            CONSTRAINT fk_kyc_requests_user
                FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE,
            CONSTRAINT fk_kyc_requests_company
                FOREIGN KEY (company_id) REFERENCES companies(id)
                ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ]

    with get_connection() as connection:
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)