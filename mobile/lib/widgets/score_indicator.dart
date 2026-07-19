/// Animated circular score indicator.
library;

import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../config/theme.dart';

class ScoreIndicator extends StatelessWidget {
  final double score; // 0.0 – 1.0
  final double size;
  final bool showLabel;

  const ScoreIndicator({
    super.key,
    required this.score,
    this.size = 120,
    this.showLabel = true,
  });

  Color get _color {
    if (score >= 0.8) return AppColors.success;
    if (score >= 0.6) return AppColors.primary400;
    if (score >= 0.4) return AppColors.warning;
    return AppColors.error;
  }

  @override
  Widget build(BuildContext context) {
    // Respect reduced-motion preference
    final reduceMotion = MediaQuery.of(context).disableAnimations;

    return SizedBox(
      width: size,
      height: size,
      child: TweenAnimationBuilder<double>(
        tween: Tween(begin: 0, end: score),
        duration: reduceMotion ? Duration.zero : const Duration(milliseconds: 800),
        curve: Curves.easeOutCubic,
        builder: (context, value, child) {
          return CustomPaint(
            painter: _ScoreArcPainter(value, _color),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '${(value * 100).round()}%',
                    style: TextStyle(
                      color: _color,
                      fontSize: size * 0.22,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  if (showLabel)
                    Text(
                      score >= 0.6 ? 'Passed' : 'Failed',
                      style: TextStyle(
                        color: _color.withAlpha(180),
                        fontSize: size * 0.1,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class _ScoreArcPainter extends CustomPainter {
  final double progress;
  final Color color;

  _ScoreArcPainter(this.progress, this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 6;

    // Background track
    canvas.drawCircle(
      center,
      radius,
      Paint()
        ..color = AppColors.surface2
        ..style = PaintingStyle.stroke
        ..strokeWidth = 8,
    );

    // Progress arc
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -math.pi / 2,
      2 * math.pi * progress,
      false,
      Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 8
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(covariant _ScoreArcPainter old) =>
      old.progress != progress || old.color != color;
}
