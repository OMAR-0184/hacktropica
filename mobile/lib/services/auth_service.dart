/// Authentication service — login, register, refresh, token management.
library;

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config/constants.dart';
import '../models/auth.dart';
import 'api_client.dart';

final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService(ref.read(dioProvider), ref.read(secureStorageProvider));
});

class AuthService {
  final Dio _dio;
  final FlutterSecureStorage _storage;

  AuthService(this._dio, this._storage);

  /// Log in and store both tokens.
  Future<TokenPair> login(LoginRequest request) async {
    final res = await _dio.post('/auth/login/json', data: request.toJson());
    final pair = TokenPair.fromJson(res.data as Map<String, dynamic>);
    await _storeTokens(pair);
    return pair;
  }

  /// Register a new account. Returns the user (no token in this flow).
  Future<UserResponse> register(RegisterRequest request) async {
    final res = await _dio.post('/auth/register', data: request.toJson());
    return UserResponse.fromJson(res.data as Map<String, dynamic>);
  }

  /// Refresh the access token using the stored refresh token.
  Future<TokenPair> refreshToken() async {
    final refresh = await _storage.read(key: AppConstants.refreshTokenKey);
    if (refresh == null) throw Exception('No refresh token stored.');

    final res = await _dio.post(
      '/auth/refresh',
      data: {'refresh_token': refresh},
    );
    final pair = TokenPair.fromJson(res.data as Map<String, dynamic>);
    await _storeTokens(pair);
    return pair;
  }

  /// Check whether a stored access token exists.
  Future<bool> hasStoredToken() async {
    final token = await _storage.read(key: AppConstants.accessTokenKey);
    return token != null && token.isNotEmpty;
  }

  /// Clear all stored tokens (logout).
  Future<void> clearTokens() async {
    await _storage.delete(key: AppConstants.accessTokenKey);
    await _storage.delete(key: AppConstants.refreshTokenKey);
  }

  Future<void> _storeTokens(TokenPair pair) async {
    await _storage.write(
        key: AppConstants.accessTokenKey, value: pair.accessToken);
    await _storage.write(
        key: AppConstants.refreshTokenKey, value: pair.refreshToken);
  }
}
