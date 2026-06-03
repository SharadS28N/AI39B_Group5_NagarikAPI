import pytest
from app import create_app, db as _db
from app.models import User, Company, KYCRequest


@pytest.fixture(scope='session')
def app():
    flask_app = create_app()
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


@pytest.fixture(scope='function')
def db(app):
    with app.app_context():
        yield _db
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function')
def sample_user(db):
    user = User(full_name='Test User', email='test@nagarik.com')
    user.set_password('Test@1234')
    db.session.add(user)
    db.session.commit()
    return user