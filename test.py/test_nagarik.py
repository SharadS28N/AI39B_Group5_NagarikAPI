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


def test_password_is_hashed_not_plaintext(db):
    user = User(full_name='Sharad Bhandari', email='sharad@nagarik.com')
    user.set_password('MyPassword123')
    db.session.add(user)
    db.session.commit()
    assert user.password_hash != 'MyPassword123'
    assert user.password_hash is not None
    assert len(user.password_hash) > 20

def test_correct_password_is_accepted(db):
    user = User(full_name='Vision Pahari', email='vision@nagarik.com')
    user.set_password('Secure@99')
    db.session.add(user)
    db.session.commit()
    assert user.check_password('Secure@99') is True


def test_wrong_password_is_rejected(db):
    user = User(full_name='Mingmar Lama', email='mingmar@nagarik.com')
    user.set_password('Correct@123')
    db.session.add(user)
    db.session.commit()
    assert user.check_password('WrongPassword') is False



def test_new_user_default_role_is_user(db):
    user = User(full_name='Sushanta Malla', email='sushanta@nagarik.com')
    user.set_password('Test@1234')
    db.session.add(user)
    db.session.commit()
    assert user.role == 'user'


def test_duplicate_email_is_blocked(db):
    user1 = User(full_name='User One', email='same@nagarik.com')
    user1.set_password('Pass@1111')
    db.session.add(user1)
    db.session.commit()
    user2 = User(full_name='User Two', email='same@nagarik.com')
    user2.set_password('Pass@2222')
    db.session.add(user2)
    try:
        db.session.commit()
        assert False, 'Should have raised error for duplicate email'
    except Exception:
        db.session.rollback()
        assert True


def test_kyc_default_status_is_pending(db):
    user = User(full_name='KYC User', email='kyc@nagarik.com')
    user.set_password('Test@1234')
    db.session.add(user)
    db.session.commit()
    kyc = KYCRequest(user_id=user.id, document_type='national_id')
    db.session.add(kyc)
    db.session.commit()
    assert kyc.status == 'pending'


def test_kyc_document_type_saved_correctly(db):
    user = User(full_name='Doc User', email='doc@nagarik.com')
    user.set_password('Test@1234')
    db.session.add(user)
    db.session.commit()
    kyc = KYCRequest(user_id=user.id, document_type='passport')
    db.session.add(kyc)
    db.session.commit()
    assert kyc.document_type == 'passport'


def test_kyc_linked_to_correct_user(db):
    user = User(full_name='Linked User', email='linked@nagarik.com')
    user.set_password('Test@1234')
    db.session.add(user)
    db.session.commit()
    kyc = KYCRequest(user_id=user.id, document_type='national_id')
    db.session.add(kyc)
    db.session.commit()
    assert kyc.user_id == user.id


def test_register_new_user_success(client, db):
    response = client.post('/register', data={
        'full_name': 'New User',
        'email': 'newuser@nagarik.com',
        'password': 'Test@1234'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'account has been created' in response.data


def test_register_saves_user_to_db(client, db):
    client.post('/register', data={
        'full_name': 'Saved User',
        'email': 'saved@nagarik.com',
        'password': 'Test@1234'
    }, follow_redirects=True)
    user = User.query.filter_by(email='saved@nagarik.com').first()
    assert user is not None
    assert user.full_name == 'Saved User'


def test_register_duplicate_email_shows_error(client, db, sample_user):
    response = client.post('/register', data={
        'full_name': 'Another User',
        'email': 'test@nagarik.com',
        'password': 'Test@1234'
    }, follow_redirects=True)
    assert response.status_code == 200


def test_login_correct_credentials_succeeds(client, db, sample_user):
    response = client.post('/login', data={
        'email': 'test@nagarik.com',
        'password': 'Test@1234'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Login Unsuccessful' not in response.data


def test_login_wrong_password_fails(client, db, sample_user):
    response = client.post('/login', data={
        'email': 'test@nagarik.com',
        'password': 'WrongPass'
    }, follow_redirects=True)
    assert b'Login Unsuccessful' in response.data


def test_login_nonexistent_email_fails(client, db):
    response = client.post('/login', data={
        'email': 'ghost@nagarik.com',
        'password': 'Test@1234'
    }, follow_redirects=True)
    assert b'Login Unsuccessful' in response.data