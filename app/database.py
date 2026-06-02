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
        'connect_timeout': 10,
    }

    # Enable SSL for Aiven (development mode)
    # For Aiven port 12398, SSL is required but cert verification can be relaxed
    if config.get('MYSQL_PORT') == 12398 or config.get('MYSQL_SSL_CA'):
        kwargs['ssl'] = {}  # Empty dict enables SSL without strict verification

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
        msg = (
            f'DNS resolution failed for {current_app.config.get("MYSQL_HOST")}. '
            'Check network access, DNS settings, and that the hostname is correct. '
            f'Error: {exc}'
        )
        return False, False, msg
    except pymysql.OperationalError as exc:
        msg = (
            f'MySQL OperationalError (host: {current_app.config.get("MYSQL_HOST")}, '
            f'port: {current_app.config.get("MYSQL_PORT")}). '
            'Check credentials, port, SSL settings, and firewall rules. '
            f'Details: {exc}'
        )
        return False, False, msg
    except Exception as exc:
        msg = (
            'MySQL connection failed. Check DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, SSL_CA. '
            f'Details: {type(exc).__name__}: {exc}'
        )
        return False, False, msg


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