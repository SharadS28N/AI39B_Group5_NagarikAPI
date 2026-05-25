-- NagarikAPI MySQL Schema

CREATE DATABASE IF NOT EXISTS nagarikapi;
USE nagarikapi;

-- Companies Table
CREATE TABLE IF NOT EXISTS companies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    registration_number VARCHAR(50) UNIQUE NOT NULL,
    api_key VARCHAR(64) UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(128) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) DEFAULT 'user', -- 'admin', 'user', 'company_admin'
    company_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL
);

-- KYC Requests Table
CREATE TABLE IF NOT EXISTS kyc_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    company_id INT,
    document_type VARCHAR(20) NOT NULL, -- 'national_id', 'passport'
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    ocr_data JSON,
    verification_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL
);

-- Initial Admin (Optional)
-- INSERT INTO users (email, password_hash, full_name, role) VALUES ('admin@nagarikapi.com.np', '...', 'System Admin', 'admin');
