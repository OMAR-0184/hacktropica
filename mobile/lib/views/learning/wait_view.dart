/// Loading state for the learning engine.
library;

import 'package:flutter/material.dart';

import '../../config/theme.dart';

class WaitView extends StatelessWidget {
  final String? reasoning;

  const WaitView({super.key, this.reasoning});

  @override
  Widget build(BuildContext context) {
    if (reasoning == null || reasoning!.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
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
          const Padding(
            padding: EdgeInsets.only(top: 2),
            child: SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                  strokeWidth: 2, color: AppColors.primary400),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Text(
              reasoning!,
              style: const TextStyle(
                color: AppColors.primary100,
                fontSize: 13,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
