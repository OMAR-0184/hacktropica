/// Staggered fade + slide-up animation wrapper.
///
/// Wrap list items in this widget to animate them with a cascading
/// entrance effect. Each item fades in and slides up with a delay
/// proportional to its [index].
///
/// Respects [MediaQuery.disableAnimations] — renders instantly when true.
library;

import 'package:flutter/material.dart';

class StaggeredFadeSlide extends StatefulWidget {
  final int index;
  final Duration staggerDelay;
  final Duration duration;
  final double slideOffset;
  final Widget child;

  const StaggeredFadeSlide({
    super.key,
    required this.index,
    this.staggerDelay = const Duration(milliseconds: 50),
    this.duration = const Duration(milliseconds: 400),
    this.slideOffset = 24.0,
    required this.child,
  });

  @override
  State<StaggeredFadeSlide> createState() => _StaggeredFadeSlideState();
}

class _StaggeredFadeSlideState extends State<StaggeredFadeSlide>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _opacity;
  late final Animation<Offset> _slide;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      vsync: this,
      duration: widget.duration,
    );

    final curve = CurvedAnimation(
      parent: _controller,
      curve: Curves.elasticOut, // Bouncy pop effect
    );

    _opacity = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeIn), // Smooth fade
    );
    _slide = Tween<Offset>(
      begin: Offset(0, widget.slideOffset),
      end: Offset.zero,
    ).animate(curve);

    // Schedule the staggered start after build
    final delay = widget.staggerDelay * widget.index;
    Future.delayed(delay, () {
      if (mounted) _controller.forward();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Respect reduced-motion preference
    if (MediaQuery.of(context).disableAnimations) {
      return widget.child;
    }

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        // Compute the 3D rotation based on the animation value
        // At 0 (start), it's rotated. At 1 (end), it's flat.
        final double progress = _controller.value;
        final double angleX = (1.0 - progress) * 0.8; // More pronounced tilt back
        final double angleY = (1.0 - progress) * 0.4 * (widget.index % 2 == 0 ? 1 : -1); // Stronger alternating tilt
        final double scale = 0.7 + (0.3 * progress); // Starts smaller to pop more

        final transform = Matrix4.identity()
          ..setEntry(3, 2, 0.003) // Stronger perspective
          ..rotateX(angleX)
          ..rotateY(angleY)
          ..scale(scale);

        return Opacity(
          opacity: _opacity.value,
          child: Transform.translate(
            offset: _slide.value,
            child: Transform(
              alignment: FractionalOffset.center,
              transform: transform,
              child: child,
            ),
          ),
        );
      },
      child: widget.child,
    );
  }
}
