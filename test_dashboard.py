from app import create_app
import re

app = create_app()

with app.test_client() as client:
    # First, login as company admin
    login_page = client.get('/auth/login')
    html = login_page.data.decode('utf-8')
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    csrf_token = csrf_match.group(1) if csrf_match else None
    
    # Post login
    client.post(
        '/auth/login',
        data={
            'email': 'hr@banknepal.com',
            'password': 'CompanyAdmin123',
            'csrf_token': csrf_token
        },
        follow_redirects=True
    )
    
    # Now access company dashboard
    response = client.get('/dashboard/company')
    print(f"Company dashboard status: {response.status_code}")
    
    if response.status_code == 200:
        content = response.data.decode('utf-8')
        print("\nChecking dashboard content:")
        print(f"Company name found: {'Bank Nepal' in content}")
        print(f"API keys found: {'API Key' in content}")
        print(f"Cases table found: {'Case Ref' in content}")
        print(f"Stats found: {'Total Cases' in content}")
