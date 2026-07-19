/// Continue request/response models and workflow snapshot.
library;

// ── NextAction enum ────────────────────────────────────────

enum NextAction {
  wait,
  takeQuiz,
  chooseBranch,
  advance,
  advanceRemediation,
  completed,
  blocked;

  static NextAction fromString(String? value) => switch (value) {
        'wait' => wait,
        'take_quiz' => takeQuiz,
        'choose_branch' => chooseBranch,
        'advance' => advance,
        'advance_remediation' => advanceRemediation,
        'completed' => completed,
        'blocked' => blocked,
        _ => wait,
      };
}

// ── ContinueRequest ────────────────────────────────────────

class ContinueRequest {
  final List<int>? answers;
  final String? selectedNode;
  final String? traversalMode;
  final String? clientRequestId;

  const ContinueRequest({
    this.answers,
    this.selectedNode,
    this.traversalMode,
    this.clientRequestId,
  });

  Map<String, dynamic> toJson() => {
        if (answers != null) 'answers': answers,
        if (selectedNode != null) 'selected_node': selectedNode,
        if (traversalMode != null) 'traversal_mode': traversalMode,
        if (clientRequestId != null) 'client_request_id': clientRequestId,
      };
}

// ── ContinueResponse ──────────────────────────────────────

class ContinueResponse {
  final String sessionId;
  final String status;
  final String action;
  final String message;
  final bool enqueued;
  final List<String> options;
  final String? recommendedNode;
  final String? recommendationReason;
  final String? requiredInput;
  final String? requestStatus;

  const ContinueResponse({
    required this.sessionId,
    required this.status,
    required this.action,
    required this.message,
    this.enqueued = false,
    this.options = const [],
    this.recommendedNode,
    this.recommendationReason,
    this.requiredInput,
    this.requestStatus,
  });

  factory ContinueResponse.fromJson(Map<String, dynamic> json) =>
      ContinueResponse(
        sessionId: json['session_id'] as String,
        status: json['status'] as String,
        action: json['action'] as String,
        message: json['message'] as String,
        enqueued: json['enqueued'] as bool? ?? false,
        options: (json['options'] as List<dynamic>?)
                ?.map((e) => e as String)
                .toList() ??
            [],
        recommendedNode: json['recommended_node'] as String?,
        recommendationReason: json['recommendation_reason'] as String?,
        requiredInput: json['required_input'] as String?,
        requestStatus: json['request_status'] as String?,
      );
}

// ── NodeHierarchyMeta ──────────────────────────────────────

class NodeHierarchyMeta {
  final String nodeId;
  final String? parentNodeId;
  final int? depth;
  final String? nodeKind;
  final List<String> pathFromRoot;
  final bool? isMathHeavy;
  final bool? isExpanded;
  final String? status;
  final double? score;
  final int? attempts;

  const NodeHierarchyMeta({
    required this.nodeId,
    this.parentNodeId,
    this.depth,
    this.nodeKind,
    this.pathFromRoot = const [],
    this.isMathHeavy,
    this.isExpanded,
    this.status,
    this.score,
    this.attempts,
  });

  factory NodeHierarchyMeta.fromJson(Map<String, dynamic> json) =>
      NodeHierarchyMeta(
        nodeId: json['node_id'] as String,
        parentNodeId: json['parent_node_id'] as String?,
        depth: json['depth'] as int?,
        nodeKind: json['node_kind'] as String?,
        pathFromRoot: (json['path_from_root'] as List<dynamic>?)
                ?.map((e) => e as String)
                .toList() ??
            [],
        isMathHeavy: json['is_math_heavy'] as bool?,
        isExpanded: json['is_expanded'] as bool?,
        status: json['status'] as String?,
        score: (json['score'] as num?)?.toDouble(),
        attempts: json['attempts'] as int?,
      );
}

// ── WorkflowSnapshot ──────────────────────────────────────

class WorkflowSnapshot {
  final String sessionId;
  final String status;
  final String? currentPhase;
  final String topic;
  final String currentNode;
  final String journeyMode;
  final String traversalMode;
  final List<String> waitingOn;
  final NextAction nextAction;
  final String? orchestratorReasoning;
  final List<String> options;
  final String? recommendedNode;
  final String? recommendationReason;
  final Map<String, dynamic> recommendationFactors;
  final bool lessonReady;
  final bool quizReady;
  final bool evaluationReady;
  final int quizQuestionCount;
  final List<String> activeFrontier;
  final List<String> currentPath;
  final Map<String, List<String>> childrenMap;
  final List<NodeHierarchyMeta> nodeCatalog;

  const WorkflowSnapshot({
    required this.sessionId,
    required this.status,
    this.currentPhase,
    this.topic = '',
    this.currentNode = '',
    this.journeyMode = 'learn',
    this.traversalMode = 'dfs',
    this.waitingOn = const [],
    this.nextAction = NextAction.wait,
    this.orchestratorReasoning,
    this.options = const [],
    this.recommendedNode,
    this.recommendationReason,
    this.recommendationFactors = const {},
    this.lessonReady = false,
    this.quizReady = false,
    this.evaluationReady = false,
    this.quizQuestionCount = 0,
    this.activeFrontier = const [],
    this.currentPath = const [],
    this.childrenMap = const {},
    this.nodeCatalog = const [],
  });

  factory WorkflowSnapshot.fromJson(Map<String, dynamic> json) {
    // Parse children_map: { "node": ["child1", "child2"] }
    final rawChildrenMap = json['children_map'] as Map<String, dynamic>? ?? {};
    final childrenMap = rawChildrenMap.map(
      (key, value) => MapEntry(
        key,
        (value as List<dynamic>).map((e) => e as String).toList(),
      ),
    );

    return WorkflowSnapshot(
      sessionId: json['session_id'] as String,
      status: json['status'] as String,
      currentPhase: json['current_phase'] as String?,
      topic: json['topic'] as String? ?? '',
      currentNode: json['current_node'] as String? ?? '',
      journeyMode: json['journey_mode'] as String? ?? 'learn',
      traversalMode: json['traversal_mode'] as String? ?? 'dfs',
      waitingOn: (json['waiting_on'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      nextAction: NextAction.fromString(json['next_action'] as String?),
      orchestratorReasoning: json['orchestrator_reasoning'] as String?,
      options: (json['options'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      recommendedNode: json['recommended_node'] as String?,
      recommendationReason: json['recommendation_reason'] as String?,
      recommendationFactors:
          json['recommendation_factors'] as Map<String, dynamic>? ?? {},
      lessonReady: json['lesson_ready'] as bool? ?? false,
      quizReady: json['quiz_ready'] as bool? ?? false,
      evaluationReady: json['evaluation_ready'] as bool? ?? false,
      quizQuestionCount: json['quiz_question_count'] as int? ?? 0,
      activeFrontier: (json['active_frontier'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      currentPath: (json['current_path'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      childrenMap: childrenMap,
      nodeCatalog: (json['node_catalog'] as List<dynamic>?)
              ?.map((e) =>
                  NodeHierarchyMeta.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }

  /// Whether the session is in a ready state for user interaction.
  bool get isReady => status == 'ready';

  /// Whether the session is still initializing.
  bool get isLoading =>
      status == 'initializing' || status == 'running' || status == 'evaluating';
}
