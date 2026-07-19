/// Renders the Tutor and Curator content for the current node.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/theme.dart';
import '../../models/workflow.dart';
import '../../viewmodels/lesson_viewmodel.dart';
import '../../viewmodels/workflow_viewmodel.dart';
import '../../widgets/curator_resources.dart';
import '../../widgets/error_banner.dart';

import '../../widgets/tutor_markdown.dart';
import 'wait_view.dart';

class LessonView extends ConsumerWidget {
  final String sessionId;
  final WorkflowSnapshot workflow;

  const LessonView({
    super.key,
    required this.sessionId,
    required this.workflow,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lessonAsync = ref.watch(lessonViewModelProvider(sessionId));

    return lessonAsync.when(
      loading: () => const WaitView(), // Re-use shimmer
      error: (err, _) => Padding(
        padding: const EdgeInsets.all(24),
        child: ErrorBanner(
          message: err.toString(),
          onRetry: () => ref.read(lessonViewModelProvider(sessionId).notifier).refresh(),
        ),
      ),
      data: (lesson) {
        final tutor = lesson.tutorContent;
        if (tutor == null) {
          return const Center(child: Text('No lesson content available.'));
        }

        return Stack(
          children: [
            SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 100),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Objective
                  if (tutor.learningObjective.isNotEmpty)
                    Container(
                      padding: const EdgeInsets.all(16),
                      margin: const EdgeInsets.only(bottom: 24),
                      decoration: BoxDecoration(
                        color: AppColors.primary500.withAlpha(20),
                        border: Border(
                          left: BorderSide(
                              color: AppColors.primary500, width: 4),
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

                  // Main Explanation
                  TutorMarkdown(data: tutor.explanation),

                  // Examples
                  if (tutor.examples.isNotEmpty) ...[
                    const SizedBox(height: 32),
                    const Text('Examples',
                        style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary)),
                    const SizedBox(height: 12),
                    for (final ex in tutor.examples) ...[
                      TutorMarkdown(data: ex),
                      const SizedBox(height: 12),
                    ],
                  ],

                  // Code Snippet
                  if (tutor.codeSnippet != null &&
                      tutor.codeSnippet!.isNotEmpty) ...[
                    const SizedBox(height: 24),
                    TutorMarkdown(
                        data: '```\n${tutor.codeSnippet!}\n```'),
                  ],

                  // Common Misconception
                  if (tutor.commonMisconception.isNotEmpty) ...[
                    const SizedBox(height: 32),
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AppColors.warning.withAlpha(15),
                        borderRadius: BorderRadius.circular(12),
                        border:
                            Border.all(color: AppColors.warning.withAlpha(30)),
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

                  // Practice Task
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

                  // Curator Resources
                  if (lesson.curatorContent != null &&
                      !lesson.curatorContent!.isEmpty) ...[
                    const SizedBox(height: 40),
                    CuratorResources(content: lesson.curatorContent!),
                  ],
                ],
              ),
            ),

            // Continue CTA
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      AppColors.background.withAlpha(0),
                      AppColors.background.withAlpha(200),
                      AppColors.background,
                    ],
                  ),
                ),
                child: SafeArea(
                  child: ElevatedButton(
                    onPressed: () {
                      ref
                          .read(workflowViewModelProvider(sessionId).notifier)
                          .continueJourney();
                    },
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                            workflow.nextAction == NextAction.advanceRemediation
                                ? 'Finish Remediation'
                                : 'Continue Journey'),
                        const SizedBox(width: 8),
                        const Icon(Icons.arrow_forward, size: 18),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}


