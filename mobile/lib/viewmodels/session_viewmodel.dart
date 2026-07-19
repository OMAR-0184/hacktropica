/// Session ViewModel — manages session list, start, archive.
library;

import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/session.dart';
import '../services/api_client.dart';
import '../services/session_service.dart';
import '../services/cache_service.dart';

/// The list of active sessions.
final sessionListProvider =
    AsyncNotifierProvider<SessionListViewModel, List<SessionSummary>>(
  SessionListViewModel.new,
);

class SessionListViewModel extends AsyncNotifier<List<SessionSummary>> {
  @override
  Future<List<SessionSummary>> build() async {
    final cacheService = ref.read(cacheServiceProvider);
    final cacheKey = '/sessions?limit=20&offset=0';
    final cachedStr = await cacheService.getString(cacheKey);
    if (cachedStr != null) {
      try {
        final data = jsonDecode(cachedStr) as Map<String, dynamic>;
        state = AsyncData(SessionListResponse.fromJson(data).sessions);
      } catch (_) {}
    }

    final service = ref.read(sessionServiceProvider);
    final response = await service.listSessions();
    return response.sessions;
  }

  /// Start a new learning session. Returns the new session ID.
  Future<String> startSession({
    required String topic,
    String courseMode = 'detailed',
    String traversalMode = 'dfs',
  }) async {
    final service = ref.read(sessionServiceProvider);
    final response = await service.startSession(
      StartSessionRequest(
        topic: topic,
        courseMode: courseMode,
        traversalMode: traversalMode,
      ),
    );
    // Refresh the session list.
    ref.invalidateSelf();
    return response.sessionId;
  }

  /// Archive (soft-delete) a session.
  Future<void> archiveSession(String sessionId) async {
    final service = ref.read(sessionServiceProvider);
    await service.archiveSession(sessionId);
    // Remove from local state immediately for snappy UI.
    state = AsyncData(
      state.value?.where((s) => s.sessionId != sessionId).toList() ?? [],
    );
  }

  /// Extract user-facing error message.
  static String errorMessage(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      return parseApiError(data, fallback: 'Session operation failed.');
    }
    return error.toString();
  }
}
