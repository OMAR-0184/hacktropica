/// Dashboard screen — lists sessions, start new, archive.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:lottie/lottie.dart';

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
                  // Lottie animation for empty state
                  Lottie.asset(
                    'assets/lottie/empty_dashboard.json',
                    width: 200,
                    height: 200,
                    fit: BoxFit.contain,
                    // If the user hasn't added the file yet, we can show a placeholder or let Lottie show its default error widget if the json is empty. 
                    // Since it's an empty {}, it will throw an exception if we don't catch it or provide an errorBuilder.
                    errorBuilder: (context, error, stackTrace) => Icon(
                      Icons.explore_outlined,
                      size: 64,
                      color: AppColors.textDisabled,
                    ),
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
                  return Padding(
                    padding: const EdgeInsets.only(top: 8, bottom: 24, left: 4),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        ShaderMask(
                          shaderCallback: (bounds) => const LinearGradient(
                            colors: [Colors.white, AppColors.primary200, AppColors.accent500],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ).createShader(bounds),
                          child: Text(
                            'Welcome back.',
                            style: GoogleFonts.roboto(
                              fontSize: 54,
                              fontWeight: FontWeight.w900,
                              height: 1.0,
                              letterSpacing: -2.0,
                              color: Colors.white,
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Resume your journey or explore something new.',
                          style: GoogleFonts.robotoMono(
                            fontSize: 14,
                            color: AppColors.textMuted,
                            letterSpacing: 0.5,
                          ),
                        ),
                        const SizedBox(height: 40),
                        Text(
                          'YOUR SUBJECTS',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            letterSpacing: 1.2,
                            color: AppColors.textDisabled,
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
      floatingActionButton: sessionsAsync.value?.isEmpty == true
          ? FloatingActionButton.extended(
              backgroundColor: AppColors.primary500,
              onPressed: () => _handleNewSession(context, ref, sessionsAsync.value),
              icon: const Icon(Icons.add, color: Colors.white),
              label: const Text('New Subject', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
            )
          : FloatingActionButton(
              backgroundColor: AppColors.primary500,
              onPressed: () => _handleNewSession(context, ref, sessionsAsync.value),
              child: const Icon(Icons.add, color: Colors.white),
            ),
    ));
  }

  void _handleNewSession(BuildContext context, WidgetRef ref, List<SessionSummary>? sessions) {
    if (sessions != null && sessions.length >= AppConstants.maxActiveSessions) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Maximum 5 active sessions. Archive one to start a new session.')),
      );
      return;
    }
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => const NewSessionSheet(),
    );
  }
}

class _SessionCard extends StatefulWidget {
  final SessionSummary session;

  const _SessionCard({required this.session});

  @override
  State<_SessionCard> createState() => _SessionCardState();
}

class _SessionCardState extends State<_SessionCard> with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  Color get _statusColor => switch (widget.session.status) {
        'running' || 'evaluating' => AppColors.primary400,
        'initializing' => AppColors.warning,
        'completed' => AppColors.success,
        'error' => AppColors.error,
        _ => AppColors.textMuted,
      };
      
  String _timeAgo(String dateString) {
    try {
      final date = DateTime.parse(dateString);
      final diff = DateTime.now().difference(date);
      if (diff.inDays > 0) return '${diff.inDays} days ago';
      if (diff.inHours > 0) return '${diff.inHours} hours ago';
      if (diff.inMinutes > 0) return '${diff.inMinutes} mins ago';
      return 'Just now';
    } catch (_) {
      return 'Recently';
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = widget.session;
    final isInitializing = session.status == 'initializing';
    final reduceMotion = MediaQuery.of(context).disableAnimations;
    
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
                content: Text('Archive "${session.topic}"? You can\'t undo this.'),
                actions: [
                  TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
                  TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Archive', style: TextStyle(color: AppColors.error))),
                ],
              ),
            ) ??
            false;
      },
      onDismissed: (_) {
        ProviderScope.containerOf(context, listen: false)
            .read(sessionListProvider.notifier)
            .archiveSession(session.sessionId);
      },
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withOpacity(0.05)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Animated Status Dot
            AnimatedBuilder(
              animation: _pulseController,
              builder: (context, child) {
                final opacity = (isInitializing && !reduceMotion) 
                    ? 0.4 + 0.6 * _pulseController.value 
                    : 1.0;
                return Opacity(
                  opacity: opacity,
                  child: Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: _statusColor,
                      boxShadow: [
                        BoxShadow(color: _statusColor.withAlpha(80), blurRadius: 6),
                      ],
                    ),
                  ),
                );
              },
            ),
            const SizedBox(width: 16),

            // Main Info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    session.topic,
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Text(
                        session.status.toUpperCase(),
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: _statusColor,
                          letterSpacing: 0.8,
                        ),
                      ),
                      if (session.overallProgress > 0) ...[
                        const SizedBox(width: 12),
                        Expanded(
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(2),
                            child: LinearProgressIndicator(
                              value: session.overallProgress,
                              minHeight: 4,
                              backgroundColor: AppColors.surface2,
                              color: AppColors.primary400,
                            ),
                          ),
                        ),
                        const SizedBox(width: 16),
                      ],
                    ],
                  ),
                ],
              ),
            ),

            // Trailing
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _timeAgo(session.createdAt),
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textDisabled,
                  ),
                ),
                const SizedBox(width: 4),
                const Icon(Icons.chevron_right, color: AppColors.textDisabled, size: 20),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
