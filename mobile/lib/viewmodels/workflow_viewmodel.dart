/// Workflow ViewModel — polling loop + state machine driving the learning UI.
library;

import 'dart:async';
import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/constants.dart';
import '../models/workflow.dart';
import '../services/learning_service.dart';
import '../services/cache_service.dart';

/// Family provider keyed by sessionId.
final workflowViewModelProvider = AsyncNotifierProvider.family<
    WorkflowViewModel, WorkflowSnapshot, String>(WorkflowViewModel.new);

class WorkflowViewModel extends FamilyAsyncNotifier<WorkflowSnapshot, String> {
  Timer? _pollTimer;
  Duration _pollInterval = AppConstants.pollIntervalInitial;

  @override
  Future<WorkflowSnapshot> build(String arg) async {
    ref.onDispose(_stopPolling);

    final cacheService = ref.read(cacheServiceProvider);
    final cacheKey = '/learning/$arg/workflow';
    final cachedStr = await cacheService.getString(cacheKey);
    if (cachedStr != null) {
      try {
        final data = jsonDecode(cachedStr) as Map<String, dynamic>;
        state = AsyncData(WorkflowSnapshot.fromJson(data));
      } catch (_) {
        // ignore malformed cache
      }
    }

    return _fetchAndSchedule();
  }

  /// Fetch the latest workflow snapshot and schedule the next poll if needed.
  Future<WorkflowSnapshot> _fetchAndSchedule() async {
    final service = ref.read(learningServiceProvider);
    final snapshot = await service.getWorkflow(arg);

    if (snapshot.status == 'error' || snapshot.status == 'archived') {
      _stopPolling();
    } else if (snapshot.nextAction == NextAction.wait || snapshot.isLoading) {
      _scheduleNextPoll();
    } else {
      // Reset interval once we leave the wait state.
      _pollInterval = AppConstants.pollIntervalInitial;
      _stopPolling();
    }

    return snapshot;
  }

  void _scheduleNextPoll() {
    _pollTimer?.cancel();
    _pollTimer = Timer(_pollInterval, () async {
      // Exponential backoff.
      _pollInterval = Duration(
        milliseconds:
            (_pollInterval.inMilliseconds * AppConstants.pollBackoffMultiplier)
                .round()
                .clamp(0, AppConstants.pollIntervalMax.inMilliseconds),
      );
      state = await AsyncValue.guard(_fetchAndSchedule);
    });
  }

  void _stopPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  /// Force-refresh the workflow (e.g., after a continue call).
  Future<void> refresh() async {
    _pollInterval = AppConstants.pollIntervalInitial;
    state = await AsyncValue.guard(_fetchAndSchedule);
  }

  /// Submit a continue request and then refresh.
  Future<void> continueJourney({
    List<int>? answers,
    String? selectedNode,
    String? traversalMode,
  }) async {
    final service = ref.read(learningServiceProvider);
    await service.continueJourney(
      arg,
      ContinueRequest(
        answers: answers,
        selectedNode: selectedNode,
        traversalMode: traversalMode,
      ),
    );
    await refresh();
  }
}
