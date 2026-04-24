package com.melisim.users.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.melisim.users.dto.TokenResponse;
import com.melisim.users.dto.UserRequest;
import com.melisim.users.dto.UserResponse;
import com.melisim.users.exception.EmailAlreadyExistsException;
import com.melisim.users.model.UserType;
import com.melisim.users.service.UserService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import com.melisim.users.config.SecurityConfig;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(UserController.class)
@Import(SecurityConfig.class)
class UserControllerTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private ObjectMapper mapper;
    @MockBean private UserService service;

    @Test
    void register_returns201() throws Exception {
        UserRequest req = new UserRequest();
        req.setName("Bob");
        req.setEmail("bob@melisim.test");
        req.setPassword("password123");
        req.setUserType(UserType.BUYER);

        when(service.register(any(UserRequest.class)))
                .thenReturn(new UserResponse(7L, "Bob", "bob@melisim.test", UserType.BUYER));

        mockMvc.perform(post("/users/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(req)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(7))
                .andExpect(jsonPath("$.email").value("bob@melisim.test"));
    }

    @Test
    void register_invalidEmail_returns400() throws Exception {
        UserRequest req = new UserRequest();
        req.setName("Bob");
        req.setEmail("not-an-email");
        req.setPassword("password123");

        mockMvc.perform(post("/users/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(req)))
                .andExpect(status().isBadRequest());
    }

    @Test
    void register_duplicateEmail_returns409() throws Exception {
        UserRequest req = new UserRequest();
        req.setName("Bob");
        req.setEmail("bob@melisim.test");
        req.setPassword("password123");

        when(service.register(any(UserRequest.class)))
                .thenThrow(new EmailAlreadyExistsException("taken"));

        mockMvc.perform(post("/users/register")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(mapper.writeValueAsString(req)))
                .andExpect(status().isConflict());
    }
}
