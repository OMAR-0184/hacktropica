/// Branching view to select the next topic in the learning tree.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../config/theme.dart';
import '../../models/workflow.dart';
import '../../viewmodels/workflow_viewmodel.dart';
import '../../widgets/staggered_list.dart';

class BranchView extends ConsumerStatefulWidget {
  final String sessionId;
  final WorkflowSnapshot workflow;

  const BranchView({
    super.key,
    required this.sessionId,
    required this.workflow,
  });

  @override
  ConsumerState<BranchView> createState() => _BranchViewState();
}

class _BranchViewState extends ConsumerState<BranchView> {
  String? _selectedNode;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    // Default to the recommended node if available
    _selectedNode = widget.workflow.recommendedNode;
  }

  void _submit() async {
    if (_selectedNode == null) return;
    setState(() => _submitting = true);

    await ref
        .read(workflowViewModelProvider(widget.sessionId).notifier)
        .continueJourney(selectedNode: _selectedNode);

    if (mounted) setState(() => _submitting = false);
  }

  @override
  Widget build(BuildContext context) {
    final options = widget.workflow.options;

    return Stack(
      children: [
        SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 100),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              StaggeredFadeSlide(
                index: 0,
                child: const Text(
                  'Choose Your Path',
                  style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              const SizedBox(height: 8),
              StaggeredFadeSlide(
                index: 1,
                child: const Text(
                  'Select the next topic you want to explore.',
                  style: TextStyle(
                    fontSize: 14,
                    color: AppColors.textMuted,
                  ),
                ),
              ),
              const SizedBox(height: 32),

              // Options list
              for (int i = 0; i < options.length; i++) ...[
                StaggeredFadeSlide(
                  index: i + 2,
                  child: _buildOptionCard(options[i]),
                ),
                const SizedBox(height: 16),
              ],
            ],
          ),
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
                    _selectedNode != null && !_submitting ? _submit : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _selectedNode != null
                      ? AppColors.primary500
                      : AppColors.surface2,
                  foregroundColor: _selectedNode != null
                      ? Colors.white
                      : AppColors.textMuted,
                ),
                child: _submitting
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : Text(_selectedNode == null
                        ? 'Select a topic'
                        : 'Explore $_selectedNode'),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildOptionCard(String option) {
    final isSelected = _selectedNode == option;
    final isRecommended = option == widget.workflow.recommendedNode;

    return InkWell(
      onTap: _submitting ? null : () => setState(() => _selectedNode = option),
      borderRadius: BorderRadius.circular(16),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOut,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.primary500.withAlpha(20) : AppColors.surface2,
          border: Border.all(
            color: isSelected ? AppColors.primary500 : AppColors.border,
            width: isSelected ? 2 : 1,
          ),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                AnimatedSwitcher(
                  duration: const Duration(milliseconds: 200),
                  child: Icon(
                    isSelected ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                    key: ValueKey(isSelected),
                    color: isSelected ? AppColors.primary500 : AppColors.textMuted,
                    size: 20,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    option,
                    style: TextStyle(
                      color: isSelected ? AppColors.primary100 : AppColors.textPrimary,
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                if (isRecommended)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.success.withAlpha(25),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppColors.success.withAlpha(60)),
                    ),
                    child: const Text(
                      'RECOMMENDED',
                      style: TextStyle(
                        color: AppColors.success,
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
              ],
            ),
            if (isRecommended && widget.workflow.recommendationReason != null) ...[
              const SizedBox(height: 16),
              Padding(
                padding: const EdgeInsets.only(left: 32),
                child: Text(
                  widget.workflow.recommendationReason!,
                  style: const TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 13,
                    height: 1.4,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
