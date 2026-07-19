/// Interactive canvas rendering the non-linear node graph.
library;

import 'package:flutter/material.dart';

import '../config/theme.dart';
import '../models/workflow.dart';

class LearningGraphView extends StatefulWidget {
  final WorkflowSnapshot workflow;
  final ValueChanged<NodeHierarchyMeta> onNodeTapped;

  const LearningGraphView({
    super.key,
    required this.workflow,
    required this.onNodeTapped,
  });

  @override
  State<LearningGraphView> createState() => _LearningGraphViewState();
}

class _LearningGraphViewState extends State<LearningGraphView> {
  final double nodeWidth = 260.0;
  final double nodeHeight = 160.0;
  final double colSpacing = 100.0;
  final double rowSpacing = 40.0;

  Map<String, Offset> _nodePositions = {};
  Size _graphSize = Size.zero;

  @override
  void initState() {
    super.initState();
    _computeLayout();
  }

  @override
  void didUpdateWidget(covariant LearningGraphView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.workflow.nodeCatalog.length !=
            widget.workflow.nodeCatalog.length ||
        oldWidget.workflow.status != widget.workflow.status) {
      _computeLayout();
    }
  }

  void _computeLayout() {
    final nodes = widget.workflow.nodeCatalog;
    final Map<int, List<NodeHierarchyMeta>> nodesByDepth = {};
    int maxDepth = 0;

    // Group by depth
    for (final node in nodes) {
      final depth = node.depth ?? 0;
      if (depth > maxDepth) maxDepth = depth;
      nodesByDepth.putIfAbsent(depth, () => []).add(node);
    }

    final newPositions = <String, Offset>{};
    double maxColHeight = 0;

    for (int d = 0; d <= maxDepth; d++) {
      final colNodes = nodesByDepth[d] ?? [];
      // Offset the entire graph by 360px horizontally to avoid overlapping the StatusPanel on the left
      final x = 360.0 + (d * (nodeWidth + colSpacing));
      final colHeight = colNodes.length * nodeHeight +
          (colNodes.length - 1) * rowSpacing;
      if (colHeight > maxColHeight) maxColHeight = colHeight;

      double y = 40.0;
      for (final node in colNodes) {
        newPositions[node.nodeId] = Offset(x, y);
        y += nodeHeight + rowSpacing;
      }
    }

    setState(() {
      _nodePositions = newPositions;
      _graphSize = Size(
        360.0 + maxDepth * (nodeWidth + colSpacing) + nodeWidth + 80.0,
        maxColHeight + 80.0,
      );
    });
  }

  void _handleNodePan(String nodeId, DragUpdateDetails details) {
    if (_nodePositions.containsKey(nodeId)) {
      setState(() {
        _nodePositions[nodeId] = _nodePositions[nodeId]! + details.delta;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return InteractiveViewer(
      boundaryMargin: const EdgeInsets.all(800),
      minScale: 0.1,
      maxScale: 2.0,
      constrained: false,
      child: SizedBox(
        width: _graphSize.width < MediaQuery.of(context).size.width
            ? MediaQuery.of(context).size.width
            : _graphSize.width,
        height: _graphSize.height < MediaQuery.of(context).size.height
            ? MediaQuery.of(context).size.height
            : _graphSize.height,
        child: Stack(
          clipBehavior: Clip.none,
          children: [
            // Draw Edges
            Positioned.fill(
              child: CustomPaint(
                painter: _GraphEdgesPainter(
                  nodePositions: _nodePositions,
                  childrenMap: widget.workflow.childrenMap,
                  nodeWidth: nodeWidth,
                  nodeHeight: nodeHeight,
                ),
              ),
            ),
            // Draw Nodes
            for (final node in widget.workflow.nodeCatalog)
              if (_nodePositions.containsKey(node.nodeId))
                Positioned(
                  left: _nodePositions[node.nodeId]!.dx,
                  top: _nodePositions[node.nodeId]!.dy,
                  width: nodeWidth,
                  height: nodeHeight,
                  child: GestureDetector(
                    onPanUpdate: (details) => _handleNodePan(node.nodeId, details),
                    child: _GraphNodeCard(
                      node: node,
                      isActive: widget.workflow.currentNode == node.nodeId,
                      onTap: () => widget.onNodeTapped(node),
                    ),
                  ),
                ),
          ],
        ),
      ),
    );
  }
}

class _GraphEdgesPainter extends CustomPainter {
  final Map<String, Offset> nodePositions;
  final Map<String, List<String>> childrenMap;
  final double nodeWidth;
  final double nodeHeight;

  _GraphEdgesPainter({
    required this.nodePositions,
    required this.childrenMap,
    required this.nodeWidth,
    required this.nodeHeight,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.primary500.withAlpha(80)
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    for (final entry in childrenMap.entries) {
      final parentId = entry.key;
      if (!nodePositions.containsKey(parentId)) continue;

      final pOffset = nodePositions[parentId]!;
      // Connection comes from the right center of the parent
      final pPt = Offset(pOffset.dx + nodeWidth, pOffset.dy + nodeHeight / 2);

      for (final childId in entry.value) {
        if (!nodePositions.containsKey(childId)) continue;
        final cOffset = nodePositions[childId]!;
        // Connection goes to the left center of the child
        final cPt = Offset(cOffset.dx, cOffset.dy + nodeHeight / 2);

        // Draw bezier curve
        final path = Path();
        path.moveTo(pPt.dx, pPt.dy);
        final controlPoint1 = Offset(pPt.dx + 40, pPt.dy);
        final controlPoint2 = Offset(cPt.dx - 40, cPt.dy);
        path.cubicTo(
            controlPoint1.dx, controlPoint1.dy, controlPoint2.dx, controlPoint2.dy, cPt.dx, cPt.dy);

        canvas.drawPath(path, paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _GraphEdgesPainter old) =>
      old.nodePositions != nodePositions || old.childrenMap != childrenMap;
}

class _GraphNodeCard extends StatelessWidget {
  final NodeHierarchyMeta node;
  final bool isActive;
  final VoidCallback onTap;

  const _GraphNodeCard({
    required this.node,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final status = (node.status ?? 'locked').toUpperCase();
    final isCompleted = status == 'COMPLETED';
    final isAvailable = status == 'AVAILABLE';
    final isRemediation = status == 'REMEDIATION';

    Color borderColor = AppColors.border;
    Color badgeColor = AppColors.surface2;
    Color badgeTextColor = AppColors.textMuted;
    
    if (isActive) {
      borderColor = AppColors.primary400;
      badgeColor = AppColors.primary400.withAlpha(30);
      badgeTextColor = AppColors.primary400;
    } else if (isCompleted) {
      borderColor = AppColors.success.withAlpha(100);
      badgeColor = AppColors.success.withAlpha(20);
      badgeTextColor = AppColors.success;
    } else if (isRemediation) {
      borderColor = AppColors.warning.withAlpha(150);
      badgeColor = AppColors.warning.withAlpha(30);
      badgeTextColor = AppColors.warning;
    } else if (isAvailable) {
      borderColor = AppColors.textMuted.withAlpha(100);
      badgeColor = AppColors.surface2;
      badgeTextColor = AppColors.textPrimary;
    }

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: isActive
              ? AppColors.primary500.withAlpha(15)
              : AppColors.surface.withAlpha(200),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: borderColor, width: isActive ? 2 : 1),
          boxShadow: isActive
              ? [
                  BoxShadow(
                    color: AppColors.primary500.withAlpha(40),
                    blurRadius: 20,
                  )
                ]
              : null,
        ),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header Row (Kind + Status Badge)
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  (node.nodeKind ?? 'CONCEPT').toUpperCase(),
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: AppColors.primary400,
                    letterSpacing: 1.2,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: badgeColor,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: badgeTextColor.withAlpha(50)),
                  ),
                  child: Text(
                    status,
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: badgeTextColor,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            // Title
            Expanded(
              child: Text(
                node.nodeId.replaceAll('_', ' '),
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                  height: 1.3,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            const SizedBox(height: 8),
            // Progress or Helper text
            if (node.score != null && isCompleted) ...[
              const Text('Mastery',
                  style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
              const SizedBox(height: 4),
              LinearProgressIndicator(
                value: node.score,
                backgroundColor: AppColors.surface2,
                color: AppColors.success,
                minHeight: 4,
              ),
            ] else if (isAvailable || isActive || isRemediation) ...[
              const Text('Open this node to review objective, explanation, and practice.',
                  style: TextStyle(fontSize: 10, color: AppColors.textMuted),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis),
            ] else ...[
              const Text('Unlocks when available.',
                  style: TextStyle(fontSize: 10, color: AppColors.textDisabled)),
            ],
          ],
        ),
      ),
    );
  }
}
