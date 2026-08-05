import 'package:flutter/material.dart';
import '../config/theme.dart';

class PaperBackground extends StatelessWidget {
  final Widget child;

  const PaperBackground({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColors.background,
      child: CustomPaint(
        painter: GraphPaperPainter(),
        child: child,
      ),
    );
  }
}

class GraphPaperPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final Paint linePaint = Paint()
      ..color = AppColors.gridLine.withOpacity(0.4)
      ..strokeWidth = 1.0;

    final Paint marginPaint = Paint()
      ..color = AppColors.gridLineMargin.withOpacity(0.6)
      ..strokeWidth = 1.5;

    const double gridSize = 30.0;

    // Draw horizontal lines
    for (double i = 0; i <= size.height; i += gridSize) {
      canvas.drawLine(Offset(0, i), Offset(size.width, i), linePaint);
    }

    // Draw vertical lines
    for (double i = 0; i <= size.width; i += gridSize) {
      canvas.drawLine(Offset(i, 0), Offset(i, size.height), linePaint);
    }

    // Draw red margin lines on the left
    canvas.drawLine(const Offset(40, 0), Offset(40, size.height), marginPaint);
    canvas.drawLine(const Offset(44, 0), Offset(44, size.height), marginPaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
