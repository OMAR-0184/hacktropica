/// Dio HTTP client with auth, refresh, and retry interceptors.
library;

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config/constants.dart';

// ── Secure storage provider ────────────────────────────────

final secureStorageProvider = Provider<FlutterSecureStorage>(
  (_) => const FlutterSecureStorage(),
);

// ── Dio provider ───────────────────────────────────────────

final dioProvider = Provider<Dio>((ref) {
  final storage = ref.read(secureStorageProvider);
  final dio = Dio(BaseOptions(
    baseUrl: AppConstants.apiBaseUrl,
    connectTimeout: const Duration(seconds: 15),
    receiveTimeout: const Duration(seconds: 30),
    headers: {'Content-Type': 'application/json'},
  ));

  dio.interceptors.add(_AuthInterceptor(storage, dio));
  return dio;
});

// ── Auth interceptor with transparent token refresh ────────

class _AuthInterceptor extends Interceptor {
  final FlutterSecureStorage _storage;
  final Dio _dio;
  bool _isRefreshing = false;
  final List<_QueuedRequest> _queue = [];

  _AuthInterceptor(this._storage, this._dio);

  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await _storage.read(key: AppConstants.accessTokenKey);
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode != 401) {
      return handler.next(err);
    }

    // Avoid refresh loops for auth endpoints themselves.
    final path = err.requestOptions.path;
    if (path.contains('/auth/')) {
      return handler.next(err);
    }

    if (_isRefreshing) {
      // Queue the request and resolve it after refresh completes.
      _queue.add(_QueuedRequest(err.requestOptions, handler));
      return;
    }

    _isRefreshing = true;
    try {
      final refreshToken =
          await _storage.read(key: AppConstants.refreshTokenKey);
      if (refreshToken == null || refreshToken.isEmpty) {
        return handler.next(err);
      }

      final res = await _dio.post(
        '/auth/refresh',
        data: {'refresh_token': refreshToken},
        options: Options(headers: {'Content-Type': 'application/json'}),
      );

      final newAccess = res.data['access_token'] as String;
      final newRefresh = res.data['refresh_token'] as String;
      await _storage.write(key: AppConstants.accessTokenKey, value: newAccess);
      await _storage.write(
          key: AppConstants.refreshTokenKey, value: newRefresh);

      // Retry the original request with the new token.
      err.requestOptions.headers['Authorization'] = 'Bearer $newAccess';
      final retryRes = await _dio.fetch(err.requestOptions);
      handler.resolve(retryRes);

      // Flush the queue.
      for (final queued in _queue) {
        queued.options.headers['Authorization'] = 'Bearer $newAccess';
        _dio.fetch(queued.options).then(
              queued.handler.resolve,
              onError: (e) => queued.handler.reject(e as DioException),
            );
      }
    } on DioException {
      // Refresh failed → clear tokens (force re-login).
      await _storage.delete(key: AppConstants.accessTokenKey);
      await _storage.delete(key: AppConstants.refreshTokenKey);
      handler.next(err);
    } finally {
      _queue.clear();
      _isRefreshing = false;
    }
  }
}

class _QueuedRequest {
  final RequestOptions options;
  final ErrorInterceptorHandler handler;
  _QueuedRequest(this.options, this.handler);
}

// ── Helper to extract API error messages ───────────────────

/// Parse a user-facing error message from either the standardized
/// `{ error: { message } }` envelope or the legacy `{ detail }` shape.
String parseApiError(dynamic responseData, {String fallback = 'An unexpected error occurred.'}) {
  if (responseData is Map<String, dynamic>) {
    // Standardized envelope
    final error = responseData['error'];
    if (error is Map<String, dynamic>) {
      return error['message'] as String? ?? fallback;
    }
    // Legacy envelope
    final detail = responseData['detail'];
    if (detail is String) return detail;
    if (detail is Map<String, dynamic>) {
      return detail['message'] as String? ?? fallback;
    }
  }
  return fallback;
}
