/// Renders a multiple choice quiz for the current topic.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/theme.dart';
import '../../models/workflow.dart';
import '../../viewmodels/quiz_viewmodel.dart';
import '../../viewmodels/workflow_viewmodel.dart';
import '../../widgets/error_banner.dart';
import '../../widgets/staggered_list.dart';

import 'wait_view.dart';

class QuizView extends ConsumerStatefulWidget {
  final String sessionId;
  final WorkflowSnapshot workflow;
  final VoidCallback? onQuizSubmitted;

  const QuizView({
    super.key,
    required this.sessionId,
    required this.workflow,
    this.onQuizSubmitted,
  });

  @override
  ConsumerState<QuizView> createState() => _QuizViewState();
}

class _QuizViewState extends ConsumerState<QuizView> {
  final Map<int, int> _selectedAnswers = {};
  bool _submitting = false;

  void _submit(int totalQuestions) async {
    if (_selectedAnswers.length < totalQuestions) return;

    setState(() => _submitting = true);

    try {
      final answers = List<int>.generate(
        totalQuestions,
        (index) => _selectedAnswers[index]!,
      );

      await ref
          .read(workflowViewModelProvider(widget.sessionId).notifier)
          .continueJourney(answers: answers);
          
      widget.onQuizSubmitted?.call();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(e.toString()),
            backgroundColor: AppColors.error,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final quizAsync = ref.watch(quizViewModelProvider(widget.sessionId));

    return quizAsync.when(
      loading: () => const WaitView(),
      error: (err, _) => Padding(
        padding: const EdgeInsets.all(24),
        child: ErrorBanner(
          message: err.toString(),
          onRetry: () =>
              ref.read(quizViewModelProvider(widget.sessionId).notifier).refresh(),
        ),
      ),
      data: (quiz) {
        if (quiz.questions.isEmpty) {
          return const Center(child: Text('No questions available.'));
        }

        final allAnswered = _selectedAnswers.length == quiz.questions.length;

        return Stack(
          children: [
            ListView.separated(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 100),
              itemCount: quiz.questions.length,
              separatorBuilder: (_, __) => const SizedBox(height: 32),
              itemBuilder: (context, qIndex) {
                final q = quiz.questions[qIndex];
                return StaggeredFadeSlide(
                  index: qIndex,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Question Number
                      Text(
                        'QUESTION ${qIndex + 1} OF ${quiz.questions.length}',
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1,
                          color: AppColors.primary400,
                        ),
                      ),
                      const SizedBox(height: 12),
                      // Question Text
                      Text(
                        q.question,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w500,
                          color: AppColors.textPrimary,
                          height: 1.5,
                        ),
                      ),
                      const SizedBox(height: 16),
                      // Options with AnimatedContainer
                      ...List.generate(q.options.length, (optIndex) {
                        final isSelected = _selectedAnswers[qIndex] == optIndex;
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: InkWell(
                            onTap: _submitting
                                ? null
                                : () => setState(
                                    () => _selectedAnswers[qIndex] = optIndex),
                            borderRadius: BorderRadius.circular(12),
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 200),
                              curve: Curves.easeOut,
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: isSelected
                                    ? AppColors.primary500.withAlpha(20)
                                    : AppColors.surface2,
                                border: Border.all(
                                  color: isSelected
                                      ? AppColors.primary500
                                      : AppColors.border,
                                ),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Row(
                                children: [
                                  // Radio
                                  AnimatedSwitcher(
                                    duration: const Duration(milliseconds: 200),
                                    child: Icon(
                                      isSelected
                                          ? Icons.radio_button_checked
                                          : Icons.radio_button_unchecked,
                                      key: ValueKey(isSelected),
                                      color: isSelected
                                          ? AppColors.primary500
                                          : AppColors.textMuted,
                                      size: 20,
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  // Option Text
                                  Expanded(
                                    child: Text(
                                      q.options[optIndex],
                                      style: TextStyle(
                                        color: isSelected
                                            ? AppColors.primary100
                                            : AppColors.textPrimary,
                                        fontSize: 14,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        );
                      }),
                    ],
                  ),
                );
              },
            ),

            // Submit Button
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
                    onPressed:
                        allAnswered && !_submitting ? () => _submit(quiz.questions.length) : null,
                    style: ElevatedButton.styleFrom(
                      backgroundColor:
                          allAnswered ? AppColors.primary500 : AppColors.surface2,
                      foregroundColor:
                          allAnswered ? Colors.white : AppColors.textMuted,
                    ),
                    child: _submitting
                        ? const SizedBox(
                            height: 20,
                            width: 20,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white),
                          )
                        : const Text('Submit Answers'),
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
