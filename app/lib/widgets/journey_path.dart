import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../api/models.dart';
import '../theme/colors.dart';
import '../theme/theme.dart';
import 'sprout.dart';

/// The age bands the backend assesses in: CREDI bands under 24 months
/// (hatua_ml/norms/who_motor.py) and ECDI2030 bands from 24 to 59 months
/// (hatua_ml/features/ecdi2030.py).
const ageBands = [
  (0, 5), (6, 11), (12, 17), (18, 23), (24, 29), (30, 35), (36, 41), (42, 47), (48, 59),
];

enum _StoneState { done, missed, current, future }

/// A child's development journey from birth to five: a winding path with one stepping
/// stone per age band. Past checks are ticked stones that open their result, the current
/// band has Sprout beside it, missed bands are dashed, future bands are outlined.
class JourneyPath extends StatelessWidget {
  const JourneyPath({
    super.key,
    required this.ageMonths,
    required this.checks,
    required this.onOpen,
    this.onStart,
  });

  final int ageMonths;

  /// The child's checks, newest first.
  final List<Assessment> checks;
  final void Function(Assessment) onOpen;

  /// Starts a check. Null for viewers who can't start one (CHWs).
  final VoidCallback? onStart;

  static const _stone = 40.0;
  static const _rowH = 76.0;
  static const _currentRowH = 124.0;
  static const _labelX = 168.0;

  @override
  Widget build(BuildContext context) {
    final stones = <_Stone>[];
    for (final (lo, hi) in ageBands) {
      final inBand = checks.where((a) => a.ageMonths >= lo && a.ageMonths <= hi).toList();
      final latest = inBand.isEmpty ? null : inBand.first;
      final _StoneState state;
      if (ageMonths > hi) {
        state = latest != null ? _StoneState.done : _StoneState.missed;
      } else if (ageMonths >= lo) {
        state = latest != null ? _StoneState.done : _StoneState.current;
      } else {
        state = _StoneState.future;
      }
      final isNow = ageMonths >= lo && ageMonths <= hi;
      stones.add(_Stone(lo, hi, state, latest, isNow));
    }

    // Row heights and stone centres along a gentle S-curve.
    final heights = [
      for (final s in stones)
        s.state == _StoneState.current && onStart != null ? _currentRowH : _rowH
    ];
    final centres = <Offset>[];
    var y = 0.0;
    for (var i = 0; i < stones.length; i++) {
      final x = 98 + 30 * math.sin(i * math.pi / 4);
      centres.add(Offset(x, y + _rowH / 2));
      y += heights[i];
    }

    return Semantics(
      label: 'Development journey',
      child: SizedBox(
        height: y,
        child: Stack(clipBehavior: Clip.none, children: [
          Positioned.fill(
            child: CustomPaint(painter: _PathPainter(centres, context.hc.plum200)),
          ),
          for (var i = 0; i < stones.length; i++) ...[
            Positioned(
              left: centres[i].dx - _stone / 2,
              top: centres[i].dy - _stone / 2,
              child: _stoneWidget(context, stones[i]),
            ),
            if (stones[i].isNow)
              Positioned(
                left: math.max(0, centres[i].dx - _stone / 2 - 66),
                top: centres[i].dy - 40,
                child: Sprout(
                    pose: stones[i].state == _StoneState.done
                        ? SproutPose.cheering
                        : SproutPose.waving,
                    size: 64),
              ),
            Positioned(
              left: _labelX,
              right: 0,
              top: centres[i].dy - 22,
              child: _label(context, stones[i]),
            ),
          ],
        ]),
      ),
    );
  }

  Widget _stoneWidget(BuildContext context, _Stone s) {
    final c = context.hc;
    final big = s.isNow;
    final size = big ? _stone + 8 : _stone;
    final Widget body = switch (s.state) {
      _StoneState.done => Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            color: big ? c.sun500 : c.plum700,
            shape: BoxShape.circle,
            border: big ? Border.all(color: c.plum700, width: 3) : null,
          ),
          child: Icon(Icons.check_rounded,
              color: big ? c.onBright : c.onPrimary, size: size * 0.55),
        ),
      _StoneState.current => Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
              color: c.sun500,
              shape: BoxShape.circle,
              border: Border.all(color: c.plum700, width: 3)),
          child: Icon(Icons.directions_walk_rounded, color: c.onBright, size: size * 0.5),
        ),
      _StoneState.missed => CustomPaint(
          size: Size.square(size),
          painter: _DashedCircle(c.muted, c.surfaceCard),
        ),
      _StoneState.future => Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
              color: c.surfaceCard,
              shape: BoxShape.circle,
              border: Border.all(color: c.plum200, width: 3)),
        ),
    };
    final stone = SizedBox(
      width: _stone,
      height: _stone,
      child: OverflowBox(maxWidth: size, maxHeight: size, child: body),
    );
    if (s.state == _StoneState.done) {
      return Semantics(
        button: true,
        label: 'Open the check from ${_band(s)}',
        child: GestureDetector(onTap: () => onOpen(s.latest!), child: stone),
      );
    }
    return stone;
  }

  Widget _label(BuildContext context, _Stone s) {
    final t = Theme.of(context).textTheme;
    final c = context.hc;
    final title = Text(_band(s), style: t.titleMedium);
    final Widget status = switch (s.state) {
      _StoneState.done => _statusDot(context, s.latest!.riskLevel),
      _StoneState.missed => Text('No check', style: t.bodySmall),
      _StoneState.future => Text('Coming up', style: t.bodySmall),
      _StoneState.current => Text('Check due now',
          style: t.bodyMedium?.copyWith(color: c.plum900, fontWeight: FontWeight.w700)),
    };
    final content = Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      title,
      const SizedBox(height: 2),
      status,
      if (s.state == _StoneState.current && onStart != null) ...[
        const SizedBox(height: Space.s2),
        SizedBox(
          width: 160,
          child: FilledButton(onPressed: onStart, child: const Text('Start check')),
        ),
      ],
    ]);
    if (s.state == _StoneState.done) {
      return InkWell(
        borderRadius: BorderRadius.circular(Radii.sm),
        onTap: () => onOpen(s.latest!),
        child: content,
      );
    }
    return content;
  }

  Widget _statusDot(BuildContext context, String level) {
    final c = context.hc;
    final t = Theme.of(context).textTheme;
    final (color, text) = switch (level) {
      'high' => (c.riskHigh, 'Check soon'),
      'medium' => (c.riskMedium, 'Watch'),
      _ => (c.riskLow, 'On track'),
    };
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Container(
          width: 10, height: 10, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
      const SizedBox(width: 6),
      Text(text, style: t.bodySmall?.copyWith(color: c.plum900)),
      const SizedBox(width: 4),
      Icon(Icons.chevron_right_rounded, size: 18, color: c.muted),
    ]);
  }

  static String _band(_Stone s) => s.hi == 59 && s.lo == 48
      ? '4 to 5 years'
      : '${s.lo} to ${s.hi} months';
}

class _Stone {
  _Stone(this.lo, this.hi, this.state, this.latest, this.isNow);
  final int lo;
  final int hi;
  final _StoneState state;
  final Assessment? latest;
  final bool isNow;
}

class _PathPainter extends CustomPainter {
  _PathPainter(this.points, this.color);
  final List<Offset> points;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    if (points.length < 2) return;
    final path = Path()..moveTo(points.first.dx, points.first.dy);
    for (var i = 1; i < points.length; i++) {
      final a = points[i - 1], b = points[i];
      final midY = (a.dy + b.dy) / 2;
      path.cubicTo(a.dx, midY, b.dx, midY, b.dx, b.dy);
    }
    canvas.drawPath(
        path,
        Paint()
          ..color = color
          ..style = PaintingStyle.stroke
          ..strokeWidth = 12
          ..strokeCap = StrokeCap.round);
  }

  @override
  bool shouldRepaint(_PathPainter old) => old.points != points || old.color != color;
}

class _DashedCircle extends CustomPainter {
  _DashedCircle(this.color, this.fill);
  final Color color;
  final Color fill;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.width / 2 - 1.5;
    canvas.drawCircle(c, r, Paint()..color = fill);
    final stroke = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5;
    const dashes = 12;
    for (var i = 0; i < dashes; i++) {
      final start = i * 2 * math.pi / dashes;
      canvas.drawArc(Rect.fromCircle(center: c, radius: r), start, math.pi / dashes, false,
          stroke);
    }
  }

  @override
  bool shouldRepaint(_DashedCircle old) => old.color != color || old.fill != fill;
}
