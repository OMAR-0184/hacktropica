/// Evaluation / grading result models.
library;

class QuestionResult {
  final String questionId;
  final String question;
  final List<String> options;
  final int correctIndex;
  final int userIndex;
  final bool isCorrect;

  const QuestionResult({
    required this.questionId,
    required this.question,
    required this.options,
    required this.correctIndex,
    required this.userIndex,
    required this.isCorrect,
  });

  factory QuestionResult.fromJson(Map<String, dynamic> json) => QuestionResult(
        questionId: json['question_id'] as String,
        question: json['question'] as String,
        options: (json['options'] as List<dynamic>)
            .map((e) => e as String)
            .toList(),
        correctIndex: json['correct_index'] as int,
        userIndex: json['user_index'] as int,
        isCorrect: json['is_correct'] as bool,
      );
}

class EvaluationResult {
  final double score;
  final List<String> weakAreas;
  final String feedback;
  final bool passed;
  final String nextAction;
  final List<QuestionResult> questionResults;
  final int questionCount;

  const EvaluationResult({
    required this.score,
    required this.weakAreas,
    required this.feedback,
    required this.passed,
    required this.nextAction,
    this.questionResults = const [],
    this.questionCount = 0,
  });

  factory EvaluationResult.fromJson(Map<String, dynamic> json) =>
      EvaluationResult(
        score: (json['score'] as num).toDouble(),
        weakAreas: (json['weak_areas'] as List<dynamic>)
            .map((e) => e as String)
            .toList(),
        feedback: json['feedback'] as String,
        passed: json['passed'] as bool,
        nextAction: json['next_action'] as String,
        questionResults: (json['question_results'] as List<dynamic>?)
                ?.map(
                    (e) => QuestionResult.fromJson(e as Map<String, dynamic>))
                .toList() ??
            [],
        questionCount: json['question_count'] as int? ?? 0,
      );

  int get scorePercent => (score * 100).round();
}
