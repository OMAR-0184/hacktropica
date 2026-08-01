/// Lesson content models — Tutor + Curator.
library;

class TutorContent {
  final String hook;
  final String priorKnowledge;
  final String learningObjective;
  final String coreExplanation;
  final List<String> workedExamples;
  final String visualDiagramDescription;
  final String commonMisconception;
  final String practiceTask;
  final String transferPrompt;
  final List<String> summary;

  // Legacy fields
  final String explanation;
  final List<String> examples;
  final String? codeSnippet;

  const TutorContent({
    this.hook = '',
    this.priorKnowledge = '',
    this.learningObjective = '',
    this.coreExplanation = '',
    this.workedExamples = const [],
    this.visualDiagramDescription = '',
    this.commonMisconception = '',
    this.practiceTask = '',
    this.transferPrompt = '',
    this.summary = const [],
    this.explanation = '',
    this.examples = const [],
    this.codeSnippet,
  });

  factory TutorContent.fromJson(Map<String, dynamic> json) => TutorContent(
        hook: json['hook'] as String? ?? '',
        priorKnowledge: json['prior_knowledge'] as String? ?? '',
        learningObjective: json['learning_objective'] as String? ?? '',
        coreExplanation: json['core_explanation'] as String? ?? '',
        workedExamples: (json['worked_examples'] as List<dynamic>?)
                ?.map((e) => e as String)
                .toList() ??
            [],
        visualDiagramDescription:
            json['visual_diagram_description'] as String? ?? '',
        commonMisconception: json['common_misconception'] as String? ?? '',
        practiceTask: json['practice_task'] as String? ?? '',
        transferPrompt: json['transfer_prompt'] as String? ?? '',
        summary: (json['summary'] as List<dynamic>?)
                ?.map((e) => e as String)
                .toList() ??
            [],
        explanation: json['explanation'] as String? ?? '',
        examples: (json['examples'] as List<dynamic>?)
                ?.map((e) => e as String)
                .toList() ??
            [],
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
  final String? latexSource;
  final bool latexValid;
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
    this.latexSource,
    this.latexValid = false,
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
        latexSource: json['latex_source'] as String?,
        latexValid: json['latex_valid'] as bool? ?? false,
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
