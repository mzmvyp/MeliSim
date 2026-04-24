package com.melisim.users.service;

import com.melisim.users.model.User;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.Map;

@Service
public class JwtService {

    private final SecretKey key;
    private final long expirationMinutes;

    public JwtService(
            @Value("${melisim.jwt.secret}") String secret,
            @Value("${melisim.jwt.expiration-minutes:60}") long expirationMinutes
    ) {
        byte[] keyBytes = secret.getBytes(StandardCharsets.UTF_8);
        this.key = Keys.hmacShaKeyFor(keyBytes);
        this.expirationMinutes = expirationMinutes;
    }

    public String generate(User user) {
        Date now = new Date();
        Date exp = new Date(now.getTime() + expirationMinutes * 60_000L);

        return Jwts.builder()
                .subject(String.valueOf(user.getId()))
                .claims(Map.of(
                        "email", user.getEmail(),
                        "role", user.getUserType().name()
                ))
                .issuedAt(now)
                .expiration(exp)
                .signWith(key)
                .compact();
    }

    public long getExpirationSeconds() {
        return expirationMinutes * 60L;
    }
}
