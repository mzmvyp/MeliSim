-- Align with JPA UserType.ADMIN (Docker init.sql may already include ADMIN).
ALTER TABLE users MODIFY COLUMN user_type ENUM('BUYER', 'SELLER', 'ADMIN') NOT NULL DEFAULT 'BUYER';
