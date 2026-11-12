import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/colors.dart';

/// Sprout, Hatua's mascot: a round seedling with two leaves, plum feet and blush cheeks.
/// Drawn in code (no image files), so it is sharp at any size and follows the theme.
enum SproutPose {
  /// Welcome screens, splash, add phone number.
  waving,

  /// Beside the milestone question.
  thinking,

  /// Results when on track, end of the welcome flow.
  cheering,

  /// Results when Watch or Check soon. Holds a small heart; never cheers on a concern.
  gentle,

  /// Empty states.
  resting,
}

class Sprout extends StatefulWidget {
  const Sprout({super.key, this.pose = SproutPose.waving, this.size = 120, this.bob = true});

  final SproutPose pose;
  final double size;

  /// A slow up-and-down float. Off for small inline uses.
  final bool bob;

  @override
  State<Sprout> createState() => _SproutState();
}

class _SproutState extends State<Sprout> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 2400));

  @override
  void initState() {
    super.initState();
    if (widget.bob) _c.repeat(reverse: true);
  }

  @override
  void didUpdateWidget(Sprout old) {
    super.didUpdateWidget(old);
    if (widget.bob && !_c.isAnimating) _c.repeat(reverse: true);
    if (!widget.bob) _c.stop();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  static const _labels = {
    SproutPose.waving: 'Sprout waving',
    SproutPose.thinking: 'Sprout thinking',
    SproutPose.cheering: 'Sprout cheering',
    SproutPose.gentle: 'Sprout holding a heart',
    SproutPose.resting: 'Sprout resting',
  };

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final painter = _SproutPainter(widget.pose, context.hc, dark);
    // Respect "remove animations" in the phone's accessibility settings.
    final reduceMotion = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    return Semantics(
      image: true,
      label: _labels[widget.pose],
      child: SizedBox.square(
        dimension: widget.size,
        child: widget.bob && !reduceMotion
            ? AnimatedBuilder(
                animation: _c,
                builder: (_, child) => Transform.translate(
                  offset: Offset(0, -widget.size * 0.03 * Curves.easeInOut.transform(_c.value)),
                  child: child,
                ),
                child: CustomPaint(painter: painter),
              )
            : CustomPaint(painter: painter),
      ),
    );
  }
}

class _SproutPainter extends CustomPainter {
  _SproutPainter(this.pose, this.c, this.dark);

  final SproutPose pose;
  final HatuaPalette c;
  final bool dark;

  static const _ink = Color(0xFF3A1F36);
  static const _blush = Color(0xFFF8AFA8);

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width / 100;
    canvas.save();
    canvas.scale(s);

    final feet = Paint()..color = dark ? const Color(0xFFA86C9C) : const Color(0xFF7B3F70);
    final body = Paint()..color = c.sprout;
    final leaf = Paint()..color = c.leaf;
    final stem = Paint()
      ..color = c.leaf
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.6
      ..strokeCap = StrokeCap.round;
    final ink = Paint()..color = _ink;
    final line = Paint()
      ..color = _ink
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.4
      ..strokeCap = StrokeCap.round;

    // Pose geometry.
    final hop = pose == SproutPose.cheering ? -6.0 : 0.0;
    final squash = pose == SproutPose.resting ? 0.92 : 1.0;
    final tilt = switch (pose) {
      SproutPose.waving => -0.07,
      SproutPose.thinking => 0.05,
      _ => 0.0,
    };

    // Feet first, behind the body.
    if (pose == SproutPose.cheering) {
      canvas.drawOval(Rect.fromCenter(center: const Offset(36, 90), width: 17, height: 8), feet);
      canvas.drawOval(Rect.fromCenter(center: const Offset(64, 90), width: 17, height: 8), feet);
    } else if (pose == SproutPose.resting) {
      canvas.drawOval(Rect.fromCenter(center: const Offset(38, 91), width: 18, height: 7), feet);
      canvas.drawOval(Rect.fromCenter(center: const Offset(62, 91), width: 18, height: 7), feet);
    } else {
      canvas.drawOval(Rect.fromCenter(center: const Offset(40, 91), width: 18, height: 8), feet);
      canvas.drawOval(Rect.fromCenter(center: const Offset(61, 89), width: 18, height: 8), feet);
    }

    canvas.save();
    canvas.translate(50, 60 + hop);
    canvas.rotate(tilt);
    canvas.scale(1, squash);
    canvas.translate(-50, -60);

    // Stem and leaves.
    canvas.drawLine(const Offset(50, 31), const Offset(50, 19), stem);
    _leaves(canvas, leaf);

    // Body.
    canvas.drawCircle(const Offset(50, 60), 30, body);

    // Cheeks.
    final cheek = Paint()..color = _blush;
    canvas.drawOval(Rect.fromCenter(center: const Offset(33, 66), width: 10, height: 6), cheek);
    canvas.drawOval(Rect.fromCenter(center: const Offset(67, 66), width: 10, height: 6), cheek);

    _face(canvas, ink, line);
    canvas.restore();

    _extras(canvas, s);
    canvas.restore();
  }

  void _leaves(Canvas canvas, Paint leaf) {
    Path leafPath(Offset base, Offset tip, double bulge) {
      final mid = Offset((base.dx + tip.dx) / 2, (base.dy + tip.dy) / 2);
      final d = tip - base;
      final n = Offset(-d.dy, d.dx) / d.distance * bulge;
      return Path()
        ..moveTo(base.dx, base.dy)
        ..quadraticBezierTo(mid.dx + n.dx, mid.dy + n.dy, tip.dx, tip.dy)
        ..quadraticBezierTo(mid.dx - n.dx, mid.dy - n.dy, base.dx, base.dy)
        ..close();
    }

    const base = Offset(50, 20);
    switch (pose) {
      case SproutPose.waving:
        canvas.drawPath(leafPath(base, const Offset(35, 14), 6), leaf);
        canvas.drawPath(leafPath(base, const Offset(66, 4), 6.5), leaf); // raised, waving
      case SproutPose.thinking:
        canvas.drawPath(leafPath(base, const Offset(66, 13), 6), leaf);
        // Curled leaf, like a question mark.
        final curl = Paint()
          ..color = leaf.color
          ..style = PaintingStyle.stroke
          ..strokeWidth = 5
          ..strokeCap = StrokeCap.round;
        canvas.drawPath(
            Path()
              ..moveTo(50, 20)
              ..quadraticBezierTo(38, 22, 37, 13)
              ..quadraticBezierTo(37, 6, 44, 7),
            curl);
      case SproutPose.cheering:
        canvas.drawPath(leafPath(base, const Offset(33, 5), 6.5), leaf);
        canvas.drawPath(leafPath(base, const Offset(67, 5), 6.5), leaf);
      case SproutPose.gentle:
        canvas.drawPath(leafPath(base, const Offset(34, 22), 5.5), leaf); // lowered
        canvas.drawPath(leafPath(base, const Offset(66, 22), 5.5), leaf);
      case SproutPose.resting:
        canvas.drawPath(leafPath(base, const Offset(36, 18), 5.5), leaf);
        canvas.drawPath(leafPath(base, const Offset(64, 16), 5.5), leaf);
    }
  }

  void _face(Canvas canvas, Paint ink, Paint line) {
    final white = Paint()..color = const Color(0xFFFFFFFF);
    void eye(double x, double y, {double dx = 0, double dy = 0}) {
      canvas.drawCircle(Offset(x, y), 4.2, ink);
      canvas.drawCircle(Offset(x + 1.4 + dx, y - 1.4 + dy), 1.4, white);
    }

    switch (pose) {
      case SproutPose.cheering:
        // Happy closed eyes (^ ^) and a wide open smile.
        canvas.drawPath(
            Path()
              ..moveTo(36, 57)
              ..quadraticBezierTo(40, 51, 44, 57),
            line);
        canvas.drawPath(
            Path()
              ..moveTo(56, 57)
              ..quadraticBezierTo(60, 51, 64, 57),
            line);
        canvas.drawPath(
            Path()
              ..moveTo(42, 66)
              ..quadraticBezierTo(50, 77, 58, 66)
              ..close(),
            ink);
      case SproutPose.resting:
        canvas.drawPath(
            Path()
              ..moveTo(36, 56)
              ..quadraticBezierTo(40, 60, 44, 56),
            line);
        canvas.drawPath(
            Path()
              ..moveTo(56, 56)
              ..quadraticBezierTo(60, 60, 64, 56),
            line);
        canvas.drawPath(
            Path()
              ..moveTo(46, 68)
              ..quadraticBezierTo(50, 71, 54, 68),
            line);
      case SproutPose.thinking:
        eye(40, 56, dx: 0.6, dy: -0.8);
        eye(60, 56, dx: 0.6, dy: -0.8);
        canvas.drawCircle(const Offset(52, 69), 2.6, ink); // small "o"
      case SproutPose.gentle:
        eye(40, 56);
        eye(60, 56);
        canvas.drawPath(
            Path()
              ..moveTo(45, 67)
              ..quadraticBezierTo(50, 70, 55, 67),
            line);
      case SproutPose.waving:
        eye(40, 56);
        eye(60, 56);
        canvas.drawPath(
            Path()
              ..moveTo(43, 66)
              ..quadraticBezierTo(50, 73, 57, 66),
            line);
    }
  }

  /// Sparkles, thought dots, a heart, or sleep lines, outside the body.
  void _extras(Canvas canvas, double s) {
    switch (pose) {
      case SproutPose.cheering:
        final star = Paint()..color = c.sun500;
        for (final p in const [Offset(14, 30), Offset(86, 26), Offset(90, 56), Offset(10, 60)]) {
          canvas.drawPath(_sparkle(p, 5), star);
        }
      case SproutPose.thinking:
        final dot = Paint()..color = c.plum500;
        canvas.drawCircle(const Offset(80, 30), 2.2, dot);
        canvas.drawCircle(const Offset(86, 22), 3, dot);
        canvas.drawCircle(const Offset(93, 12), 3.8, dot);
      case SproutPose.gentle:
        final heart = Paint()..color = const Color(0xFFEA8A86);
        canvas.drawPath(_heart(const Offset(50, 84), 11), heart);
      case SproutPose.resting:
        final z = Paint()
          ..color = c.plum500
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2.2
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round;
        canvas.drawPath(_z(const Offset(78, 28), 7), z);
        canvas.drawPath(_z(const Offset(88, 16), 5), z);
      case SproutPose.waving:
        final wave = Paint()
          ..color = c.plum500
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2
          ..strokeCap = StrokeCap.round;
        canvas.drawArc(Rect.fromCircle(center: const Offset(66, 6), radius: 13), -0.9, 0.9,
            false, wave);
        canvas.drawArc(Rect.fromCircle(center: const Offset(66, 6), radius: 18), -0.85, 0.8,
            false, wave);
    }
  }

  Path _sparkle(Offset c, double r) {
    final p = Path();
    for (var i = 0; i < 8; i++) {
      final a = i * math.pi / 4 - math.pi / 2;
      final rr = i.isEven ? r : r * 0.35;
      final pt = c + Offset(math.cos(a) * rr, math.sin(a) * rr);
      i == 0 ? p.moveTo(pt.dx, pt.dy) : p.lineTo(pt.dx, pt.dy);
    }
    return p..close();
  }

  Path _heart(Offset c, double w) {
    final h = w * 0.9;
    return Path()
      ..moveTo(c.dx, c.dy + h * 0.45)
      ..cubicTo(c.dx - w, c.dy - h * 0.1, c.dx - w * 0.45, c.dy - h * 0.75, c.dx, c.dy - h * 0.25)
      ..cubicTo(c.dx + w * 0.45, c.dy - h * 0.75, c.dx + w, c.dy - h * 0.1, c.dx, c.dy + h * 0.45)
      ..close();
  }

  Path _z(Offset o, double w) => Path()
    ..moveTo(o.dx, o.dy)
    ..lineTo(o.dx + w, o.dy)
    ..lineTo(o.dx, o.dy + w)
    ..lineTo(o.dx + w, o.dy + w);

  @override
  bool shouldRepaint(_SproutPainter old) => old.pose != pose || old.c != c || old.dark != dark;
}
