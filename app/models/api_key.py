"""
API Key management for company-type clients.

Generates, stores (hashed), lists and revokes API keys.
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.database import get_connection


class APIKeyManager:
    HASH_ALGO = 'sha256'

    @staticmethod
    def _hash_key(raw_key: str) -> str:
        h = hashlib.new(APIKeyManager.HASH_ALGO)
        h.update(raw_key.encode('utf-8'))
        return h.hexdigest()

    @staticmethod
    def create_table():
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255),
                    company_type VARCHAR(100) NOT NULL,
                    key_hash VARCHAR(255) NOT NULL UNIQUE,
                    scopes TEXT,
                    created_by INT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME NULL,
                    revoked_at DATETIME NULL,
                    revoked_reason VARCHAR(255),
                    INDEX idx_company_type (company_type),
                    INDEX idx_created_by (created_by)
                )
            """)
            conn.commit()

    @staticmethod
    def generate_key() -> str:
        return secrets.token_urlsafe(32)

    @classmethod
    def create_api_key(cls, name: str, company_type: str, created_by: Optional[int] = None,
                       expires_in_days: Optional[int] = None, scopes: Optional[str] = None) -> Dict[str, Any]:
        raw = cls.generate_key()
        key_hash = cls._hash_key(raw)

        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO api_keys (name, company_type, key_hash, scopes, created_by, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (name, company_type, key_hash, scopes, created_by, expires_at)
            )
            api_id = cursor.lastrowid

        return {
            'id': api_id,
            'name': name,
            'company_type': company_type,
            'raw_key': raw,
            'scopes': scopes,
            'expires_at': expires_at.isoformat() + 'Z' if expires_at else None
        }

    @classmethod
    def revoke_key(cls, api_id: int, reason: Optional[str] = None):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE api_keys SET revoked_at = CURRENT_TIMESTAMP, revoked_reason = %s WHERE id = %s", (reason, api_id))
            conn.commit()

    @classmethod
    def list_keys(cls, company_type: Optional[str] = None, include_revoked: bool = False):
        with get_connection() as conn:
            cursor = conn.cursor()
            if company_type:
                if include_revoked:
                    cursor.execute("SELECT id, name, company_type, scopes, created_by, created_at, expires_at, revoked_at FROM api_keys WHERE company_type = %s", (company_type,))
                else:
                    cursor.execute("SELECT id, name, company_type, scopes, created_by, created_at, expires_at, revoked_at FROM api_keys WHERE company_type = %s AND revoked_at IS NULL", (company_type,))
            else:
                if include_revoked:
                    cursor.execute("SELECT id, name, company_type, scopes, created_by, created_at, expires_at, revoked_at FROM api_keys")
                else:
                    cursor.execute("SELECT id, name, company_type, scopes, created_by, created_at, expires_at, revoked_at FROM api_keys WHERE revoked_at IS NULL")

            results = []
            for r in cursor.fetchall():
                if isinstance(r, dict):
                    results.append({
                        'id': r['id'],
                        'name': r['name'],
                        'company_type': r['company_type'],
                        'scopes': r['scopes'],
                        'created_by': r['created_by'],
                        'created_at': r['created_at'].isoformat() + 'Z' if r['created_at'] else None,
                        'expires_at': r['expires_at'].isoformat() + 'Z' if r['expires_at'] else None,
                        'revoked_at': r['revoked_at'].isoformat() + 'Z' if r['revoked_at'] else None
                    })
                else:
                    results.append({
                        'id': r[0],
                        'name': r[1],
                        'company_type': r[2],
                        'scopes': r[3],
                        'created_by': r[4],
                        'created_at': r[5].isoformat() + 'Z' if r[5] else None,
                        'expires_at': r[6].isoformat() + 'Z' if r[6] else None,
                        'revoked_at': r[7].isoformat() + 'Z' if r[7] else None
                    })

            return results

    @classmethod
    def validate_key(cls, raw_key: str) -> Optional[Dict[str, Any]]:
        key_hash = cls._hash_key(raw_key)
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, company_type, scopes, created_by, created_at, expires_at, revoked_at FROM api_keys WHERE key_hash = %s LIMIT 1", (key_hash,))
            row = cursor.fetchone()
            if not row:
                return None

            # Normalize row
            if isinstance(row, dict):
                expires_at = row['expires_at']
                revoked_at = row['revoked_at']
            else:
                expires_at = row[6]
                revoked_at = row[7]

            if revoked_at:
                return None
            if expires_at and datetime.utcnow() > expires_at:
                return None

            return {
                'id': row[0] if not isinstance(row, dict) else row['id'],
                'name': row[1] if not isinstance(row, dict) else row['name'],
                'company_type': row[2] if not isinstance(row, dict) else row['company_type'],
                'scopes': row[3] if not isinstance(row, dict) else row['scopes']
            }

    @staticmethod
    def get_token_label(api_id: int) -> str:
        return f"api_key:{api_id}"
