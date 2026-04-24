package com.melisim.users.service;

import com.melisim.users.dto.LoginRequest;
import com.melisim.users.dto.TokenResponse;
import com.melisim.users.dto.UserRequest;
import com.melisim.users.dto.UserResponse;
import com.melisim.users.exception.EmailAlreadyExistsException;
import com.melisim.users.exception.InvalidCredentialsException;
import com.melisim.users.exception.UserNotFoundException;
import com.melisim.users.model.User;
import com.melisim.users.model.UserType;
import com.melisim.users.repository.UserRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock private UserRepository repository;
    @Mock private PasswordEncoder encoder;
    @Mock private JwtService jwtService;

    @InjectMocks private UserService service;

    private UserRequest validRequest;

    @BeforeEach
    void setUp() {
        validRequest = new UserRequest();
        validRequest.setName("Alice Seller");
        validRequest.setEmail("alice@melisim.test");
        validRequest.setPassword("super-secret-pw");
        validRequest.setUserType(UserType.SELLER);
    }

    @Test
    void register_success_hashesPasswordAndPersists() {
        when(repository.existsByEmail("alice@melisim.test")).thenReturn(false);
        when(encoder.encode("super-secret-pw")).thenReturn("HASHED");
        when(repository.save(any(User.class))).thenAnswer(inv -> {
            User u = inv.getArgument(0);
            u.setId(42L);
            return u;
        });

        UserResponse resp = service.register(validRequest);

        assertThat(resp.getId()).isEqualTo(42L);
        assertThat(resp.getEmail()).isEqualTo("alice@melisim.test");
        assertThat(resp.getUserType()).isEqualTo(UserType.SELLER);
        verify(encoder).encode("super-secret-pw");
    }

    @Test
    void register_duplicateEmail_throwsConflict() {
        when(repository.existsByEmail(validRequest.getEmail())).thenReturn(true);

        assertThatThrownBy(() -> service.register(validRequest))
                .isInstanceOf(EmailAlreadyExistsException.class);

        verify(repository, never()).save(any());
    }

    @Test
    void login_wrongPassword_throwsInvalidCredentials() {
        User u = new User();
        u.setId(1L);
        u.setEmail("alice@melisim.test");
        u.setPasswordHash("HASHED");
        u.setUserType(UserType.BUYER);

        when(repository.findByEmail("alice@melisim.test")).thenReturn(Optional.of(u));
        when(encoder.matches("bad", "HASHED")).thenReturn(false);

        LoginRequest req = new LoginRequest();
        req.setEmail("alice@melisim.test");
        req.setPassword("bad");

        assertThatThrownBy(() -> service.login(req))
                .isInstanceOf(InvalidCredentialsException.class);
    }

    @Test
    void login_success_returnsToken() {
        User u = new User();
        u.setId(1L);
        u.setEmail("alice@melisim.test");
        u.setPasswordHash("HASHED");
        u.setUserType(UserType.BUYER);

        when(repository.findByEmail("alice@melisim.test")).thenReturn(Optional.of(u));
        when(encoder.matches("good", "HASHED")).thenReturn(true);
        when(jwtService.generate(u)).thenReturn("jwt.token.here");
        when(jwtService.getExpirationSeconds()).thenReturn(3600L);

        LoginRequest req = new LoginRequest();
        req.setEmail("alice@melisim.test");
        req.setPassword("good");

        TokenResponse resp = service.login(req);

        assertThat(resp.getAccessToken()).isEqualTo("jwt.token.here");
        assertThat(resp.getExpiresIn()).isEqualTo(3600L);
        assertThat(resp.getUser().getEmail()).isEqualTo("alice@melisim.test");
    }

    @Test
    void getById_notFound_throws() {
        when(repository.findById(99L)).thenReturn(Optional.empty());
        assertThatThrownBy(() -> service.getById(99L))
                .isInstanceOf(UserNotFoundException.class);
    }
}
