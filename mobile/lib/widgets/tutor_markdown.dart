/// Tutor markdown renderer with dark theme styling.
library;

import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config/theme.dart';

class TutorMarkdown extends StatelessWidget {
  final String data;

  const TutorMarkdown({super.key, required this.data});

  @override
  Widget build(BuildContext context) {
    return MarkdownBody(
      data: data,
      selectable: true,
      onTapLink: (text, href, title) {
        if (href != null) {
          launchUrl(Uri.parse(href), mode: LaunchMode.externalApplication);
        }
      },
      styleSheet: MarkdownStyleSheet(
        p: const TextStyle(
          color: AppColors.textPrimary,
          fontSize: 15,
          height: 1.7,
        ),
        h1: const TextStyle(
          color: AppColors.textPrimary,
          fontSize: 24,
          fontWeight: FontWeight.w700,
        ),
        h2: const TextStyle(
          color: AppColors.textPrimary,
          fontSize: 20,
          fontWeight: FontWeight.w600,
        ),
        h3: const TextStyle(
          color: AppColors.textPrimary,
          fontSize: 17,
          fontWeight: FontWeight.w600,
        ),
        code: TextStyle(
          color: AppColors.primary200,
          backgroundColor: AppColors.surface2,
          fontSize: 13,
          fontFamily: 'JetBrains Mono',
        ),
        codeblockDecoration: BoxDecoration(
          color: AppColors.surface2,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppColors.border),
        ),
        codeblockPadding: const EdgeInsets.all(14),
        blockquoteDecoration: BoxDecoration(
          border: Border(
            left: BorderSide(color: AppColors.primary500.withAlpha(150), width: 3),
          ),
        ),
        blockquotePadding: const EdgeInsets.only(left: 14, top: 4, bottom: 4),
        listBullet: const TextStyle(color: AppColors.primary400),
        a: const TextStyle(
          color: AppColors.primary400,
          decoration: TextDecoration.underline,
        ),
        horizontalRuleDecoration: BoxDecoration(
          border: Border(
            top: BorderSide(color: AppColors.border.withAlpha(100)),
          ),
        ),
      ),
    );
  }
}
