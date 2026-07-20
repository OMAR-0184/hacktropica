/// Auth ViewModel — manages authentication state, login/register/logout.
library;

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../models/auth.dart';

/// Emits `true` when authenticated, `false` when not.
final authViewModelProvider =
    AsyncNotifierProvider<AuthViewModel, bool>(AuthViewModel.new);

class AuthViewModel extends AsyncNotifier<bool> {
  @override
  Future<bool> build() async {
    final service = ref.read(authServiceProvider);
    return service.hasStoredToken();
  }

  Future<void> login(String email, String password) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final service = ref.read(authServiceProvider);
      await service.login(LoginRequest(email: email, password: password));
      return true;
    });
  }

  /// Register then auto-login.
  Future<void> register(String email, String password,
      {String? username}) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final service = ref.read(authServiceProvider);
      await service.register(
        RegisterRequest(email: email, password: password, username: username),
      );
      // Auto-login after successful registration.
      await service.login(LoginRequest(email: email, password: password));
      return true;
    });
  }

  Future<void> logout() async {
    final service = ref.read(authServiceProvider);
    await service.clearTokens();
    state = const AsyncData(false);
  }

  /// Extract a user-facing error message from the current state or DioException.
  static String errorMessage(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      return parseApiError(data,
          fallback: error.message ?? 'Connection error.');
    }
    return error.toString();
  }
}
