/// Animated cinematic background mimicking a WebGL neural fog.
library;

import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../config/theme.dart';

class CinematicBackground extends StatefulWidget {
  final Widget child;

  const CinematicBackground({super.key, required this.child});

  @override
  State<CinematicBackground> createState() => _CinematicBackgroundState();
}

class _CinematicBackgroundState extends State<CinematicBackground>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 15),
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
      return Container(
        color: AppColors.background,
        child: widget.child,
      );
    }

    return Stack(
      children: [
        // Base dark background
        Container(color: AppColors.background),
        // Animated gradient blobs
        AnimatedBuilder(
          animation: _controller,
          builder: (context, _) {
            final t = _controller.value * 2 * math.pi;
            return CustomPaint(
              painter: _CinematicPainter(t),
              child: const SizedBox.expand(),
            );
          },
        ),
        // The foreground content
        widget.child,
      ],
    );
  }
}

class _CinematicPainter extends CustomPainter {
  final double t;

  _CinematicPainter(this.t);

  @override
  void paint(Canvas canvas, Size size) {
    // Top right blob (primary)
    final cx1 = size.width * (0.8 + 0.1 * math.sin(t));
    final cy1 = size.height * (0.1 + 0.1 * math.cos(t));
    final paint1 = Paint()
      ..shader = RadialGradient(
        colors: [
          AppColors.primary500.withAlpha(20),
          AppColors.primary500.withAlpha(0),
        ],
      ).createShader(Rect.fromCircle(center: Offset(cx1, cy1), radius: size.width));
    canvas.drawCircle(Offset(cx1, cy1), size.width, paint1);

    // Bottom left blob (accent)
    final cx2 = size.width * (0.1 + 0.2 * math.cos(t * 1.5));
    final cy2 = size.height * (0.8 + 0.1 * math.sin(t * 0.8));
    final paint2 = Paint()
      ..shader = RadialGradient(
        colors: [
          AppColors.accent500.withAlpha(15),
          AppColors.accent500.withAlpha(0),
        ],
      ).createShader(Rect.fromCircle(center: Offset(cx2, cy2), radius: size.width * 0.8));
    canvas.drawCircle(Offset(cx2, cy2), size.width * 0.8, paint2);

    // subtle grid overly pattern
    final gridPaint = Paint()
      ..color = Colors.white.withAlpha(2)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.0;
      
    final cellSize = 40.0;
    for (double x = 0; x < size.width; x += cellSize) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), gridPaint);
    }
    for (double y = 0; y < size.height; y += cellSize) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _CinematicPainter old) => old.t != t;
}
