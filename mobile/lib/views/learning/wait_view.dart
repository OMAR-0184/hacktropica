/// Loading state for the learning engine.
library;

import 'package:flutter/material.dart';
import 'package:lottie/lottie.dart';

import '../../config/theme.dart';

class WaitView extends StatelessWidget {
  final String? reasoning;

  const WaitView({super.key, this.reasoning});

  @override
  Widget build(BuildContext context) {
    if (reasoning == null || reasoning!.isEmpty) {
      return const SizedBox.shrink();
    }

    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.0, end: 1.0),
      duration: MediaQuery.of(context).disableAnimations
          ? Duration.zero
          : const Duration(milliseconds: 300),
      curve: Curves.easeOut,
      builder: (context, opacity, child) => Opacity(
        opacity: opacity,
        child: child,
      ),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.background.withAlpha(240),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.primary500.withAlpha(80)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withAlpha(100),
              blurRadius: 20,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: SizedBox(
                width: 24,
                height: 24,
                child: Lottie.asset(
                  'assets/lottie/thinking.json',
                  fit: BoxFit.contain,
                  errorBuilder: (context, error, stackTrace) => const _PulsingDots(),
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Text(
                reasoning!,
                style: TextStyle(
                  color: AppColors.primary100,
                  fontSize: 13,
                  height: 1.4,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Three dots that pulse sequentially with a stagger.
class _PulsingDots extends StatefulWidget {
  const _PulsingDots();

  @override
  State<_PulsingDots> createState() => _PulsingDotsState();
}

class _PulsingDotsState extends State<_PulsingDots>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (MediaQuery.of(context).disableAnimations) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(
          3,
          (_) => Container(
            width: 5,
            height: 5,
            margin: const EdgeInsets.symmetric(horizontal: 1.5),
            decoration: BoxDecoration(
              color: AppColors.primary400,
              shape: BoxShape.circle,
            ),
          ),
        ),
      );
    }

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(3, (index) {
            // Each dot is offset by 0.2 in the animation cycle
            final delay = index * 0.2;
            final t = (_controller.value + delay) % 1.0;
            // Scale from 0.4 to 1.0 and back using a sine curve
            final scale = 0.4 + 0.6 * _pulse(t);
            final alpha = (100 + 155 * _pulse(t)).toInt();

            return Container(
              width: 5,
              height: 5,
              margin: const EdgeInsets.symmetric(horizontal: 1.5),
              child: Transform.scale(
                scale: scale,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: AppColors.primary400.withAlpha(alpha),
                    shape: BoxShape.circle,
                  ),
                ),
              ),
            );
          }),
        );
      },
    );
  }

  /// Returns 0→1→0 pulse curve over the [0, 1) range.
  double _pulse(double t) {
    if (t < 0.5) return t * 2;
    return 2 - t * 2;
  }
}
