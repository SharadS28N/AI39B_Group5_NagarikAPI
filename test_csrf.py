from app import create_app
from flask import render_template_string

app = create_app()

with app.test_request_context('/auth/login'):
    print("Testing csrf_token()...")
    try:
        token = render_template_string('{{ csrf_token() }}')
        print(f"csrf_token() returns: {token}")
        print(f"Type: {type(token)}")
    except Exception as e:
        print(f"Error: {e}")
