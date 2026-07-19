/// Lesson ViewModel — fetches lesson content for a session.
library;

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/lesson.dart';
import '../services/learning_service.dart';

/// Family provider keyed by sessionId.
final lessonViewModelProvider =
    AsyncNotifierProvider.family<LessonViewModel, LessonResponse, String>(
  LessonViewModel.new,
);

class LessonViewModel extends FamilyAsyncNotifier<LessonResponse, String> {
  @override
  Future<LessonResponse> build(String arg) async {
    final service = ref.read(learningServiceProvider);
    return service.getLesson(arg);
  }

  Future<void> refresh() async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final service = ref.read(learningServiceProvider);
      return service.getLesson(arg);
    });
  }
}
