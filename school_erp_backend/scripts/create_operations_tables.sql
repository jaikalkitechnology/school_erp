-- Phase 28 operations tables.
--
-- Paste this into MySQL if `alembic upgrade head` isn't practical.
-- Every table uses IF NOT EXISTS so it is safe to re-run.
--
--   mysql -u <user> -p school_erp_db < scripts/create_operations_tables.sql
--
-- Or paste the whole file into a MySQL console.

-- ============================================================
-- 1. Admissions
-- ============================================================
CREATE TABLE IF NOT EXISTS admission_inquiries (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    child_full_name VARCHAR(180) NOT NULL,
    child_dob DATE NULL,
    class_applying_for VARCHAR(40) NULL,
    parent_name VARCHAR(180) NULL,
    parent_phone VARCHAR(20) NULL,
    parent_email VARCHAR(180) NULL,
    source VARCHAR(40) NULL,
    stage VARCHAR(20) NOT NULL DEFAULT 'enquiry',
    notes TEXT NULL,
    test_date DATE NULL,
    test_score DECIMAL(5,2) NULL,
    student_id INT NULL,
    handled_by_user_id INT NULL,
    INDEX ix_adm_inq_tenant_stage (tenant_id, stage),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL,
    FOREIGN KEY (handled_by_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 2. Finance — vendors + expenses
-- ============================================================
CREATE TABLE IF NOT EXISTS vendors (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    name VARCHAR(180) NOT NULL,
    contact_person VARCHAR(120) NULL,
    phone VARCHAR(20) NULL,
    email VARCHAR(180) NULL,
    gst_number VARCHAR(40) NULL,
    address TEXT NULL,
    notes TEXT NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    UNIQUE KEY uq_vendor_name (tenant_id, name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS expenses (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    category VARCHAR(80) NOT NULL,
    vendor_id INT NULL,
    amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    spent_on DATE NOT NULL,
    paid_from VARCHAR(40) NULL,
    invoice_ref VARCHAR(80) NULL,
    description TEXT NULL,
    status VARCHAR(12) NOT NULL DEFAULT 'pending',
    created_by_user_id INT NULL,
    approved_by_user_id INT NULL,
    approved_at DATETIME NULL,
    INDEX ix_expenses_tenant_date (tenant_id, spent_on),
    FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (approved_by_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 3. Payroll — salary structures + payslips
-- ============================================================
CREATE TABLE IF NOT EXISTS salary_structures (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    user_id INT NOT NULL,
    basic DECIMAL(12,2) NOT NULL DEFAULT 0,
    hra DECIMAL(12,2) NOT NULL DEFAULT 0,
    allowances JSON NOT NULL,
    deductions JSON NOT NULL,
    effective_from DATE NOT NULL,
    notes TEXT NULL,
    INDEX ix_salary_user (tenant_id, user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS payslips (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    user_id INT NOT NULL,
    period VARCHAR(7) NOT NULL,
    basic DECIMAL(12,2) NOT NULL DEFAULT 0,
    hra DECIMAL(12,2) NOT NULL DEFAULT 0,
    other_earnings DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_deductions DECIMAL(12,2) NOT NULL DEFAULT 0,
    net_pay DECIMAL(12,2) NOT NULL DEFAULT 0,
    breakdown JSON NULL,
    status VARCHAR(12) NOT NULL DEFAULT 'draft',
    paid_on DATE NULL,
    UNIQUE KEY uq_payslip_user_period (tenant_id, user_id, period),
    INDEX ix_payslip_period (tenant_id, period),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 4. Inventory
-- ============================================================
CREATE TABLE IF NOT EXISTS inventory_items (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    code VARCHAR(40) NOT NULL,
    name VARCHAR(180) NOT NULL,
    category VARCHAR(80) NULL,
    unit VARCHAR(20) NOT NULL DEFAULT 'pcs',
    on_hand INT NOT NULL DEFAULT 0,
    reorder_level INT NOT NULL DEFAULT 0,
    unit_cost DECIMAL(12,2) NOT NULL DEFAULT 0,
    location VARCHAR(80) NULL,
    notes TEXT NULL,
    UNIQUE KEY uq_inv_item_code (tenant_id, code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS inventory_movements (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    item_id INT NOT NULL,
    kind VARCHAR(10) NOT NULL DEFAULT 'in',
    quantity INT NOT NULL,
    reference VARCHAR(120) NULL,
    occurred_on DATE NOT NULL,
    by_user_id INT NULL,
    notes TEXT NULL,
    INDEX ix_inv_mov_item (tenant_id, item_id),
    FOREIGN KEY (item_id) REFERENCES inventory_items(id) ON DELETE CASCADE,
    FOREIGN KEY (by_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 5. Visitors
-- ============================================================
CREATE TABLE IF NOT EXISTS visitor_logs (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    full_name VARCHAR(180) NOT NULL,
    phone VARCHAR(20) NULL,
    company VARCHAR(180) NULL,
    purpose VARCHAR(180) NULL,
    host_user_id INT NULL,
    id_proof_type VARCHAR(40) NULL,
    id_proof_ref VARCHAR(80) NULL,
    badge_no VARCHAR(20) NULL,
    photo_url VARCHAR(500) NULL,
    checked_in_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    checked_out_at DATETIME NULL,
    checked_in_by_user_id INT NULL,
    notes TEXT NULL,
    INDEX ix_visitor_tenant_in (tenant_id, checked_in_at),
    FOREIGN KEY (host_user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (checked_in_by_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 6. Health
-- ============================================================
CREATE TABLE IF NOT EXISTS health_records (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    student_id INT NOT NULL,
    kind VARCHAR(20) NOT NULL DEFAULT 'visit',
    title VARCHAR(180) NOT NULL,
    description TEXT NULL,
    occurred_on DATE NOT NULL,
    severity VARCHAR(20) NULL,
    treatment TEXT NULL,
    medication TEXT NULL,
    follow_up_on DATE NULL,
    by_user_id INT NULL,
    INDEX ix_health_student (tenant_id, student_id),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (by_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 7. Certificates
-- ============================================================
CREATE TABLE IF NOT EXISTS certificate_templates (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    code VARCHAR(40) NOT NULL,
    name VARCHAR(120) NOT NULL,
    body_html TEXT NOT NULL,
    signatory_label VARCHAR(120) NULL,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    UNIQUE KEY uq_cert_tpl_code (tenant_id, code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS issued_certificates (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    template_code VARCHAR(40) NOT NULL,
    student_id INT NULL,
    for_name VARCHAR(180) NOT NULL,
    reference_no VARCHAR(40) NOT NULL,
    issued_on DATE NOT NULL,
    issued_by_user_id INT NULL,
    rendered_body TEXT NOT NULL,
    notes TEXT NULL,
    INDEX ix_issued_cert_student (tenant_id, student_id),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL,
    FOREIGN KEY (issued_by_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 8. Discipline
-- ============================================================
CREATE TABLE IF NOT EXISTS discipline_incidents (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    student_id INT NOT NULL,
    occurred_on DATE NOT NULL,
    location VARCHAR(80) NULL,
    severity VARCHAR(12) NOT NULL DEFAULT 'minor',
    headline VARCHAR(180) NOT NULL,
    description TEXT NULL,
    action_taken TEXT NULL,
    reported_by_user_id INT NULL,
    parent_informed TINYINT(1) NOT NULL DEFAULT 0,
    INDEX ix_discipline_student (tenant_id, student_id),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (reported_by_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 9. Notice board
-- ============================================================
CREATE TABLE IF NOT EXISTS notices (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    title VARCHAR(180) NOT NULL,
    body TEXT NOT NULL,
    audience VARCHAR(20) NOT NULL DEFAULT 'all',
    is_pinned TINYINT(1) NOT NULL DEFAULT 0,
    published_at DATETIME NULL,
    expires_at DATETIME NULL,
    attachments JSON NOT NULL,
    author_user_id INT NULL,
    INDEX ix_notice_pub (tenant_id, published_at),
    FOREIGN KEY (author_user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 10. Alumni
-- ============================================================
CREATE TABLE IF NOT EXISTS alumni (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    student_id INT NULL,
    full_name VARCHAR(180) NOT NULL,
    graduation_year INT NOT NULL,
    current_role VARCHAR(180) NULL,
    current_company VARCHAR(180) NULL,
    email VARCHAR(180) NULL,
    phone VARCHAR(20) NULL,
    city VARCHAR(80) NULL,
    linkedin_url VARCHAR(500) NULL,
    notes TEXT NULL,
    INDEX ix_alumni_year (tenant_id, graduation_year),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- 11. Sports
-- ============================================================
CREATE TABLE IF NOT EXISTS sports_houses (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    name VARCHAR(80) NOT NULL,
    color VARCHAR(20) NULL,
    motto VARCHAR(180) NULL,
    captain_student_id INT NULL,
    points INT NOT NULL DEFAULT 0,
    UNIQUE KEY uq_sports_house_name (tenant_id, name),
    FOREIGN KEY (captain_student_id) REFERENCES students(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sports_events (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    name VARCHAR(180) NOT NULL,
    kind VARCHAR(20) NOT NULL DEFAULT 'tournament',
    sport VARCHAR(80) NULL,
    starts_on DATE NOT NULL,
    ends_on DATE NULL,
    venue VARCHAR(120) NULL,
    winner_house_id INT NULL,
    notes TEXT NULL,
    INDEX ix_sports_event_date (tenant_id, starts_on),
    FOREIGN KEY (winner_house_id) REFERENCES sports_houses(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Mark the Alembic revision as applied so future `upgrade head`
-- doesn't try to re-create the same tables. Only run this after
-- verifying all 16 tables above created successfully.
--
-- If your alembic_version row already exists, replace INSERT with
-- an UPDATE:
--   UPDATE alembic_version SET version_num = 'a5c2d9e11f28';
-- ============================================================
INSERT INTO alembic_version (version_num) VALUES ('a5c2d9e11f28')
ON DUPLICATE KEY UPDATE version_num = 'a5c2d9e11f28';
