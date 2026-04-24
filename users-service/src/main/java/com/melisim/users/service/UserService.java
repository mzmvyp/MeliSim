package com.melisim.users.service;

import com.melisim.users.dto.LoginRequest;
import com.melisim.users.dto.TokenResponse;
import com.melisim.users.dto.UserRequest;
import com.melisim.users.dto.UserResponse;
import com.melisim.users.exception.EmailAlreadyExistsException;
import com.melisim.users.exception.InvalidCredentialsException;
import com.melisim.users.exception.UserNotFoundException;
import com.melisim.users.model.User;
import com.melisim.users.repository.UserRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class UserService {

    private final UserRepository repository;
    private final PasswordEncoder encoder;
    private final JwtService jwtService;

    public UserService(UserRepository repository, PasswordEncoder encoder, JwtService jwtService) {
        this.repository = repository;
        this.encoder = encoder;
        this.jwtService = jwtService;
    }

    @Transactional
    public UserResponse register(UserRequest req) {
        if (repository.existsByEmail(req.getEmail())) {
            throw new EmailAlreadyExistsException("Email already registered: " + req.getEmail());
        }
        User u = new User();
        u.setName(req.getName());
        u.setEmail(req.getEmail());
        u.setPasswordHash(encoder.encode(req.getPassword()));
        u.setUserType(req.getUserType());
        return UserResponse.from(repository.save(u));
    }

    public TokenResponse login(LoginRequest req) {
        User u = repository.findByEmail(req.getEmail())
                .orElseThrow(() -> new InvalidCredentialsException("Invalid email or password"));
        if (!encoder.matches(req.getPassword(), u.getPasswordHash())) {
            throw new InvalidCredentialsException("Invalid email or password");
        }
        String token = jwtService.generate(u);
        return new TokenResponse(token, jwtService.getExpirationSeconds(), UserResponse.from(u));
    }

    @Transactional(readOnly = true)
    public UserResponse getById(Long id) {
        User u = repository.findById(id)
                .orElseThrow(() -> new UserNotFoundException("User not found: " + id));
        return UserResponse.from(u);
    }

    @Transactional
    public UserResponse update(Long id, UserRequest req) {
        User u = repository.findById(id)
                .orElseThrow(() -> new UserNotFoundException("User not found: " + id));
        u.setName(req.getName());
        if (!u.getEmail().equalsIgnoreCase(req.getEmail())) {
            if (repository.existsByEmail(req.getEmail())) {
                throw new EmailAlreadyExistsException("Email already in use: " + req.getEmail());
            }
            u.setEmail(req.getEmail());
        }
        if (req.getPassword() != null && !req.getPassword().isBlank()) {
            u.setPasswordHash(encoder.encode(req.getPassword()));
        }
        if (req.getUserType() != null) {
            u.setUserType(req.getUserType());
        }
        return UserResponse.from(repository.save(u));
    }

    @Transactional
    public void delete(Long id) {
        if (!repository.existsById(id)) {
            throw new UserNotFoundException("User not found: " + id);
        }
        repository.deleteById(id);
    }
}
