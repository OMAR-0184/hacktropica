/// Evaluation screen showing grading results.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/theme.dart';
import '../../viewmodels/evaluation_viewmodel.dart';
import '../../viewmodels/workflow_viewmodel.dart';
import '../../widgets/error_banner.dart';
import '../../widgets/score_indicator.dart';
import '../../widgets/staggered_list.dart';
import 'wait_view.dart';

class EvaluationView extends ConsumerWidget {
  final String sessionId;

  const EvaluationView({super.key, required this.sessionId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final evalAsync = ref.watch(evaluationViewModelProvider(sessionId));

    return evalAsync.when(
      loading: () => const WaitView(reasoning: 'Grading your answers...'),
      error: (err, _) => Padding(
        padding: const EdgeInsets.all(24),
        child: ErrorBanner(
          message: err.toString(),
          onRetry: () => ref
              .read(evaluationViewModelProvider(sessionId).notifier)
              .refresh(),
        ),
      ),
      data: (eval) {
        int staggerIndex = 0;

        return Stack(
          children: [
            SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 32, 20, 100),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  // Score ring
                  StaggeredFadeSlide(
                    index: staggerIndex++,
                    slideOffset: 30,
                    child: ScoreIndicator(score: eval.score, size: 160),
                  ),
                  const SizedBox(height: 32),

                  // Weak areas
                  if (eval.weakAreas.isNotEmpty) ...[
                    StaggeredFadeSlide(
                      index: staggerIndex++,
                      child: const Align(
                        alignment: Alignment.centerLeft,
                        child: Text('Areas for Review',
                            style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                                color: AppColors.textPrimary)),
                      ),
                    ),
                    const SizedBox(height: 12),
                    StaggeredFadeSlide(
                      index: staggerIndex++,
                      child: Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        alignment: WrapAlignment.start,
                        children: eval.weakAreas
                            .map((wa) => Chip(
                                  label: Text(wa),
                                  backgroundColor:
                                      AppColors.warning.withAlpha(20),
                                  side: BorderSide(
                                      color: AppColors.warning.withAlpha(40)),
                                  labelStyle: const TextStyle(
                                      color: AppColors.warning, fontSize: 13),
                                ))
                            .toList(),
                      ),
                    ),
                    const SizedBox(height: 32),
                  ],

                  // Feedback text
                  StaggeredFadeSlide(
                    index: staggerIndex++,
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: Text(eval.feedback,
                          style: const TextStyle(
                              fontSize: 15,
                              height: 1.5,
                              color: AppColors.textPrimary)),
                    ),
                  ),
                  const SizedBox(height: 40),

                  // Per-question breakdown
                  if (eval.questionResults.isNotEmpty) ...[
                    StaggeredFadeSlide(
                      index: staggerIndex++,
                      child: const Align(
                        alignment: Alignment.centerLeft,
                        child: Text('Breakdown',
                            style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                                color: AppColors.textPrimary)),
                      ),
                    ),
                    const SizedBox(height: 16),
                    for (int i = 0; i < eval.questionResults.length; i++)
                      StaggeredFadeSlide(
                        index: staggerIndex++,
                        child: _QuestionBreakdownCard(
                          qNum: i + 1,
                          result: eval.questionResults[i],
                        ),
                      ),
                  ],
                ],
              ),
            ),

            // Continue button
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
                    style: ElevatedButton.styleFrom(
                      backgroundColor:
                          eval.passed ? AppColors.success : AppColors.warning,
                      foregroundColor: eval.passed
                          ? Colors.white
                          : AppColors.background,
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(eval.passed
                            ? 'Continue Journey'
                            : 'Start Remediation'),
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

class _QuestionBreakdownCard extends StatelessWidget {
  final int qNum;
  final dynamic result; // using dynamic here to avoid re-importing model

  const _QuestionBreakdownCard({required this.qNum, required this.result});

  @override
  Widget build(BuildContext context) {
    final bool isCorrect = result.isCorrect;
    final color = isCorrect ? AppColors.success : AppColors.error;
    final icon = isCorrect ? Icons.check_circle : Icons.cancel;

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface2,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withAlpha(50)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'Q$qNum: ${result.question}',
                  style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: AppColors.textPrimary),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Padding(
            padding: const EdgeInsets.only(left: 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (!isCorrect) ...[
                  Text(
                    'Your answer:',
                    style: TextStyle(
                        fontSize: 11,
                        color: AppColors.error.withAlpha(150),
                        fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    result.options[result.userIndex],
                    style: const TextStyle(
                        fontSize: 13, color: AppColors.error),
                  ),
                  const SizedBox(height: 12),
                ],
                Text(
                  isCorrect ? 'Your answer (Correct):' : 'Correct answer:',
                  style: TextStyle(
                      fontSize: 11,
                      color: AppColors.success.withAlpha(150),
                      fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 4),
                Text(
                  result.options[result.correctIndex],
                  style: const TextStyle(
                      fontSize: 13, color: AppColors.success),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
