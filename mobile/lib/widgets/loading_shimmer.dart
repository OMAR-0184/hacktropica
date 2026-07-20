/// Shimmer loading placeholder widget.
library;

import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';

import '../config/theme.dart';

class LoadingShimmer extends StatelessWidget {
  final double height;
  final double width;
  final double borderRadius;

  const LoadingShimmer({
    super.key,
    this.height = 16,
    this.width = double.infinity,
    this.borderRadius = 8,
  });

  @override
  Widget build(BuildContext context) {
    final box = Container(
      height: height,
      width: width,
      decoration: BoxDecoration(
        color: AppColors.surface2,
        borderRadius: BorderRadius.circular(borderRadius),
      ),
    );

    // Respect reduced-motion preference
    if (MediaQuery.of(context).disableAnimations) {
      return box;
    }

    return Shimmer.fromColors(
      baseColor: AppColors.surface2,
      highlightColor: AppColors.border,
      child: box,
    );
  }

  /// A multi-line skeleton mimicking a lesson layout.
  static Widget lessonSkeleton() {
    return const Padding(
      padding: EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          LoadingShimmer(height: 28, width: 200),
          SizedBox(height: 20),
          LoadingShimmer(height: 14),
          SizedBox(height: 10),
          LoadingShimmer(height: 14),
          SizedBox(height: 10),
          LoadingShimmer(height: 14, width: 280),
          SizedBox(height: 24),
          LoadingShimmer(height: 14),
          SizedBox(height: 10),
          LoadingShimmer(height: 14),
          SizedBox(height: 10),
          LoadingShimmer(height: 14, width: 320),
          SizedBox(height: 24),
          LoadingShimmer(height: 80),
        ],
      ),
    );
  }
}
