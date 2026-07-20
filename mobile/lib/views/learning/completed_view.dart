/// Completion view shown when the learning journey is finished.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../config/theme.dart';
import '../../models/workflow.dart';
import '../../widgets/staggered_list.dart';

class CompletedView extends StatelessWidget {
  final WorkflowSnapshot workflow;

  const CompletedView({super.key, required this.workflow});

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.of(context).disableAnimations;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Celebration: bouncy scale-in trophy with pulsing glow
            StaggeredFadeSlide(
              index: 0,
              slideOffset: 0,
              child: TweenAnimationBuilder<double>(
                tween: Tween(begin: reduceMotion ? 1.0 : 0.0, end: 1.0),
                duration: reduceMotion
                    ? Duration.zero
                    : const Duration(milliseconds: 600),
                curve: Curves.easeOutBack,
                builder: (context, scale, child) => Transform.scale(
                  scale: scale,
                  child: child,
                ),
                child: _PulsingGlowCircle(
                  color: AppColors.success,
                  reduceMotion: reduceMotion,
                  child: const Icon(
                    Icons.emoji_events_outlined,
                    size: 80,
                    color: AppColors.success,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 32),
            StaggeredFadeSlide(
              index: 1,
              child: const Text(
                'Journey Completed!',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
            const SizedBox(height: 12),
            StaggeredFadeSlide(
              index: 2,
              child: Text(
                'You have mastered ${workflow.topic}.',
                style: const TextStyle(
                  fontSize: 16,
                  color: AppColors.textMuted,
                ),
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(height: 48),
            StaggeredFadeSlide(
              index: 3,
              child: SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () => context.go('/dashboard'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppColors.success,
                  ),
                  child: const Text('Return to Dashboard'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// A circle that subtly pulses its glow shadow.
class _PulsingGlowCircle extends StatefulWidget {
  final Color color;
  final bool reduceMotion;
  final Widget child;

  const _PulsingGlowCircle({
    required this.color,
    required this.reduceMotion,
    required this.child,
  });

  @override
  State<_PulsingGlowCircle> createState() => _PulsingGlowCircleState();
}

class _PulsingGlowCircleState extends State<_PulsingGlowCircle>
    with SingleTickerProviderStateMixin {
  AnimationController? _controller;
  Animation<double>? _glowAnim;

  @override
  void initState() {
    super.initState();
    if (!widget.reduceMotion) {
      _controller = AnimationController(
        vsync: this,
        duration: const Duration(seconds: 2),
      );
      _glowAnim = Tween<double>(begin: 12.0, end: 30.0).animate(
        CurvedAnimation(parent: _controller!, curve: Curves.easeInOut),
      );
      _controller!.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.reduceMotion || _glowAnim == null) {
      return Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: widget.color.withAlpha(20),
          shape: BoxShape.circle,
        ),
        child: widget.child,
      );
    }

    return AnimatedBuilder(
      animation: _glowAnim!,
      builder: (context, child) => Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: widget.color.withAlpha(20),
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: widget.color.withAlpha(30),
              blurRadius: _glowAnim!.value,
            ),
          ],
        ),
        child: child,
      ),
      child: widget.child,
    );
  }
}
