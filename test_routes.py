
from app import create_app

app = create_app()

test_urls = [
    "/",
    "/auth/login",
    "/auth/register",
    "/about",
    "/contact",
    "/solutions",
    "/pricing",
    "/docs"
]

with app.test_client() as client:
    for url in test_urls:
        try:
            response = client.get(url)
            print(f"{url:20} -> {response.status_code}")
        except Exception as e:
            print(f"{url:20} -> ERROR: {type(e).__name__}: {e}")
