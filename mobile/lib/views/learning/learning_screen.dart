/// Main learning screen — orchestration shell that swaps views based on workflow state.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../models/workflow.dart';
import '../../viewmodels/workflow_viewmodel.dart';
import '../../widgets/error_banner.dart';
import 'branch_view.dart';
import 'completed_view.dart';
import 'evaluation_view.dart';
import 'wait_view.dart';
import '../../widgets/learning_graph_view.dart';
import 'node_detail_sheet.dart';

class LearningScreen extends ConsumerWidget {
  final String sessionId;

  const LearningScreen({super.key, required this.sessionId});

  void _showNodeDetail(
      BuildContext context, NodeHierarchyMeta node, WorkflowSnapshot workflow) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (_) => NodeDetailSheet(
        sessionId: sessionId,
        nodeMeta: node,
        workflow: workflow,
      ),
    );
  }

  void _handlePrimaryAction(
      BuildContext context, WidgetRef ref, WorkflowSnapshot workflow) {
    switch (workflow.nextAction) {
      case NextAction.chooseBranch:
        showModalBottomSheet(
          context: context,
          isScrollControlled: true,
          useSafeArea: true,
          backgroundColor: Colors.transparent,
          builder: (_) => BranchView(
            sessionId: sessionId,
            workflow: workflow,
          ),
        );
        break;
      case NextAction.advance:
      case NextAction.advanceRemediation:
        if (workflow.evaluationReady) {
          showModalBottomSheet(
            context: context,
            isScrollControlled: true,
            useSafeArea: true,
            backgroundColor: Colors.transparent,
            builder: (_) => EvaluationView(sessionId: sessionId),
          );
        } else {
          ref
              .read(workflowViewModelProvider(sessionId).notifier)
              .continueJourney();
        }
        break;
      case NextAction.takeQuiz:
        // Find current node meta and open sheet
        final currentMeta = workflow.nodeCatalog.cast<NodeHierarchyMeta?>().firstWhere(
            (n) => n?.nodeId == workflow.currentNode,
            orElse: () => null);
        if (currentMeta != null) {
          _showNodeDetail(context, currentMeta, workflow);
        }
        break;
      case NextAction.completed:
        showModalBottomSheet(
          context: context,
          isScrollControlled: true,
          useSafeArea: true,
          backgroundColor: Colors.transparent,
          builder: (_) => CompletedView(workflow: workflow),
        );
        break;
      default:
        // Open current node detail by default
        final currentMeta = workflow.nodeCatalog.cast<NodeHierarchyMeta?>().firstWhere(
            (n) => n?.nodeId == workflow.currentNode,
            orElse: () => null);
        if (currentMeta != null) {
          _showNodeDetail(context, currentMeta, workflow);
        }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final workflowAsync = ref.watch(workflowViewModelProvider(sessionId));

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/dashboard'),
        ),
        title: workflowAsync.whenOrNull(
          data: (wf) => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                wf.topic.isNotEmpty ? wf.topic : 'Learning',
                style: const TextStyle(fontSize: 16),
              ),
              if (wf.currentNode.isNotEmpty)
                Text(
                  wf.currentNode,
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppColors.textMuted,
                    fontWeight: FontWeight.w400,
                  ),
                ),
            ],
          ),
        ),
      ),
      body: workflowAsync.when(
        loading: () => const WaitView(),
        error: (err, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: ErrorBanner(
              message: err.toString(),
              onRetry: () => ref
                  .read(workflowViewModelProvider(sessionId).notifier)
                  .refresh(),
            ),
          ),
        ),
        data: (workflow) => _buildBody(context, ref, workflow),
      ),
    );
  }

  Widget _buildBody(
      BuildContext context, WidgetRef ref, WorkflowSnapshot workflow) {
    return Stack(
      children: [
        // Graph Canvas
        Positioned.fill(
          child: LearningGraphView(
            workflow: workflow,
            onNodeTapped: (node) => _showNodeDetail(context, node, workflow),
          ),
        ),

        // Docked Status Panel
        Positioned(
          left: 20,
          top: 20,
          width: 320,
          child: _StatusPanel(
            workflow: workflow,
            onActionTapped: () => _handlePrimaryAction(context, ref, workflow),
          ),
        ),

        // Wait Overlay (AI Reasoning)
        if (workflow.isLoading || workflow.nextAction == NextAction.wait)
          Positioned(
            left: 20,
            right: 20,
            bottom: 20,
            child: WaitView(reasoning: workflow.orchestratorReasoning),
          ),
      ],
    );
  }
}

class _StatusPanel extends StatelessWidget {
  final WorkflowSnapshot workflow;
  final VoidCallback onActionTapped;

  const _StatusPanel({
    required this.workflow,
    required this.onActionTapped,
  });

  @override
  Widget build(BuildContext context) {
    String actionText = 'Continue';
    String actionDesc = 'Continue your learning journey.';

    switch (workflow.nextAction) {
      case NextAction.takeQuiz:
        actionText = 'Open Quiz';
        actionDesc = 'Submit quiz answers to continue.';
        break;
      case NextAction.chooseBranch:
        actionText = 'Choose Path';
        actionDesc = 'Select your next topic.';
        break;
      case NextAction.advance:
      case NextAction.advanceRemediation:
        if (workflow.evaluationReady) {
          actionText = 'View Evaluation';
          actionDesc = 'Check your quiz score and feedback.';
        } else {
          actionText = 'Next Topic';
          actionDesc = 'Advance to the next concept.';
        }
        break;
      case NextAction.completed:
        actionText = 'Finish';
        actionDesc = 'You have mastered this topic!';
        break;
      default:
        actionText = 'Open Lesson';
        actionDesc = 'Read the lesson material.';
        break;
    }

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.surface.withAlpha(230),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.border),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withAlpha(100),
            blurRadius: 20,
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'JOURNEY',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: AppColors.textMuted,
              letterSpacing: 1.5,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            workflow.topic,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '${workflow.status} • ${workflow.currentNode.replaceAll('_', ' ')}',
            style: const TextStyle(
              fontSize: 12,
              color: AppColors.primary400,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            actionDesc,
            style: const TextStyle(
              fontSize: 13,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 16),
          Align(
            alignment: Alignment.centerRight,
            child: ElevatedButton(
              onPressed: onActionTapped,
              child: Text(actionText),
            ),
          ),
        ],
      ),
    );
  }
}

