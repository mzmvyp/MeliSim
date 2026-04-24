package com.melisim.users.dto;

public class TokenResponse {
    private String accessToken;
    private String tokenType = "Bearer";
    private long expiresIn;
    private UserResponse user;

    public TokenResponse() {}

    public TokenResponse(String accessToken, long expiresIn, UserResponse user) {
        this.accessToken = accessToken;
        this.expiresIn = expiresIn;
        this.user = user;
    }

    public String getAccessToken() { return accessToken; }
    public String getTokenType() { return tokenType; }
    public long getExpiresIn() { return expiresIn; }
    public UserResponse getUser() { return user; }

    public void setAccessToken(String accessToken) { this.accessToken = accessToken; }
    public void setTokenType(String tokenType) { this.tokenType = tokenType; }
    public void setExpiresIn(long expiresIn) { this.expiresIn = expiresIn; }
    public void setUser(UserResponse user) { this.user = user; }
}
