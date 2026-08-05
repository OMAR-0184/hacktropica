/// Modal sheet displaying Tutor, Curator, and Quiz tabs for a specific node.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../config/theme.dart';
import '../../models/lesson.dart';
import '../../models/evaluation.dart';
import '../../models/workflow.dart';
import '../../services/learning_service.dart';
import '../../widgets/error_banner.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/tutor_markdown.dart';
import '../../widgets/tutor_chart_paper.dart';
import '../../widgets/paper_background.dart';
import '../../viewmodels/workflow_viewmodel.dart';
import 'quiz_view.dart';
import 'quiz_statistics_view.dart';

class NodeDetailSheet extends ConsumerStatefulWidget {
  final String sessionId;
  final NodeHierarchyMeta nodeMeta;
  final WorkflowSnapshot workflow;

  const NodeDetailSheet({
    super.key,
    required this.sessionId,
    required this.nodeMeta,
    required this.workflow,
  });

  @override
  ConsumerState<NodeDetailSheet> createState() => _NodeDetailSheetState();
}

class _NodeDetailSheetState extends ConsumerState<NodeDetailSheet>
    with SingleTickerProviderStateMixin {
  late TabController _tabCtrl;
  late Future<LessonResponse> _lessonFuture;

  @override
  void initState() {
    super.initState();
    // Only show Quiz tab if this is the active node and quiz is ready (or if we want to show it disabled).
    // Actually, let's always show 3 tabs, and conditionally render the content.
    _tabCtrl = TabController(length: 3, vsync: this);
    
    // Fetch specific node lesson
    _lessonFuture = ref
        .read(learningServiceProvider)
        .getLesson(widget.sessionId, nodeId: widget.nodeMeta.nodeId);
  }

  @override
  void dispose() {
    _tabCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isCurrentNode = widget.workflow.currentNode == widget.nodeMeta.nodeId;
    final status = (widget.nodeMeta.status ?? 'locked').toUpperCase();

    return PaperBackground(
      child: Container(
        height: MediaQuery.of(context).size.height,
        child: Column(
          children: [
          // Drag handle
          Center(
            child: Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(top: 12, bottom: 8),
              decoration: BoxDecoration(
                color: AppColors.border,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),

          // Header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    widget.nodeMeta.nodeId.replaceAll('_', ' '),
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppColors.surface2,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: Text(
                    status,
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: AppColors.textMuted,
                    ),
                  ),
                ),
              ],
            ),
          ),
          
          if (widget.workflow.options.contains(widget.nodeMeta.nodeId) &&
              widget.workflow.nextAction == NextAction.chooseBranch)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
              child: ElevatedButton(
                onPressed: () async {
                  try {
                    await ref.read(workflowViewModelProvider(widget.sessionId).notifier).continueJourney(
                          selectedNode: widget.nodeMeta.nodeId,
                        );
                    if (context.mounted) Navigator.of(context).pop();
                  } catch (e) {
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Failed to start topic: $e')),
                      );
                    }
                  }
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary500,
                  foregroundColor: Colors.white,
                  minimumSize: const Size.fromHeight(48),
                ),
                child: const Text('Start this Topic'),
              ),
            ),

          // Tabs
          TabBar(
            controller: _tabCtrl,
            indicatorColor: AppColors.primary400,
            labelColor: AppColors.primary400,
            unselectedLabelColor: AppColors.textMuted,
            tabs: const [
              Tab(text: 'Tutor'),
              Tab(text: 'Curator'),
              Tab(text: 'Quiz'),
            ],
          ),

          // Tab Views
          Expanded(
            child: FutureBuilder<LessonResponse>(
              future: _lessonFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return SingleChildScrollView(
                      child: LoadingShimmer.lessonSkeleton());
                }

                if (snapshot.hasError) {
                  final errStr = snapshot.error.toString();
                  if (errStr.contains('409') || errStr.contains('LESSON_NOT_GENERATED')) {
                    return const Center(
                      child: Padding(
                        padding: EdgeInsets.all(32),
                        child: Text(
                          'Content not available yet. You need to reach this topic in your journey first.',
                          textAlign: TextAlign.center,
                          style: TextStyle(color: AppColors.textMuted, fontSize: 16),
                        ),
                      ),
                    );
                  }
                  
                  return Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: ErrorBanner(message: errStr),
                    ),
                  );
                }

                final lesson = snapshot.data!;
                final curator = lesson.curatorContent;

                return TabBarView(
                  controller: _tabCtrl,
                  children: [
                    // Tutor Tab
                    _buildTutorTab(lesson),

                    // Curator Tab
                    _buildCuratorTab(curator),

                    // Quiz Tab
                    _buildQuizTab(isCurrentNode),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    ));
  }

  Widget _buildTutorTab(LessonResponse lesson) {
    final tutor = lesson.tutorContent;
    if (tutor == null) {
      return const Center(child: Text('No tutor content available.'));
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (tutor.hook.isNotEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              margin: const EdgeInsets.only(bottom: 24),
              decoration: BoxDecoration(
                color: AppColors.primary500.withAlpha(20),
                border: const Border(
                  left: BorderSide(color: AppColors.primary500, width: 4),
                ),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                tutor.hook,
                style: const TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 15,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ),
          if (tutor.priorKnowledge.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 24),
              child: TutorMarkdown(data: "**Recall:** ${tutor.priorKnowledge}"),
            ),
          if (tutor.learningObjective.isNotEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              margin: const EdgeInsets.only(bottom: 24),
              decoration: BoxDecoration(
                color: AppColors.primary500.withAlpha(20),
                border: const Border(
                  left: BorderSide(color: AppColors.primary500, width: 4),
                ),
                borderRadius: const BorderRadius.only(
                  topRight: Radius.circular(8),
                  bottomRight: Radius.circular(8),
                ),
              ),
              child: Text(
                tutor.learningObjective,
                style: const TextStyle(
                  color: AppColors.primary100,
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          TutorMarkdown(data: tutor.coreExplanation.isNotEmpty ? tutor.coreExplanation : tutor.explanation),
          if (tutor.workedExamples.isNotEmpty || tutor.examples.isNotEmpty) ...[
            const SizedBox(height: 32),
            const Text('Examples',
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary)),
            const SizedBox(height: 12),
            for (final ex in (tutor.workedExamples.isNotEmpty ? tutor.workedExamples : tutor.examples)) ...[
              TutorMarkdown(data: ex),
              const SizedBox(height: 12),
            ],
          ],
          if (tutor.visualDiagramDescription.isNotEmpty) ...[
            const SizedBox(height: 24),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.primary500.withAlpha(30)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.image, color: AppColors.primary500, size: 24),
                  const SizedBox(width: 12),
                  Expanded(child: TutorMarkdown(data: tutor.visualDiagramDescription)),
                ],
              ),
            ),
          ],
          if (lesson.markdownValid && lesson.markdownSource != null) ...[
            const SizedBox(height: 16),
            TutorChartPaper(markdownSource: lesson.markdownSource!),
          ],
          if (tutor.codeSnippet != null && tutor.codeSnippet!.isNotEmpty) ...[
            const SizedBox(height: 24),
            TutorMarkdown(data: '```\n${tutor.codeSnippet!}\n```'),
          ],
          if (tutor.commonMisconception.isNotEmpty) ...[
            const SizedBox(height: 32),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.warning.withAlpha(15),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.warning.withAlpha(30)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.lightbulb_outline,
                          color: AppColors.warning, size: 18),
                      SizedBox(width: 8),
                      Text('Common Misconception',
                          style: TextStyle(
                              color: AppColors.warning,
                              fontWeight: FontWeight.w600)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  TutorMarkdown(data: tutor.commonMisconception),
                ],
              ),
            ),
          ],
          if (tutor.practiceTask.isNotEmpty) ...[
            const SizedBox(height: 32),
            const Text('Practice',
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary)),
            const SizedBox(height: 12),
            TutorMarkdown(data: tutor.practiceTask),
          ],
          if (tutor.transferPrompt.isNotEmpty) ...[
            const SizedBox(height: 32),
            const Text('Apply Your Knowledge',
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary)),
            const SizedBox(height: 12),
            TutorMarkdown(data: tutor.transferPrompt),
          ],
          if (tutor.summary.isNotEmpty) ...[
            const SizedBox(height: 32),
            const Text('Summary',
                style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary)),
            const SizedBox(height: 12),
            for (final sum in tutor.summary) ...[
              TutorMarkdown(data: "- $sum"),
              const SizedBox(height: 8),
            ],
          ],
        ],
      ),
    );
  }

  Widget _buildCuratorTab(CuratorContent? curator) {
    if (curator == null || curator.isEmpty) {
      return const Center(child: Text('No curated resources available.'));
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Curated Links',
            style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary),
          ),
          const SizedBox(height: 16),
          // Reshape CuratorResources to be vertical list instead of horizontal for this tab.
          ...curator.articles.map((r) => _CuratorLinkTile(r, Icons.article, AppColors.primary400)),
          ...curator.videos.map((r) => _CuratorLinkTile(r, Icons.play_circle, AppColors.error)),
          ...curator.courses.map((r) => _CuratorLinkTile(r, Icons.school, AppColors.accent400)),
        ],
      ),
    );
  }

  Widget _buildQuizTab(bool isCurrentNode) {
    if (!isCurrentNode) {
      if (widget.nodeMeta.status == 'mastered' || widget.nodeMeta.status == 'completed' || widget.nodeMeta.status == 'needs_remediation' || (widget.nodeMeta.attempts != null && widget.nodeMeta.attempts! > 0)) {
        return FutureBuilder<EvaluationResult>(
          future: ref.read(learningServiceProvider).getEvaluationForNode(widget.sessionId, widget.nodeMeta.nodeId),
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: Text(
                    'Could not load quiz statistics for this node.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppColors.textMuted),
                  ),
                ),
              );
            }
            if (snapshot.hasData) {
              return QuizStatisticsView(
                evaluation: snapshot.data!,
                nodeId: widget.nodeMeta.nodeId,
              );
            }
            return const SizedBox.shrink();
          },
        );
      }
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Text(
            'Quiz is only available for the currently active node or completed nodes.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.textMuted),
          ),
        ),
      );
    }

    if (widget.workflow.nextAction != NextAction.takeQuiz && !widget.workflow.quizReady) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Text(
            'Quiz unlocks when this node is fully active or when tutor AI finishes generating.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.textMuted),
          ),
        ),
      );
    }

    return QuizView(
      sessionId: widget.sessionId,
      workflow: widget.workflow,
      onQuizSubmitted: () {
        // Close sheet after submit
        Navigator.of(context).pop();
      },
    );
  }
}

class _CuratorLinkTile extends StatelessWidget {
  final CuratorResource resource;
  final IconData icon;
  final Color color;

  const _CuratorLinkTile(this.resource, this.icon, this.color);

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppColors.surface2,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: ListTile(
        leading: Icon(icon, color: color),
        title: Text(resource.title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500)),
        subtitle: resource.description != null && resource.description!.isNotEmpty
            ? Text(resource.description!, style: const TextStyle(fontSize: 12), maxLines: 2, overflow: TextOverflow.ellipsis)
            : null,
        trailing: const Icon(Icons.open_in_new, size: 16, color: AppColors.textDisabled),
        onTap: () {
          if (resource.url.isNotEmpty) {
            launchUrl(Uri.parse(resource.url), mode: LaunchMode.externalApplication);
          }
        },
      ),
    );
  }
}
