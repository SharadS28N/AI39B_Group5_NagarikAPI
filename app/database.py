import os
import socket
from contextlib import contextmanager

import pymysql
import sqlite3
from flask import current_app
from pymysql.cursors import DictCursor


def _using_mysql():
    cfg = current_app.config
    host = cfg.get('MYSQL_HOST')
    return bool(host)


def _connection_kwargs():
    config = current_app.config
    return {
        'host': config.get('MYSQL_HOST', '127.0.0.1'),
        'port': int(config.get('MYSQL_PORT', 3306)),
        'user': config.get('MYSQL_USER', ''),
        'password': config.get('MYSQL_PASSWORD', ''),
        'database': config.get('MYSQL_DATABASE', ''),
        'charset': 'utf8mb4',
        'cursorclass': DictCursor,
        'autocommit': False,
        'connect_timeout': 10,
    }


@contextmanager
def get_connection():
    """Yield a DB connection object. Uses MySQL when configured, else sqlite file fallback.

    The returned connection will commit on success and rollback on exception.
    """
    if _using_mysql():
        kwargs = _connection_kwargs()
        conn = pymysql.connect(**kwargs)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    else:
        db_path = current_app.config.get('SQLITE_PATH') or os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'nagarikapi.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            # Ensure foreign keys enabled
            conn.execute('PRAGMA foreign_keys = ON')
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _to_params(query, params):
    # For sqlite, replace %s placeholders with ?
    if _using_mysql():
        return query, params
    return query.replace('%s', '?'), params


def fetch_all(query, params=None):
    params = params or ()
    q, p = _to_params(query, params)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(q, p)
        rows = cur.fetchall()
        # For sqlite, convert sqlite3.Row to dicts
        if not _using_mysql():
            return [dict(r) for r in rows]
        return rows


def fetch_one(query, params=None):
    params = params or ()
    q, p = _to_params(query, params)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(q, p)
        row = cur.fetchone()
        if not _using_mysql() and row is not None:
            return dict(row)
        return row


def execute(query, params=None):
    params = params or ()
    q, p = _to_params(query, params)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(q, p)
        # sqlite returns lastrowid similarly
        return cur.lastrowid


def executemany(query, params_list):
    q, _ = _to_params(query, ())
    # convert params list for sqlite if necessary
    if _using_mysql():
        with get_connection() as conn:
            cur = conn.cursor()
            cur.executemany(q, params_list)
            return cur.rowcount
    else:
        # replace %s with ? already done in q
        with get_connection() as conn:
            cur = conn.cursor()
            cur.executemany(q, params_list)
            return cur.rowcount


def ping_database():
    try:
        if _using_mysql():
            row = fetch_one('SELECT 1 AS ok')
            return True, bool(row and (row.get('ok') == 1 or row.get('ok') == 1)), None
        else:
            # sqlite always available if file can be opened
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute('SELECT 1')
                _ = cur.fetchone()
            return True, True, None
    except pymysql.OperationalError as exc:
        msg = (
            f'MySQL OperationalError (host: {current_app.config.get("MYSQL_HOST")}, '
            f'port: {current_app.config.get("MYSQL_PORT")}). Details: {exc}'
        )
        return False, False, msg
    except socket.gaierror as exc:
        msg = (
            f'DNS resolution failed for {current_app.config.get("MYSQL_HOST")}. Error: {exc}'
        )
        return False, False, msg
    except Exception as exc:
        return False, False, str(exc)


def preflight_database_check():
    connected, ping_ok, error = ping_database()
    if connected and ping_ok:
        return True, 'Database connection verified.'
    return False, error or 'Database connection check failed.'


def ensure_schema():
    # Create minimal compatible schema for sqlite and mysql
    if _using_mysql():
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
    else:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                registration_number TEXT NOT NULL UNIQUE,
                api_key TEXT UNIQUE,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                company_id INTEGER NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS kyc_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                company_id INTEGER NULL,
                document_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                ocr_data TEXT NULL,
                verification_date TEXT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """,
        ]

    with get_connection() as connection:
        cur = connection.cursor()
        for statement in statements:
            cur.execute(statement)