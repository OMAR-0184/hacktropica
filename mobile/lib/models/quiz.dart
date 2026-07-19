/// Quiz data models.
library;

class QuizQuestion {
  final String questionId;
  final String question;
  final List<String> options;

  const QuizQuestion({
    required this.questionId,
    required this.question,
    required this.options,
  });

  factory QuizQuestion.fromJson(Map<String, dynamic> json) => QuizQuestion(
        questionId: json['question_id'] as String,
        question: json['question'] as String,
        options: (json['options'] as List<dynamic>)
            .map((e) => e as String)
            .toList(),
      );
}

class QuizResponse {
  final String sessionId;
  final String nodeId;
  final List<QuizQuestion> questions;
  final int questionCount;

  const QuizResponse({
    required this.sessionId,
    required this.nodeId,
    required this.questions,
    this.questionCount = 0,
  });

  factory QuizResponse.fromJson(Map<String, dynamic> json) => QuizResponse(
        sessionId: json['session_id'] as String,
        nodeId: json['node_id'] as String,
        questions: (json['questions'] as List<dynamic>)
            .map((e) => QuizQuestion.fromJson(e as Map<String, dynamic>))
            .toList(),
        questionCount: json['question_count'] as int? ?? 0,
      );
}
