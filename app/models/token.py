"""
Token generation and management system.
Handles JWT tokens for authentication and session management.
"""

import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.database import get_connection


class TokenManager:
    """Manages token generation, validation, and revocation"""
    
    # Token configuration
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    @classmethod
    def _get_secret_key(cls) -> str:
        """Get secret key from environment"""
        secret = os.getenv('SECRET_KEY')
        if not secret:
            raise ValueError("SECRET_KEY not found in environment variables")
        return secret
    
    @staticmethod
    def create_table():
        """Create token management table"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                
                # Token blacklist table (for token revocation)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS token_blacklist (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        token_jti VARCHAR(500) NOT NULL UNIQUE,
                        user_id INT NOT NULL,
                        token_type VARCHAR(50),
                        revoked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        revoke_reason VARCHAR(255),
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        INDEX idx_user_id (user_id),
                        INDEX idx_jti (token_jti)
                    )
                """)
                
                # Token usage audit
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS token_audit (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT NOT NULL,
                        token_jti VARCHAR(500),
                        action VARCHAR(100),
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        INDEX idx_user_id (user_id),
                        INDEX idx_action (action)
                    )
                """)
                
            return True
        except Exception as e:
            if "already exists" not in str(e):
                raise
            return True
    
    @classmethod
    def generate_access_token(cls, user_id: int, additional_claims: Dict[str, Any] = None) -> str:
        """
        Generate JWT access token
        
        Args:
            user_id: User ID
            additional_claims: Additional claims to include in token
        
        Returns:
            Encoded JWT token
        """
        now = datetime.utcnow()
        expires = now + timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            'user_id': user_id,
            'token_type': 'access',
            'iat': now,
            'exp': expires,
            'jti': jwt.utils.base64url_encode(os.urandom(16)).decode('utf-8')
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, cls._get_secret_key(), algorithm=cls.ALGORITHM)
        return token
    
    @classmethod
    def generate_refresh_token(cls, user_id: int, additional_claims: Dict[str, Any] = None) -> str:
        """
        Generate JWT refresh token
        
        Args:
            user_id: User ID
        
        Returns:
            Encoded JWT token
        """
        now = datetime.utcnow()
        expires = now + timedelta(days=cls.REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            'user_id': user_id,
            'token_type': 'refresh',
            'iat': now,
            'exp': expires,
            'jti': jwt.utils.base64url_encode(os.urandom(16)).decode('utf-8')
        }

        if additional_claims:
            payload.update(additional_claims)
        
        token = jwt.encode(payload, cls._get_secret_key(), algorithm=cls.ALGORITHM)
        return token
    
    @classmethod
    def generate_token_pair(cls, user_id: int, kyc_status: str = None, additional_claims: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Generate both access and refresh tokens
        
        Args:
            user_id: User ID
            kyc_status: Optional KYC verification status to include in claims
        
        Returns:
            Dictionary with 'access_token' and 'refresh_token'
        """
        claims = dict(additional_claims or {})
        if kyc_status:
            claims['kyc_status'] = kyc_status
        
        access_token = cls.generate_access_token(user_id, claims)
        refresh_token = cls.generate_refresh_token(user_id, claims)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': cls.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    @classmethod
    def verify_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
        
        Returns:
            Decoded payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, cls._get_secret_key(), algorithms=[cls.ALGORITHM])
            
            # Check if token is revoked
            if not cls._is_token_revoked(payload.get('jti')):
                return payload
            return None
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @classmethod
    def refresh_access_token(cls, refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Generate new access token from refresh token
        
        Args:
            refresh_token: Valid refresh token
        
        Returns:
            New token pair if valid, None otherwise
        """
        payload = cls.verify_token(refresh_token)
        if not payload or payload.get('token_type') != 'refresh':
            return None
        
        user_id = payload.get('user_id')
        claims = {
            key: value
            for key, value in payload.items()
            if key not in {'user_id', 'token_type', 'iat', 'exp', 'jti'}
        }
        return cls.generate_token_pair(user_id, payload.get('kyc_status'), claims)
    
    @staticmethod
    def revoke_token(token_jti: str, user_id: int, reason: str = None):
        """
        Revoke a token by adding it to blacklist
        
        Args:
            token_jti: Token JTI claim
            user_id: User ID
            reason: Reason for revocation
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO token_blacklist (token_jti, user_id, revoke_reason)
                VALUES (%s, %s, %s)
            """, (token_jti, user_id, reason))
    
    @staticmethod
    def logout(user_id: int, token_jti: str = None):
        """
        Logout user by revoking tokens
        
        Args:
            user_id: User ID
            token_jti: Specific token JTI to revoke (if None, revoke all)
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            if token_jti:
                cursor.execute("""
                    INSERT INTO token_blacklist (token_jti, user_id, revoke_reason)
                    VALUES (%s, %s, 'logout')
                """, (token_jti, user_id))
            else:
                # Revoke all user tokens
                cursor.execute("""
                    INSERT INTO token_blacklist (token_jti, user_id, revoke_reason)
                    SELECT jti, %s, 'logout'
                    FROM token_audit
                    WHERE user_id = %s AND action = 'token_issued'
                """, (user_id, user_id))
    
    @staticmethod
    def log_token_usage(user_id: int, token_jti: str, action: str, 
                       ip_address: str = None, user_agent: str = None):
        """Log token usage for audit trail"""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO token_audit (user_id, token_jti, action, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, token_jti, action, ip_address, user_agent))
    
    @staticmethod
    def _is_token_revoked(token_jti: str) -> bool:
        """Check if token is in blacklist"""
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM token_blacklist WHERE token_jti = %s LIMIT 1", (token_jti,))
                result = cursor.fetchone()
                return result is not None
        except:
            return True

    @classmethod
    def get_token_jti(cls, token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, cls._get_secret_key(), algorithms=[cls.ALGORITHM], options={"verify_exp": False})
            return payload.get('jti')
        except Exception:
            return None
