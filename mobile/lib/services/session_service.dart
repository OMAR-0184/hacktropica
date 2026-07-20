/// Session management service — list, start, archive.
library;

import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/session.dart';
import 'api_client.dart';
import 'cache_service.dart';

final sessionServiceProvider = Provider<SessionService>((ref) {
  return SessionService(ref.read(dioProvider), ref.read(cacheServiceProvider));
});

class SessionService {
  final Dio _dio;
  final CacheService _cache;

  SessionService(this._dio, this._cache);

  /// List all non-archived sessions for the authenticated user.
  Future<SessionListResponse> listSessions({
    int limit = 20,
    int offset = 0,
  }) async {
    final cacheKey = '/sessions?limit=$limit&offset=$offset';
    
    try {
      final res = await _dio.get(
        '/learning/sessions',
        queryParameters: {'limit': limit, 'offset': offset},
      );
      final data = res.data as Map<String, dynamic>;
      
      // Save to cache
      await _cache.setString(cacheKey, jsonEncode(data));
      
      return SessionListResponse.fromJson(data);
    } on DioException catch (_) {
      // Offline fallback
      final cachedStr = await _cache.getString(cacheKey);
      if (cachedStr != null) {
        final data = jsonDecode(cachedStr) as Map<String, dynamic>;
        return SessionListResponse.fromJson(data);
      }
      rethrow;
    }
  }

  /// Start a new learning session.
  Future<StartSessionResponse> startSession(StartSessionRequest request) async {
    final res = await _dio.post('/learning/start', data: request.toJson());
    return StartSessionResponse.fromJson(res.data as Map<String, dynamic>);
  }

  /// Soft-archive (delete) a session.
  Future<void> archiveSession(String sessionId) async {
    await _dio.delete('/learning/$sessionId');
  }
}
