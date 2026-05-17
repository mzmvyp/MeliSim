-- Run manually against an EXISTING MeliSim MySQL volume (init.sql only runs on first DB creation).
-- Usage: docker exec -i melisim-mysql mysql -uroot -pmelisim123 melisim < infra/mysql/upgrade-admin-role-and-seed.sql

ALTER TABLE users MODIFY user_type ENUM('BUYER', 'SELLER', 'ADMIN') NOT NULL DEFAULT 'BUYER';

INSERT INTO users (name, email, password_hash, user_type)
VALUES (
    'Administrador',
    'admin@melisim.com',
    '$2b$10$4o.hD2stzjHS3cPGWW2aM.p/qViRI7PqPyAr3tlWLBwD7AxLYU/jO',
    'ADMIN'
)
ON DUPLICATE KEY UPDATE name = VALUES(name), password_hash = VALUES(password_hash), user_type = 'ADMIN';
