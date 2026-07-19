/// Lesson content models — Tutor + Curator.
library;

class TutorContent {
  final String learningObjective;
  final String explanation;
  final List<String> examples;
  final String commonMisconception;
  final String practiceTask;
  final String? codeSnippet;

  const TutorContent({
    this.learningObjective = '',
    this.explanation = '',
    this.examples = const [],
    this.commonMisconception = '',
    this.practiceTask = '',
    this.codeSnippet,
  });

  factory TutorContent.fromJson(Map<String, dynamic> json) => TutorContent(
        learningObjective: json['learning_objective'] as String? ?? '',
        explanation: json['explanation'] as String? ?? '',
        examples: (json['examples'] as List<dynamic>?)
                ?.map((e) => e as String)
                .toList() ??
            [],
        commonMisconception: json['common_misconception'] as String? ?? '',
        practiceTask: json['practice_task'] as String? ?? '',
        codeSnippet: json['code_snippet'] as String?,
      );
}

class CuratorResource {
  final String title;
  final String url;
  final String? description;

  const CuratorResource({
    this.title = '',
    this.url = '',
    this.description,
  });

  factory CuratorResource.fromJson(Map<String, dynamic> json) =>
      CuratorResource(
        title: json['title'] as String? ?? '',
        url: json['url'] as String? ?? '',
        description: json['description'] as String?,
      );
}

class CuratorContent {
  final List<CuratorResource> articles;
  final List<CuratorResource> videos;
  final List<CuratorResource> courses;
  final List<String> references;

  const CuratorContent({
    this.articles = const [],
    this.videos = const [],
    this.courses = const [],
    this.references = const [],
  });

  factory CuratorContent.fromJson(Map<String, dynamic> json) => CuratorContent(
        articles: _parseResources(json['articles']),
        videos: _parseResources(json['videos']),
        courses: _parseResources(json['courses']),
        references: (json['references'] as List<dynamic>?)
                ?.map((e) => e as String)
                .toList() ??
            [],
      );

  static List<CuratorResource> _parseResources(dynamic list) =>
      (list as List<dynamic>?)
          ?.map((e) => CuratorResource.fromJson(e as Map<String, dynamic>))
          .toList() ??
      [];

  bool get isEmpty =>
      articles.isEmpty &&
      videos.isEmpty &&
      courses.isEmpty &&
      references.isEmpty;
}

class LessonResponse {
  final String sessionId;
  final String? nodeId;
  final TutorContent? tutorContent;
  final CuratorContent? curatorContent;
  final bool isRemediation;
  final String? parentNodeId;
  final int? depth;
  final String? nodeKind;
  final List<String> pathFromRoot;
  final bool? isMathHeavy;
  final bool? isExpanded;

  const LessonResponse({
    required this.sessionId,
    this.nodeId,
    this.tutorContent,
    this.curatorContent,
    this.isRemediation = false,
    this.parentNodeId,
    this.depth,
    this.nodeKind,
    this.pathFromRoot = const [],
    this.isMathHeavy,
    this.isExpanded,
  });

  factory LessonResponse.fromJson(Map<String, dynamic> json) =>
      LessonResponse(
        sessionId: json['session_id'] as String,
        nodeId: json['node_id'] as String?,
        tutorContent: json['tutor_content'] != null
            ? TutorContent.fromJson(
                json['tutor_content'] as Map<String, dynamic>)
            : null,
        curatorContent: json['curator_content'] != null
            ? CuratorContent.fromJson(
                json['curator_content'] as Map<String, dynamic>)
            : null,
        isRemediation: json['is_remediation'] as bool? ?? false,
        parentNodeId: json['parent_node_id'] as String?,
        depth: json['depth'] as int?,
        nodeKind: json['node_kind'] as String?,
        pathFromRoot: (json['path_from_root'] as List<dynamic>?)
                ?.map((e) => e as String)
                .toList() ??
            [],
        isMathHeavy: json['is_math_heavy'] as bool?,
        isExpanded: json['is_expanded'] as bool?,
      );
}
