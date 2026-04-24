package com.melisim.users.dto;

import com.melisim.users.model.User;
import com.melisim.users.model.UserType;

public class UserResponse {
    private Long id;
    private String name;
    private String email;
    private UserType userType;

    public UserResponse() {}

    public UserResponse(Long id, String name, String email, UserType userType) {
        this.id = id;
        this.name = name;
        this.email = email;
        this.userType = userType;
    }

    public static UserResponse from(User u) {
        return new UserResponse(u.getId(), u.getName(), u.getEmail(), u.getUserType());
    }

    public Long getId() { return id; }
    public String getName() { return name; }
    public String getEmail() { return email; }
    public UserType getUserType() { return userType; }

    public void setId(Long id) { this.id = id; }
    public void setName(String name) { this.name = name; }
    public void setEmail(String email) { this.email = email; }
    public void setUserType(UserType userType) { this.userType = userType; }
}
