/// Quiz ViewModel — fetches quiz and manages answer state.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/quiz.dart';
import '../services/learning_service.dart';

/// Family provider keyed by sessionId.
final quizViewModelProvider =
    AsyncNotifierProvider.family<QuizViewModel, QuizResponse, String>(
  QuizViewModel.new,
);

class QuizViewModel extends FamilyAsyncNotifier<QuizResponse, String> {
  @override
  Future<QuizResponse> build(String arg) async {
    final service = ref.read(learningServiceProvider);
    return service.getQuiz(arg);
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final service = ref.read(learningServiceProvider);
      return service.getQuiz(arg);
    });
  }
}
