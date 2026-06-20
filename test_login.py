from app import create_app
from app.extensions import db
from app.models import User
from flask_login import current_user
import re

app = create_app()

with app.test_client() as client:
    # First, check if test user exists
    with app.app_context():
        user = User.query.filter_by(email='user@example.com').first()
        if not user:
            print("Test user not found!")
        else:
            print(f"Test user found: {user.email}")
    
    # Test GET login page
    print("\nTesting GET /auth/login...")
    response = client.get('/auth/login')
    print(f"Response status: {response.status_code}")
    
    # Extract CSRF token from HTML
    html = response.data.decode('utf-8')
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    if csrf_match:
        csrf_token = csrf_match.group(1)
        print(f"CSRF token found: {csrf_token[:20]}...")
    else:
        print("CSRF token NOT found in HTML!")
        print("HTML snippet:")
        print(html[:500])
        csrf_token = None
    
    # Try to login with CSRF token
    if csrf_token:
        print("\nTesting POST /auth/login with valid credentials and CSRF token...")
        response = client.post(
            '/auth/login',
            data={
                'email': 'user@example.com',
                'password': 'User123',
                'csrf_token': csrf_token
            },
            follow_redirects=True
        )
        print(f"Response status: {response.status_code}")
        
        # Check if user is authenticated
        with client.session_transaction() as sess:
            print(f"Session has user_id: {'_user_id' in sess}")
        
        # Check if we're on the home page
        print(f"Response contains 'Nagarik API': {'Nagarik API' in response.data.decode('utf-8')}")
