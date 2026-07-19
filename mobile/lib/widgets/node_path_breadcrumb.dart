/// Breadcrumb trail showing the current path through the learning tree.
library;

import 'package:flutter/material.dart';
import '../config/theme.dart';

class NodePathBreadcrumb extends StatelessWidget {
  final List<String> path;

  const NodePathBreadcrumb({super.key, required this.path});

  @override
  Widget build(BuildContext context) {
    if (path.isEmpty) return const SizedBox.shrink();

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (int i = 0; i < path.length; i++) ...[
            if (i > 0) ...[
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 4),
                child: Icon(
                  Icons.chevron_right,
                  size: 14,
                  color: AppColors.textDisabled,
                ),
              ),
            ],
            Text(
              path[i],
              style: TextStyle(
                color: i == path.length - 1
                    ? AppColors.primary400
                    : AppColors.textMuted,
                fontSize: 12,
                fontWeight:
                    i == path.length - 1 ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
