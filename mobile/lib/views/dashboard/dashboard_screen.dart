/// Dashboard screen — lists sessions, start new, archive.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../config/constants.dart';
import '../../config/theme.dart';
import '../../models/session.dart';
import '../../viewmodels/auth_viewmodel.dart';
import '../../viewmodels/session_viewmodel.dart';
import '../../widgets/error_banner.dart';
import '../../widgets/loading_shimmer.dart';
import '../../widgets/press_scale.dart';
import '../../widgets/staggered_list.dart';
import '../../widgets/cinematic_background.dart';
import 'new_session_sheet.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sessionsAsync = ref.watch(sessionListProvider);

    return CinematicBackground(
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
        title: const Text('Cognimap'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout, size: 20),
            tooltip: 'Logout',
            onPressed: () async {
              await ref.read(authViewModelProvider.notifier).logout();
              if (context.mounted) context.go('/auth');
            },
          ),
        ],
      ),
      body: sessionsAsync.when(
        loading: () => ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: 3,
          itemBuilder: (_, __) => const Padding(
            padding: EdgeInsets.only(bottom: 12),
            child: LoadingShimmer(height: 90, borderRadius: 16),
          ),
        ),
        error: (err, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: ErrorBanner(
              message: SessionListViewModel.errorMessage(err),
              onRetry: () => ref.invalidate(sessionListProvider),
            ),
          ),
        ),
        data: (sessions) {
          if (sessions.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Pulsing glow on empty-state icon
                  TweenAnimationBuilder<double>(
                    tween: Tween(begin: 0.3, end: 0.8),
                    duration: const Duration(seconds: 2),
                    curve: Curves.easeInOut,
                    builder: (context, value, child) => Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: AppColors.primary500.withAlpha((value * 20).toInt()),
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.primary500.withAlpha((value * 30).toInt()),
                            blurRadius: 24,
                          ),
                        ],
                      ),
                      child: child,
                    ),
                    child: Icon(Icons.explore_outlined,
                        size: 64, color: AppColors.textDisabled),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'No active sessions',
                    style: TextStyle(
                        color: AppColors.textMuted,
                        fontSize: 16,
                        fontWeight: FontWeight.w500),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Tap + to start learning something new',
                    style:
                        TextStyle(color: AppColors.textDisabled, fontSize: 13),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(sessionListProvider),
            color: AppColors.primary500,
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: sessions.length + 1,
              itemBuilder: (context, index) {
                if (index == 0) {
                  return const Padding(
                    padding: EdgeInsets.only(top: 8, bottom: 24, left: 4),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Welcome back',
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.w700,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Resume your journey or explore something new.',
                          style: TextStyle(
                            fontSize: 14,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ),
                  );
                }
                
                final session = sessions[index - 1];
                return Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: StaggeredFadeSlide(
                    index: index,
                    child: PressScale(
                      onTap: () => context.go('/learn/${session.sessionId}'),
                      child: _SessionCard(session: session),
                    ),
                  ),
                );
              },
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        backgroundColor: AppColors.primary500,
        onPressed: () {
          final sessions = sessionsAsync.value ?? [];
          if (sessions.length >= AppConstants.maxActiveSessions) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text(
                    'Maximum 5 active sessions. Archive one to start a new session.'),
              ),
            );
            return;
          }
          showModalBottomSheet(
            context: context,
            isScrollControlled: true,
            builder: (_) => const NewSessionSheet(),
          );
        },
        child: const Icon(Icons.add, color: Colors.white),
      ),
    ));
  }
}

class _SessionCard extends ConsumerWidget {
  final SessionSummary session;

  const _SessionCard({required this.session});

  Color get _statusColor => switch (session.status) {
        'ready' => AppColors.success,
        'running' || 'initializing' || 'evaluating' => AppColors.warning,
        'completed' => AppColors.primary400,
        'error' => AppColors.error,
        _ => AppColors.textMuted,
      };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Dismissible(
      key: ValueKey(session.sessionId),
      direction: DismissDirection.endToStart,
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        decoration: BoxDecoration(
          color: AppColors.error.withAlpha(30),
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Icon(Icons.archive_outlined, color: AppColors.error),
      ),
      confirmDismiss: (_) async {
        return await showDialog<bool>(
              context: context,
              builder: (ctx) => AlertDialog(
                backgroundColor: AppColors.surface,
                title: const Text('Archive session?'),
                content: Text(
                    'Archive "${session.topic}"? You can\'t undo this.'),
                actions: [
                  TextButton(
                      onPressed: () => Navigator.pop(ctx, false),
                      child: const Text('Cancel')),
                  TextButton(
                      onPressed: () => Navigator.pop(ctx, true),
                      child: const Text('Archive',
                          style: TextStyle(color: AppColors.error))),
                ],
              ),
            ) ??
            false;
      },
      onDismissed: (_) {
        ref
            .read(sessionListProvider.notifier)
            .archiveSession(session.sessionId);
      },
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            // Status dot
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _statusColor,
                boxShadow: [
                  BoxShadow(
                      color: _statusColor.withAlpha(80), blurRadius: 6),
                ],
              ),
            ),
            const SizedBox(width: 14),

            // Info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    session.topic,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 15,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    session.status.toUpperCase(),
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: _statusColor,
                      letterSpacing: 0.8,
                    ),
                  ),
                ],
              ),
            ),

            // Progress
            if (session.overallProgress > 0)
              SizedBox(
                width: 40,
                height: 40,
                child: CircularProgressIndicator(
                  value: session.overallProgress,
                  strokeWidth: 3,
                  backgroundColor: AppColors.surface2,
                  color: AppColors.primary400,
                ),
              ),

            const SizedBox(width: 8),
            const Icon(Icons.chevron_right,
                color: AppColors.textDisabled, size: 20),
          ],
        ),
      ),
    );
  }
}
