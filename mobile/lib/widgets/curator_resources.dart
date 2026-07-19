/// Horizontal scrollable curator resource cards (articles, videos, courses).
library;

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config/theme.dart';
import '../models/lesson.dart';

class CuratorResources extends StatelessWidget {
  final CuratorContent content;

  const CuratorResources({super.key, required this.content});

  @override
  Widget build(BuildContext context) {
    if (content.isEmpty) return const SizedBox.shrink();

    final allResources = <_TaggedResource>[
      ...content.articles.map((r) => _TaggedResource(r, 'Article')),
      ...content.videos.map((r) => _TaggedResource(r, 'Video')),
      ...content.courses.map((r) => _TaggedResource(r, 'Course')),
    ];

    if (allResources.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.only(left: 4, bottom: 10),
          child: Row(
            children: [
              Icon(Icons.auto_awesome, size: 16, color: AppColors.accent400),
              SizedBox(width: 8),
              Text(
                'Curated Resources',
                style: TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
        ),
        SizedBox(
          height: 100,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: allResources.length,
            separatorBuilder: (_, __) => const SizedBox(width: 10),
            itemBuilder: (context, index) {
              final tagged = allResources[index];
              return _ResourceCard(
                resource: tagged.resource,
                tag: tagged.tag,
              );
            },
          ),
        ),
      ],
    );
  }
}

class _TaggedResource {
  final CuratorResource resource;
  final String tag;
  _TaggedResource(this.resource, this.tag);
}

class _ResourceCard extends StatelessWidget {
  final CuratorResource resource;
  final String tag;

  const _ResourceCard({required this.resource, required this.tag});

  IconData get _icon => switch (tag) {
        'Video' => Icons.play_circle_outline,
        'Course' => Icons.school_outlined,
        _ => Icons.article_outlined,
      };

  Color get _tagColor => switch (tag) {
        'Video' => AppColors.error,
        'Course' => AppColors.accent400,
        _ => AppColors.primary400,
      };

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        if (resource.url.isNotEmpty) {
          launchUrl(Uri.parse(resource.url),
              mode: LaunchMode.externalApplication);
        }
      },
      child: Container(
        width: 220,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.surface2,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(_icon, size: 14, color: _tagColor),
                const SizedBox(width: 6),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: _tagColor.withAlpha(25),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    tag,
                    style: TextStyle(
                        color: _tagColor,
                        fontSize: 10,
                        fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Expanded(
              child: Text(
                resource.title,
                style: const TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (resource.description != null &&
                resource.description!.isNotEmpty)
              Text(
                resource.description!,
                style:
                    const TextStyle(color: AppColors.textMuted, fontSize: 11),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
          ],
        ),
      ),
    );
  }
}
