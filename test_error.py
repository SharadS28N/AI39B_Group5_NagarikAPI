
from app import create_app
import traceback

app = create_app()

with app.test_client() as client:
    try:
        print("Testing / ...")
        response = client.get('/')
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"\nFirst 2000 chars of data:\n{response.data[:2000]}\n")
        
        print("Testing /static/css/globals.css ...")
        css = client.get('/static/css/globals.css')
        print(f"CSS status: {css.status_code}")
        
        print("Testing /static/img/logo.svg ...")
        logo = client.get('/static/img/logo.svg')
        print(f"Logo status: {logo.status_code}")
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        traceback.print_exc()
