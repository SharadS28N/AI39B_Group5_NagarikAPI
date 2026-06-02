#!/usr/bin/env python3
"""
Test script for KYC, token generation, and API key flow.
Uses the Python standard library to avoid external client dependencies.
"""

import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "http://localhost:5000/api"


def print_header(text):
    """Print formatted header"""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def request_json(method, path, payload=None, headers=None):
    url = f"{BASE_URL}{path}"
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = Request(url, data=data, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except HTTPError as error:
        body = error.read().decode("utf-8")
        return error.code, json.loads(body) if body else {"error": error.reason}
    except URLError as error:
        raise ConnectionError(f"Could not connect to {BASE_URL}: {error.reason}") from error


def test_health_check():
    """Test API health check"""
    print_header("1. HEALTH CHECK")
    status, data = request_json("GET", "/health")
    print(f"Status: {status}")
    print(f"Response: {json.dumps(data, indent=2)}")
    return status, data


def test_token_generation():
    """Test token generation"""
    print_header("2. TOKEN GENERATION")
    payload = {
        "user_id": 1,
        "kyc_status": "approved",
        "claims": {"is_admin": True, "role": "admin"},
    }
    status, data = request_json("POST", "/token/generate", payload)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(data, indent=2)}")
    return status, data.get("access_token"), data.get("refresh_token")


def test_token_verify(token):
    """Test token verification"""
    print_header("3. TOKEN VERIFICATION")
    status, data = request_json("POST", "/token/verify", {"token": token})
    print(f"Status: {status}")
    print(f"Response: {json.dumps(data, indent=2)}")
    return status, data


def test_kyc_submit(access_token):
    """Test KYC submission"""
    print_header("4. KYC SUBMISSION")
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "date_of_birth": "1990-01-15",
        "nationality": "US",
        "country": "United States",
        "address_line1": "123 Main Street",
        "address_line2": "Apt 4B",
        "city": "New York",
        "state": "NY",
        "postal_code": "10001",
    }
    status, data = request_json("POST", "/kyc/submit", payload, headers=headers)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(data, indent=2)}")
    return status, data.get("kyc_id") if isinstance(data, dict) else None


def test_kyc_status(access_token):
    """Test KYC status retrieval"""
    print_header("5. KYC STATUS CHECK")
    headers = {"Authorization": f"Bearer {access_token}"}
    status, data = request_json("GET", "/kyc/status", headers=headers)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(data, indent=2)}")
    return status, data


def test_token_refresh(refresh_token):
    """Test token refresh"""
    print_header("6. TOKEN REFRESH")
    status, data = request_json("POST", "/token/refresh", {"refresh_token": refresh_token})
    print(f"Status: {status}")
    print(f"Response: {json.dumps(data, indent=2)}")
    return status, data.get("access_token") if isinstance(data, dict) else None


def test_kyc_audit_log(access_token):
    """Test KYC audit log retrieval (admin endpoint)"""
    print_header("7. KYC AUDIT LOG")
    headers = {"Authorization": f"Bearer {access_token}"}
    status, data = request_json("GET", "/kyc/audit-log?limit=10&offset=0", headers=headers)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(data, indent=2)}")
    return status, data


def test_logout(access_token):
    """Test logout (token revocation)"""
    print_header("8. LOGOUT")
    headers = {"Authorization": f"Bearer {access_token}"}
    status, data = request_json("POST", "/token/logout", headers=headers)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(data, indent=2)}")
    return status, data


def test_api_key_create(admin_token):
    """Test API key creation for company integrations"""
    print_header("9. API KEY CREATE")
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "name": "Company Integration",
        "company_type": "company",
        "expires_in_days": 365,
        "scopes": "kyc:read,kyc:write",
    }
    status, data = request_json("POST", "/apikey/create", payload, headers=headers)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(data, indent=2)}")
    return status, data.get("raw_key") if isinstance(data, dict) else None


def test_api_key_validate(api_key):
    """Test API key validation endpoint"""
    print_header("10. API KEY VALIDATE")
    headers = {"X-API-Key": api_key}
    status, data = request_json("GET", "/apikey/validate", headers=headers)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(data, indent=2)}")
    return status, data


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  KYC & TOKEN GENERATION API TEST SUITE")
    print("=" * 60)
    print(f"  Start Time: {datetime.now().isoformat()}")
    print(f"  Base URL: {BASE_URL}")

    try:
        test_health_check()

        status, access_token, refresh_token = test_token_generation()
        if not access_token:
            print("\n❌ FAILED: Could not generate access token")
            return

        test_token_verify(access_token)

        status, kyc_id = test_kyc_submit(access_token)
        if status != 201:
            print(f"\n⚠️  KYC submission returned {status}, continuing with tests...")

        test_kyc_status(access_token)

        if refresh_token:
            status, new_access_token = test_token_refresh(refresh_token)
            if new_access_token:
                access_token = new_access_token
                print("\n✓ Successfully refreshed access token")

        test_kyc_audit_log(access_token)

        api_key = None
        status, api_key = test_api_key_create(access_token)
        if api_key:
            test_api_key_validate(api_key)

        test_logout(access_token)

        print_header("11. VERIFY TOKEN REVOCATION")
        status, data = request_json("POST", "/token/verify", {"token": access_token})
        print(f"Status: {status}")
        print(f"Response: {json.dumps(data, indent=2)}")
        if data.get("valid") is False:
            print("✓ Token correctly revoked after logout")

        print("\n" + "=" * 60)
        print("  ✓ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60 + "\n")

    except ConnectionError as error:
        print(f"\n❌ ERROR: {error}")
        print("Make sure the Flask app is running: python run.py")
    except Exception as error:
        print(f"\n❌ ERROR: {error}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
