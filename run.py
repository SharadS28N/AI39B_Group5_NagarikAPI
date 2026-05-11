from run import create_app
import os

app = create_app()

def main():
    debug = os.getenv('FLASK_DEBUG', '').strip().lower() in {'1', 'true', 'yes', 'on'}
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('PORT', '5000'))

    app.run(host=host, port=port, debug=debug, use_reloader=debug)

if __name__ == '__main__':
    main()