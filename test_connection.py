#!/usr/bin/env python3
"""
Diagnostic script to test MySQL connectivity and DNS resolution.
"""
import os
import socket
import sys
from dotenv import load_dotenv

load_dotenv()

def test_dns():
    """Test DNS resolution"""
    host = os.getenv('DB_HOST', 'nagarikapi-sharad-b099.g.aivencloud.com')
    print(f"\n[DNS Test] Attempting to resolve: {host}")
    try:
        ip = socket.gethostbyname(host)
        print(f"  ✓ Resolved to IP: {ip}")
        return True
    except socket.gaierror as e:
        print(f"  ✗ DNS resolution failed: {e}")
        return False

def test_port():
    """Test if port is accessible"""
    host = os.getenv('DB_HOST', 'nagarikapi-sharad-b099.g.aivencloud.com')
    port = int(os.getenv('DB_PORT', '12398'))
    print(f"\n[Port Test] Attempting connection to {host}:{port}")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    
    try:
        result = sock.connect_ex((host, port))
        if result == 0:
            print(f"  ✓ Port {port} is open")
            return True
        else:
            print(f"  ✗ Port {port} is closed or unreachable (code: {result})")
            return False
    except Exception as e:
        print(f"  ✗ Connection test failed: {e}")
        return False
    finally:
        sock.close()

def test_pymysql():
    """Test PyMySQL connection"""
    print(f"\n[PyMySQL Test] Attempting database connection")
    
    try:
        import pymysql
        
        config = {
            'host': os.getenv('DB_HOST'),
            'port': int(os.getenv('DB_PORT')),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'database': os.getenv('DB_NAME'),
            'charset': 'utf8mb4',
            'connect_timeout': 10,
        }
        
        port = int(os.getenv('DB_PORT'))
        if port == 12398 or os.getenv('SSL_CA'):
            config['ssl'] = {}  # Empty dict for SSL without strict verification
            print("  Using SSL (development mode)")
        
        print(f"  Connecting to {config['host']}:{config['port']} as {config['user']}")
        conn = pymysql.connect(**config)
        print("  ✓ Connection successful!")
        
        # Test query
        cursor = conn.cursor()
        cursor.execute('SELECT 1 AS test')
        result = cursor.fetchone()
        print(f"  ✓ Query test passed: {result}")
        
        conn.close()
        return True
    except socket.gaierror as e:
        print(f"  ✗ DNS error: {e}")
        return False
    except pymysql.OperationalError as e:
        print(f"  ✗ MySQL operational error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Connection failed: {type(e).__name__}: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("MySQL Connection Diagnostics")
    print("=" * 60)
    
    dns_ok = test_dns()
    if dns_ok:
        port_ok = test_port()
        if port_ok:
            test_pymysql()
    
    print("\n" + "=" * 60)
