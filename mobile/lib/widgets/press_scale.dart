/// Press-scale feedback wrapper.
///
/// Wraps any tappable widget to provide a subtle scale-down effect
/// on press, springing back on release. Gives cards and interactive
/// elements a tactile, premium feel.
///
/// Respects [MediaQuery.disableAnimations] — disables scale when true.
library;

import 'package:flutter/material.dart';

class PressScale extends StatefulWidget {
  final Widget child;
  final double scaleDown;
  final Duration duration;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;

  const PressScale({
    super.key,
    required this.child,
    this.scaleDown = 0.96,
    this.duration = const Duration(milliseconds: 150),
    this.onTap,
    this.onLongPress,
  });

  @override
  State<PressScale> createState() => _PressScaleState();
}

class _PressScaleState extends State<PressScale>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _scale;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      vsync: this,
      duration: widget.duration,
    );

    _scale = Tween<double>(
      begin: 1.0,
      end: widget.scaleDown,
    ).animate(CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOut,
    ));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onTapDown(TapDownDetails _) => _controller.forward();

  void _onTapUp(TapUpDetails _) {
    _controller.reverse();
    widget.onTap?.call();
  }

  void _onTapCancel() => _controller.reverse();

  @override
  Widget build(BuildContext context) {
    // Respect reduced-motion preference
    final disableAnimations = MediaQuery.of(context).disableAnimations;

    return GestureDetector(
      onTapDown: disableAnimations ? null : _onTapDown,
      onTapUp: disableAnimations ? null : _onTapUp,
      onTapCancel: disableAnimations ? null : _onTapCancel,
      onTap: disableAnimations ? widget.onTap : null,
      onLongPress: widget.onLongPress,
      child: disableAnimations
          ? widget.child
          : ScaleTransition(
              scale: _scale,
              child: widget.child,
            ),
    );
  }
}
