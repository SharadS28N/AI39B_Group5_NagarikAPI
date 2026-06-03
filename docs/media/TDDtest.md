# Nagarik API — TDD Test Report

**Module:** ST4005CMD Integrative Project  
**Sprint:** 1 & 2  
**Tester:** Bimit Shrestha  
**Date:** June 2026  
**Methodology:** Test Driven Development — Red Green Refactor  
**Test Runner:** pytest 9.0.3  
**Test Database:** SQLite in-memory — real MySQL database never touched  

---

## What is TDD

TDD means writing tests before writing code.
Every test follows three steps:

- RED — write a failing test first
- GREEN — write code to make it pass
- REFACTOR — clean up the code

---

## Tools Used

| Tool | Version | Purpose |
|------|---------|---------|
| pytest | 9.0.3 | Run the tests |
| pytest-flask | 1.3.0 | Flask test client support |
| SQLite in-memory | built-in | Fake database for testing |
| Flask | 3.1.3 | Web framework being tested |
| Flask-Bcrypt | 1.0.1 | Password hashing |

---

## Test File Location

test.py/test_nagarik.py

---

## Batch 1 — User Model Tests

Testing password hashing, role defaults, and email uniqueness from app/models/__init__.py

| # | Test Name | What It Checks | Result |
|---|-----------|----------------|--------|
| 1 | test_password_is_hashed_not_plaintext | Password never stored as plain text | PASSED |
| 2 | test_correct_password_is_accepted | Correct password returns True | PASSED |
| 3 | test_wrong_password_is_rejected | Wrong password returns False | PASSED |
| 4 | test_new_user_default_role_is_user | New user role defaults to user | PASSED |
| 5 | test_duplicate_email_is_blocked | Same email cannot register twice | PASSED |

---

## Batch 2 — KYC Model Tests

Testing KYC request creation and data integrity from app/models/__init__.py

| # | Test Name | What It Checks | Result |
|---|-----------|----------------|--------|
| 6 | test_kyc_default_status_is_pending | New KYC defaults to pending | PASSED |
| 7 | test_kyc_document_type_saved_correctly | Document type saved as submitted | PASSED |
| 8 | test_kyc_linked_to_correct_user | KYC linked to correct user ID | PASSED |

---

## Batch 3 — Auth Route Tests

Testing register, login, logout routes from app/routes/auth.py

| # | Test Name | What It Checks | Result |
|---|-----------|----------------|--------|
| 9 | test_register_new_user_success | Valid registration shows success | PASSED |
| 10 | test_register_saves_user_to_db | Registered user exists in database | PASSED |
| 11 | test_register_duplicate_email_shows_error | Duplicate email is blocked | PASSED |
| 12 | test_login_correct_credentials_succeeds | Correct login works | PASSED |
| 13 | test_login_wrong_password_fails | Wrong password shows error | PASSED |
| 14 | test_login_nonexistent_email_fails | Unknown email shows error | PASSED |

---

## Batch 4 — Company Model Tests

Testing company creation and uniqueness from app/models/__init__.py

| # | Test Name | What It Checks | Result |
|---|-----------|----------------|--------|
| 15 | test_company_created_successfully | Company saved with correct data | PASSED |
| 16 | test_company_registration_number_is_unique | Duplicate reg number blocked | PASSED |

---

## Final Results

| Total Tests | Passed | Failed | Warnings |
|-------------|--------|--------|----------|
| 16 | 16 | 0 | 20 (SQLAlchemy deprecation — not our code) |

---

## TDD Cycle Summary

| Commit | Test Added | Status |
|--------|-----------|--------|
| 1 | requirements.txt updated | DONE |
| 2 | fixtures setup | DONE |
| 3 | test_password_is_hashed_not_plaintext | PASSED |
| 4 | test_correct_password_is_accepted | PASSED |
| 5 | test_wrong_password_is_rejected | PASSED |
| 6 | test_new_user_default_role_is_user | PASSED |
| 7 | test_duplicate_email_is_blocked | PASSED |
| 8 | test_kyc_default_status_is_pending | PASSED |
| 9 | test_kyc_document_type_saved_correctly | PASSED |
| 10 | test_kyc_linked_to_correct_user | PASSED |
| 11 | test_register_new_user_success | PASSED |
| 12 | test_register_saves_user_to_db | PASSED |
| 13 | test_register_duplicate_email_shows_error | PASSED |
| 14 | test_login_correct_credentials_succeeds | PASSED |
| 15 | test_login_wrong_password_fails | PASSED |
| 16 | test_login_nonexistent_email_fails | PASSED |
| 17 | test_company_created_successfully | PASSED |
| 18 | test_company_registration_number_is_unique | PASSED |

---

## Notes

- All tests use SQLite in-memory — real database never touched
- All tests written following TDD Red Green Refactor cycle
- Each test committed separately for full traceability
- 20 warnings are from SQLAlchemy internal code — not our code