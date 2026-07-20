/// Evaluation ViewModel — fetches grading results.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/evaluation.dart';
import '../services/learning_service.dart';

/// Family provider keyed by sessionId.
final evaluationViewModelProvider = AsyncNotifierProvider.family<
    EvaluationViewModel, EvaluationResult, String>(EvaluationViewModel.new);

class EvaluationViewModel
    extends FamilyAsyncNotifier<EvaluationResult, String> {
  @override
  Future<EvaluationResult> build(String arg) async {
    final service = ref.read(learningServiceProvider);
    return service.getEvaluation(arg);
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final service = ref.read(learningServiceProvider);
      return service.getEvaluation(arg);
    });
  }
}
