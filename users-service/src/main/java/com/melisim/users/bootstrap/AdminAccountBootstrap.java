package com.melisim.users.bootstrap;

import com.melisim.users.model.User;
import com.melisim.users.model.UserType;
import com.melisim.users.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.core.annotation.Order;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.Optional;

/**
 * Ensures the seeded admin account uses a real BCrypt hash. Plain text or truncated
 * SQL (e.g. shell stripping {@code $}) triggers Spring's "Encoded password does not look like BCrypt".
 */
@Component
@Order(100)
public class AdminAccountBootstrap implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(AdminAccountBootstrap.class);

    private final UserRepository users;
    private final PasswordEncoder encoder;

    @Value("${melisim.admin.email:admin@melisim.com}")
    private String adminEmail;

    @Value("${melisim.admin.password:Admin00@@}")
    private String adminPassword;

    public AdminAccountBootstrap(UserRepository users, PasswordEncoder encoder) {
        this.users = users;
        this.encoder = encoder;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        Optional<User> existing = users.findByEmail(adminEmail);
        if (existing.isEmpty()) {
            User u = new User();
            u.setName("Administrador");
            u.setEmail(adminEmail);
            u.setPasswordHash(encoder.encode(adminPassword));
            u.setUserType(UserType.ADMIN);
            users.save(u);
            log.info("Created seeded admin user {}", adminEmail);
            return;
        }

        User u = existing.get();
        if (needsRehash(u.getPasswordHash())) {
            u.setPasswordHash(encoder.encode(adminPassword));
            if (u.getUserType() != UserType.ADMIN) {
                u.setUserType(UserType.ADMIN);
            }
            users.save(u);
            log.warn("Repaired password hash for {} (stored value was not valid BCrypt)", adminEmail);
        }
    }

    private static boolean needsRehash(String stored) {
        if (stored == null || stored.isBlank()) {
            return true;
        }
        return !stored.startsWith("$2a$") && !stored.startsWith("$2b$") && !stored.startsWith("$2y$");
    }
}
