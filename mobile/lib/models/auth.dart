/// Authentication data models.
library;

class LoginRequest {
  final String email;
  final String password;

  const LoginRequest({required this.email, required this.password});

  Map<String, dynamic> toJson() => {'email': email, 'password': password};
}

class RegisterRequest {
  final String email;
  final String password;
  final String? username;

  const RegisterRequest({
    required this.email,
    required this.password,
    this.username,
  });

  Map<String, dynamic> toJson() => {
        'email': email,
        'password': password,
        if (username != null && username!.isNotEmpty) 'username': username,
      };
}

class TokenPair {
  final String accessToken;
  final String refreshToken;
  final String tokenType;

  const TokenPair({
    required this.accessToken,
    required this.refreshToken,
    this.tokenType = 'bearer',
  });

  factory TokenPair.fromJson(Map<String, dynamic> json) => TokenPair(
        accessToken: json['access_token'] as String,
        refreshToken: json['refresh_token'] as String,
        tokenType: json['token_type'] as String? ?? 'bearer',
      );
}

class UserResponse {
  final int id;
  final String email;
  final String username;
  final String? createdAt;

  const UserResponse({
    required this.id,
    required this.email,
    required this.username,
    this.createdAt,
  });

  factory UserResponse.fromJson(Map<String, dynamic> json) => UserResponse(
        id: json['id'] as int,
        email: json['email'] as String,
        username: json['username'] as String? ?? '',
        createdAt: json['created_at'] as String?,
      );
}
