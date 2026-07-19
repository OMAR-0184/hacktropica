/// Learning service — workflow, lesson, quiz, evaluation, continue, choices.
library;

import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/evaluation.dart';
import '../models/lesson.dart';
import '../models/quiz.dart';
import '../models/workflow.dart';
import 'api_client.dart';
import 'cache_service.dart';

final learningServiceProvider = Provider<LearningService>((ref) {
  return LearningService(ref.read(dioProvider), ref.read(cacheServiceProvider));
});

class LearningService {
  final Dio _dio;
  final CacheService _cache;

  LearningService(this._dio, this._cache);

  /// Fetch the full workflow snapshot (primary orchestration endpoint).
  Future<WorkflowSnapshot> getWorkflow(String sessionId) async {
    final cacheKey = '/learning/$sessionId/workflow';
    try {
      final res = await _dio.get(cacheKey);
      final data = res.data as Map<String, dynamic>;
      await _cache.setString(cacheKey, jsonEncode(data));
      return WorkflowSnapshot.fromJson(data);
    } on DioException catch (_) {
      final cachedStr = await _cache.getString(cacheKey);
      if (cachedStr != null) {
        return WorkflowSnapshot.fromJson(jsonDecode(cachedStr) as Map<String, dynamic>);
      }
      rethrow;
    }
  }

  /// Fetch lesson content for the active node (or a specific node).
  Future<LessonResponse> getLesson(String sessionId, {String? nodeId}) async {
    final cacheKey = '/learning/$sessionId/lesson${nodeId != null ? "?node_id=$nodeId" : ""}';
    try {
      final res = await _dio.get(
        '/learning/$sessionId/lesson',
        queryParameters: nodeId != null ? {'node_id': nodeId} : null,
      );
      final data = res.data as Map<String, dynamic>;
      await _cache.setString(cacheKey, jsonEncode(data));
      return LessonResponse.fromJson(data);
    } on DioException catch (_) {
      final cachedStr = await _cache.getString(cacheKey);
      if (cachedStr != null) {
        return LessonResponse.fromJson(jsonDecode(cachedStr) as Map<String, dynamic>);
      }
      rethrow;
    }
  }

  /// Fetch quiz questions for the current node.
  Future<QuizResponse> getQuiz(String sessionId) async {
    final res = await _dio.get('/learning/$sessionId/quiz');
    return QuizResponse.fromJson(res.data as Map<String, dynamic>);
  }

  /// Fetch the evaluation/grading result.
  Future<EvaluationResult> getEvaluation(String sessionId) async {
    final res = await _dio.get('/learning/$sessionId/evaluation');
    return EvaluationResult.fromJson(res.data as Map<String, dynamic>);
  }

  /// Unified continue endpoint — submit answers, select branch, or advance.
  Future<ContinueResponse> continueJourney(
    String sessionId,
    ContinueRequest request,
  ) async {
    final res = await _dio.post(
      '/learning/$sessionId/continue',
      data: request.toJson(),
    );
    return ContinueResponse.fromJson(res.data as Map<String, dynamic>);
  }
}
