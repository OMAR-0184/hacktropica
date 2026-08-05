import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:google_fonts/google_fonts.dart';
import 'dart:math';

class TutorChartPaper extends StatelessWidget {
  final String markdownSource;

  const TutorChartPaper({super.key, required this.markdownSource});

  @override
  Widget build(BuildContext context) {
    // Generate a random rotation between -1.5 and 1.5 degrees for a "stuck to a board" look
    final random = Random(markdownSource.hashCode);

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.symmetric(vertical: 24, horizontal: 12),
      padding: const EdgeInsets.fromLTRB(24, 40, 24, 32),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF9C4), // Light yellow sticky note / chart paper color
        borderRadius: BorderRadius.circular(4),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.15),
            blurRadius: 10,
            offset: const Offset(3, 5),
          ),
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 3,
            offset: const Offset(0, 1),
          ),
        ],
      ),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          // A piece of tape at the top center
          Positioned(
            top: -50,
            left: 0,
            right: 0,
            child: Center(
              child: Transform.rotate(
                angle: (random.nextDouble() * 10 - 5) * pi / 180,
                child: Container(
                  width: 80,
                  height: 25,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(2),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.05),
                        blurRadius: 1,
                        offset: const Offset(0, 1),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          MarkdownBody(
            data: markdownSource,
            styleSheet: MarkdownStyleSheet(
              p: GoogleFonts.comicNeue(
                fontSize: 18,
                color: const Color(0xFF2C3E50),
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
              h1: GoogleFonts.caveat(
                fontSize: 34,
                fontWeight: FontWeight.bold,
                color: const Color(0xFFE74C3C),
              ),
              h2: GoogleFonts.caveat(
                fontSize: 28,
                fontWeight: FontWeight.bold,
                color: const Color(0xFF2980B9),
              ),
              h3: GoogleFonts.caveat(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: const Color(0xFF27AE60),
              ),
              blockquote: GoogleFonts.comicNeue(
                fontSize: 18,
                color: const Color(0xFF8E44AD),
                fontStyle: FontStyle.italic,
                fontWeight: FontWeight.w600,
              ),
              blockquoteDecoration: BoxDecoration(
                color: const Color(0xFFE8DAEF),
                borderRadius: BorderRadius.circular(8),
                border: const Border(
                  left: BorderSide(color: Color(0xFF8E44AD), width: 6),
                ),
              ),
              code: GoogleFonts.firaCode(
                fontSize: 14,
                color: const Color(0xFFD35400),
                backgroundColor: const Color(0xFFFDEBD0),
              ),
              codeblockDecoration: BoxDecoration(
                color: const Color(0xFFFDEBD0),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFD35400)),
              ),
              listBullet: GoogleFonts.comicNeue(
                fontSize: 18,
                color: const Color(0xFF2C3E50),
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
