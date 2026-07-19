/// Session data models.
library;

class SessionSummary {
  final String sessionId;
  final String topic;
  final String status;
  final String createdAt;
  final double overallProgress;

  const SessionSummary({
    required this.sessionId,
    required this.topic,
    required this.status,
    required this.createdAt,
    this.overallProgress = 0.0,
  });

  factory SessionSummary.fromJson(Map<String, dynamic> json) => SessionSummary(
        sessionId: json['session_id'] as String,
        topic: json['topic'] as String,
        status: json['status'] as String,
        createdAt: json['created_at'] as String,
        overallProgress: (json['overall_progress'] as num?)?.toDouble() ?? 0.0,
      );
}

class SessionListResponse {
  final List<SessionSummary> sessions;
  final int total;

  const SessionListResponse({required this.sessions, required this.total});

  factory SessionListResponse.fromJson(Map<String, dynamic> json) =>
      SessionListResponse(
        sessions: (json['sessions'] as List<dynamic>)
            .map((e) => SessionSummary.fromJson(e as Map<String, dynamic>))
            .toList(),
        total: json['total'] as int,
      );
}

class StartSessionRequest {
  final String topic;
  final String courseMode;
  final String traversalMode;

  const StartSessionRequest({
    required this.topic,
    this.courseMode = 'detailed',
    this.traversalMode = 'dfs',
  });

  Map<String, dynamic> toJson() => {
        'topic': topic,
        'course_mode': courseMode,
        'traversal_mode': traversalMode,
      };
}

class StartSessionResponse {
  final String sessionId;
  final String message;

  const StartSessionResponse({required this.sessionId, required this.message});

  factory StartSessionResponse.fromJson(Map<String, dynamic> json) =>
      StartSessionResponse(
        sessionId: json['session_id'] as String,
        message: json['message'] as String,
      );
}
