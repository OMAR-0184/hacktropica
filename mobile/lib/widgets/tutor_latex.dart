import 'package:flutter/material.dart';
import 'package:flutter_tex/flutter_tex.dart';
import '../config/theme.dart';

class TutorLatex extends StatelessWidget {
  final String latexSource;

  const TutorLatex({super.key, required this.latexSource});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.primary500.withAlpha(50)),
      ),
      padding: const EdgeInsets.all(16),
      child: TeXView(
        loadingWidgetBuilder: (context) => const Center(
          child: CircularProgressIndicator(),
        ),
        child: TeXViewDocument(
          latexSource,
          style: const TeXViewStyle(
            backgroundColor: Colors.transparent,
          ),
        ),
      ),
    );
  }
}
