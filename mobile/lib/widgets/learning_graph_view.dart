/// Interactive canvas rendering the non-linear node graph.
library;

import 'package:flutter/material.dart';

import '../config/theme.dart';
import '../models/workflow.dart';
import 'press_scale.dart';

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
                  currentNode: widget.workflow.currentNode,
                  nodeWidth: nodeWidth,
                  nodeHeight: nodeHeight,
                  nodeCatalog: widget.workflow.nodeCatalog,
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
                    child: PressScale(
                      onTap: () => widget.onNodeTapped(node),
                      child: _GraphNodeCard(
                        node: node,
                        isActive: widget.workflow.currentNode == node.nodeId,
                      ),
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
  final String currentNode;
  final double nodeWidth;
  final double nodeHeight;
  final List<NodeHierarchyMeta> nodeCatalog;

  _GraphEdgesPainter({
    required this.nodePositions,
    required this.childrenMap,
    required this.currentNode,
    required this.nodeWidth,
    required this.nodeHeight,
    required this.nodeCatalog,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Build a status lookup for edge dimming
    final statusMap = <String, String>{};
    for (final node in nodeCatalog) {
      statusMap[node.nodeId] = (node.status ?? 'locked').toUpperCase();
    }

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

        // Determine edge style based on node status
        final isActiveEdge = parentId == currentNode || childId == currentNode;
        final parentStatus = statusMap[parentId] ?? 'LOCKED';
        final childStatus = statusMap[childId] ?? 'LOCKED';
        final isLockedEdge = parentStatus == 'LOCKED' || childStatus == 'LOCKED';

        int alpha;
        double strokeWidth;
        if (isActiveEdge) {
          alpha = 180;
          strokeWidth = 3;
        } else if (isLockedEdge) {
          alpha = 30;
          strokeWidth = 2;
        } else {
          alpha = 80;
          strokeWidth = 3;
        }

        final paint = Paint()
          ..color = AppColors.primary500.withAlpha(alpha)
          ..strokeWidth = strokeWidth
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round;

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
      old.nodePositions != nodePositions ||
      old.childrenMap != childrenMap ||
      old.currentNode != currentNode;
}

/// Graph node card with pulsing glow for the active node.
class _GraphNodeCard extends StatefulWidget {
  final NodeHierarchyMeta node;
  final bool isActive;

  const _GraphNodeCard({
    required this.node,
    required this.isActive,
  });

  @override
  State<_GraphNodeCard> createState() => _GraphNodeCardState();
}

class _GraphNodeCardState extends State<_GraphNodeCard>
    with SingleTickerProviderStateMixin {
  AnimationController? _pulseCtrl;
  Animation<double>? _pulseAnim;

  @override
  void initState() {
    super.initState();
    _setupPulse();
  }

  @override
  void didUpdateWidget(covariant _GraphNodeCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.isActive != widget.isActive) {
      _setupPulse();
    }
  }

  void _setupPulse() {
    if (widget.isActive) {
      _pulseCtrl ??= AnimationController(
        vsync: this,
        duration: const Duration(seconds: 2),
      );
      _pulseAnim = Tween<double>(begin: 15.0, end: 28.0).animate(
        CurvedAnimation(parent: _pulseCtrl!, curve: Curves.easeInOut),
      );
      _pulseCtrl!.repeat(reverse: true);
    } else {
      _pulseCtrl?.dispose();
      _pulseCtrl = null;
      _pulseAnim = null;
    }
  }

  @override
  void dispose() {
    _pulseCtrl?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final status = (widget.node.status ?? 'locked').toUpperCase();
    final isCompleted = status == 'COMPLETED';
    final isAvailable = status == 'AVAILABLE';
    final isRemediation = status == 'REMEDIATION';
    final reduceMotion = MediaQuery.of(context).disableAnimations;

    Color borderColor = AppColors.border;
    Color badgeColor = AppColors.surface2;
    Color badgeTextColor = AppColors.textMuted;
    
    if (widget.isActive) {
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

    Widget card = Container(
      decoration: BoxDecoration(
        color: widget.isActive
            ? AppColors.primary500.withAlpha(15)
            : AppColors.surface.withAlpha(200),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: borderColor, width: widget.isActive ? 2 : 1),
        boxShadow: widget.isActive && (reduceMotion || _pulseAnim == null)
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
                (widget.node.nodeKind ?? 'CONCEPT').toUpperCase(),
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
              widget.node.nodeId.replaceAll('_', ' '),
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
          if (widget.node.score != null && isCompleted) ...[
            const Text('Mastery',
                style: TextStyle(fontSize: 11, color: AppColors.textMuted)),
            const SizedBox(height: 4),
            LinearProgressIndicator(
              value: widget.node.score,
              backgroundColor: AppColors.surface2,
              color: AppColors.success,
              minHeight: 4,
            ),
          ] else if (isAvailable || widget.isActive || isRemediation) ...[
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
    );

    // Wrap active node in pulsing glow animation
    if (widget.isActive && !reduceMotion && _pulseAnim != null) {
      return AnimatedBuilder(
        animation: _pulseAnim!,
        builder: (context, child) => Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: AppColors.primary500.withAlpha(40),
                blurRadius: _pulseAnim!.value,
              ),
            ],
          ),
          child: child,
        ),
        child: card,
      );
    }

    return card;
  }
}
