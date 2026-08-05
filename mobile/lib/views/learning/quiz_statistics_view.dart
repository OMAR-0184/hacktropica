import 'dart:math';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../models/evaluation.dart';
import '../../config/theme.dart';

class QuizStatisticsView extends StatelessWidget {
  final EvaluationResult evaluation;
  final String nodeId;

  const QuizStatisticsView({
    super.key,
    required this.evaluation,
    required this.nodeId,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildScoreCard(context),
          const SizedBox(height: 24),
          _buildFeedbackCard(theme),
          const SizedBox(height: 24),
          _buildWeakAreasCard(theme),
          const SizedBox(height: 24),
          _buildDetailedBreakdown(theme),
          const SizedBox(height: 48), // Padding at bottom
        ],
      ),
    );
  }

  Widget _buildScoreCard(BuildContext context) {
    final bool passed = evaluation.passed;
    final primaryColor = passed ? Colors.green.shade600 : Colors.red.shade500;
    
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFFDFBF7),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.brown.shade200, width: 2),
        boxShadow: const [
          BoxShadow(
            color: Colors.black12,
            offset: Offset(4, 4),
            blurRadius: 4,
          ),
          BoxShadow(
            color: Colors.white,
            offset: Offset(-2, -2),
            blurRadius: 4,
          ),
        ],
      ),
      padding: const EdgeInsets.all(24.0),
      child: Column(
        children: [
          Text(
            'Quiz Results',
            style: GoogleFonts.caveat(
              fontSize: 32,
              fontWeight: FontWeight.bold,
              color: Colors.black87,
            ),
          ),
          const SizedBox(height: 16),
          Stack(
            alignment: Alignment.center,
            children: [
              SizedBox(
                width: 140,
                height: 140,
                child: CustomPaint(
                  painter: _ScorePainter(
                    score: evaluation.score,
                    color: primaryColor,
                    backgroundColor: Colors.grey.shade300,
                  ),
                ),
              ),
              Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '${evaluation.scorePercent}%',
                    style: GoogleFonts.comicNeue(
                      fontSize: 40,
                      fontWeight: FontWeight.bold,
                      color: primaryColor,
                    ),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: primaryColor.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: primaryColor, width: 2),
            ),
            child: Text(
              passed ? 'Mastered!' : 'Needs Remediation',
              style: GoogleFonts.comicNeue(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: primaryColor,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFeedbackCard(ThemeData theme) {
    return _buildPaperSection(
      title: 'Tutor Feedback',
      icon: Icons.chat_bubble_outline,
      color: Colors.blue.shade600,
      content: Text(
        evaluation.feedback,
        style: GoogleFonts.comicNeue(
          fontSize: 16,
          fontWeight: FontWeight.w600,
          color: Colors.black87,
          height: 1.4,
        ),
      ),
    );
  }

  Widget _buildWeakAreasCard(ThemeData theme) {
    if (evaluation.weakAreas.isEmpty) {
      return const SizedBox.shrink();
    }
    
    return _buildPaperSection(
      title: 'Areas to Review',
      icon: Icons.warning_amber_rounded,
      color: Colors.orange.shade700,
      content: Wrap(
        spacing: 8.0,
        runSpacing: 8.0,
        children: evaluation.weakAreas.map((area) {
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.orange.shade100,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.orange.shade300),
            ),
            child: Text(
              area,
              style: GoogleFonts.comicNeue(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: Colors.orange.shade900,
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildDetailedBreakdown(ThemeData theme) {
    if (evaluation.questionResults.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8.0),
          child: Text(
            'Question Breakdown',
            style: GoogleFonts.caveat(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: Colors.black87,
            ),
          ),
        ),
        ...evaluation.questionResults.asMap().entries.map((entry) {
          final index = entry.key;
          final result = entry.value;
          final isCorrect = result.isCorrect;
          
          return Container(
            margin: const EdgeInsets.only(bottom: 16),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: isCorrect ? Colors.green.shade300 : Colors.red.shade300,
                width: 2,
              ),
              boxShadow: const [
                BoxShadow(
                  color: Colors.black12,
                  offset: Offset(2, 2),
                  blurRadius: 2,
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: isCorrect ? Colors.green.shade100 : Colors.red.shade100,
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        isCorrect ? Icons.check : Icons.close,
                        color: isCorrect ? Colors.green.shade700 : Colors.red.shade700,
                        size: 20,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Q${index + 1}: ${result.question}',
                        style: GoogleFonts.comicNeue(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Colors.black87,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                _buildOptionRow(
                  'Your Answer:',
                  result.options[result.userIndex],
                  isCorrect ? Colors.green.shade700 : Colors.red.shade700,
                  isCorrect ? Colors.green.shade50 : Colors.red.shade50,
                ),
                if (!isCorrect) ...[
                  const SizedBox(height: 8),
                  _buildOptionRow(
                    'Correct Answer:',
                    result.options[result.correctIndex],
                    Colors.green.shade700,
                    Colors.green.shade50,
                  ),
                ],
              ],
            ),
          );
        }),
      ],
    );
  }

  Widget _buildOptionRow(String label, String text, Color textColor, Color bgColor) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: textColor.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: GoogleFonts.comicNeue(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: textColor.withValues(alpha: 0.8),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            text,
            style: GoogleFonts.comicNeue(
              fontSize: 15,
              fontWeight: FontWeight.w600,
              color: textColor,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPaperSection({
    required String title,
    required IconData icon,
    required Color color,
    required Widget content,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFFFDFBF7),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.brown.shade200, width: 1.5),
        boxShadow: const [
          BoxShadow(
            color: Colors.black12,
            offset: Offset(3, 3),
            blurRadius: 3,
          ),
        ],
      ),
      padding: const EdgeInsets.all(20.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 28),
              const SizedBox(width: 8),
              Text(
                title,
                style: GoogleFonts.caveat(
                  fontSize: 26,
                  fontWeight: FontWeight.bold,
                  color: color,
                ),
              ),
            ],
          ),
          const Divider(height: 24, thickness: 1.5),
          content,
        ],
      ),
    );
  }
}

class _ScorePainter extends CustomPainter {
  final double score;
  final Color color;
  final Color backgroundColor;

  _ScorePainter({
    required this.score,
    required this.color,
    required this.backgroundColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = min(size.width / 2, size.height / 2) - 10;
    
    // Draw thick background circle
    final bgPaint = Paint()
      ..color = backgroundColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 16
      ..strokeCap = StrokeCap.round;
      
    canvas.drawCircle(center, radius, bgPaint);
    
    // Draw 3D shadow for progress
    final shadowPaint = Paint()
      ..color = Colors.black26
      ..style = PaintingStyle.stroke
      ..strokeWidth = 16
      ..strokeCap = StrokeCap.round;
      
    final sweepAngle = 2 * pi * score;
    canvas.drawArc(
      Rect.fromCircle(center: center.translate(2, 2), radius: radius),
      -pi / 2,
      sweepAngle,
      false,
      shadowPaint,
    );
    
    // Draw progress arc with vibrant color
    final progressPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 16
      ..strokeCap = StrokeCap.round;
      
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -pi / 2,
      sweepAngle,
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _ScorePainter oldDelegate) {
    return oldDelegate.score != score || oldDelegate.color != color;
  }
}
