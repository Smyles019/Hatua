import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../api/models.dart';
import '../i18n/strings.dart';
import '../theme/colors.dart';
import '../theme/theme.dart';

/// Graphs for the child health record (the purple book): the vaccine timeline, the
/// progress ring, vitamin A and deworming dots, the growth chart with the WHO zones,
/// the arm tape (MUAC) and the meals-a-day bars. Every mark also differs by shape, not
/// only colour, so each graph still reads when printed in black and white.

// ---------------------------------------------------------------------------
// Dose marks
// ---------------------------------------------------------------------------

/// A dose as a small mark: filled circle = given, ring = coming up, thick ring = due now,
/// cross in a circle = overdue, dashed ring = not copied from the booklet.
class DoseMark extends StatelessWidget {
  const DoseMark(this.status, {super.key, this.size = 18});
  final String status;
  final double size;

  @override
  Widget build(BuildContext context) => SizedBox.square(
        dimension: size,
        child: CustomPaint(painter: _MarkPainter(status, _colours(context))),
      );
}

class MarkColours {
  MarkColours(this.given, this.due, this.overdue, this.muted, this.fill);
  final Color given, due, overdue, muted, fill;
}

MarkColours _colours(BuildContext context) => MarkColours(context.hc.riskLow, context.hc.riskMedium,
    context.hc.riskHigh, context.hc.plum200, context.hc.surfaceCard);

class _MarkPainter extends CustomPainter {
  _MarkPainter(this.status, this.c);
  final String status;
  final MarkColours c;

  @override
  void paint(Canvas canvas, Size size) => paintMark(canvas, size.center(Offset.zero),
      size.shortestSide / 2 - 1.5, status, c);

  @override
  bool shouldRepaint(_MarkPainter old) => old.status != status;
}

void paintMark(Canvas canvas, Offset at, double r, String status, MarkColours c) {
  final stroke = Paint()
    ..style = PaintingStyle.stroke
    ..strokeWidth = 2;
  switch (status) {
    case 'given':
      canvas.drawCircle(at, r, Paint()..color = c.given);
      final tick = Path()
        ..moveTo(at.dx - r * 0.45, at.dy)
        ..lineTo(at.dx - r * 0.1, at.dy + r * 0.35)
        ..lineTo(at.dx + r * 0.5, at.dy - r * 0.35);
      canvas.drawPath(tick, stroke..color = c.fill);
    case 'overdue':
      canvas.drawCircle(at, r, Paint()..color = c.fill);
      canvas.drawCircle(at, r, stroke..color = c.overdue);
      final d = r * 0.45;
      canvas.drawLine(at.translate(-d, -d), at.translate(d, d), stroke);
      canvas.drawLine(at.translate(d, -d), at.translate(-d, d), stroke);
    case 'due':
      canvas.drawCircle(at, r, Paint()..color = c.fill);
      canvas.drawCircle(at, r - 1, stroke..color = c.due..strokeWidth = 3.5);
    case 'not_recorded':
      canvas.drawCircle(at, r, Paint()..color = c.fill);
      final p = stroke..color = c.muted;
      const n = 8;
      for (var i = 0; i < n; i++) {
        final a = i * 2 * math.pi / n;
        canvas.drawArc(Rect.fromCircle(center: at, radius: r), a, math.pi / n, false, p);
      }
    default: // upcoming
      canvas.drawCircle(at, r, Paint()..color = c.fill);
      canvas.drawCircle(at, r, stroke..color = c.muted);
  }
}

/// What the marks mean, for under a graph.
class DoseLegend extends StatelessWidget {
  const DoseLegend({super.key, this.showNotRecorded = true});
  final bool showNotRecorded;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme.bodySmall;
    Widget item(String status, String label) => Row(mainAxisSize: MainAxisSize.min, children: [
          DoseMark(status, size: 14),
          const SizedBox(width: 4),
          Text(label, style: t),
        ]);
    return Wrap(spacing: Space.s3, runSpacing: Space.s1, children: [
      item('given', tr('Given')),
      item('due', tr('Due now')),
      item('overdue', tr('Overdue')),
      item('upcoming', tr('Coming up')),
      if (showNotRecorded) item('not_recorded', tr('Not copied from the booklet')),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Progress ring
// ---------------------------------------------------------------------------

/// "12 of 18": a ring filled in proportion, with the numbers in the middle.
class ProgressRing extends StatelessWidget {
  const ProgressRing({super.key, required this.done, required this.total, this.size = 92});
  final int done;
  final int total;
  final double size;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Semantics(
      label: tr('{done} of {total} given', {'done': done, 'total': total}),
      child: SizedBox.square(
        dimension: size,
        child: Stack(alignment: Alignment.center, children: [
          CustomPaint(
            size: Size.square(size),
            painter: _RingPainter(total == 0 ? 0 : done / total, context.hc.riskLow,
                context.hc.plum100),
          ),
          Column(mainAxisSize: MainAxisSize.min, children: [
            Text('$done', style: t.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
            Text(tr('of {total}', {'total': total}), style: t.bodySmall),
          ]),
        ]),
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter(this.fraction, this.fg, this.bg);
  final double fraction;
  final Color fg, bg;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final p = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * 0.11
      ..strokeCap = StrokeCap.round;
    final r = rect.deflate(p.strokeWidth / 2);
    canvas.drawArc(r, 0, 2 * math.pi, false, p..color = bg);
    if (fraction > 0) {
      canvas.drawArc(r, -math.pi / 2, 2 * math.pi * fraction.clamp(0, 1), false, p..color = fg);
    }
  }

  @override
  bool shouldRepaint(_RingPainter old) => old.fraction != fraction;
}

// ---------------------------------------------------------------------------
// Vaccine timeline
// ---------------------------------------------------------------------------

/// The vaccine visits as stops along a line (birth, 6, 10 and 14 weeks, 9 and 18 months,
/// and the county-only ones), each with one mark per dose, and a "today" pin.
class VaccineTimeline extends StatelessWidget {
  const VaccineTimeline({super.key, required this.doses, required this.dateOfBirth});
  final List<Dose> doses; // vaccines only
  final DateTime dateOfBirth;

  @override
  Widget build(BuildContext context) {
    final visits = <String, List<Dose>>{};
    for (final d in doses) {
      visits.putIfAbsent(d.visit, () => []).add(d);
    }
    final stops = visits.entries.toList()
      ..sort((a, b) => a.value.first.dueOn.compareTo(b.value.first.dueOn));
    final tallest = stops.fold<int>(1, (m, s) => math.max(m, s.value.length));
    final height = 46.0 + tallest * 22;
    final given = doses.where((d) => d.given).length;
    return Semantics(
      label: tr('Vaccine timeline: {done} of {total} given', {'done': given, 'total': doses.length}),
      child: SizedBox(
        height: height,
        child: CustomPaint(
          size: Size.infinite,
          painter: _TimelinePainter(
            stops: [for (final s in stops) (s.key, s.value.map((d) => d.status).toList(), s.value.first.dueOn)],
            today: DateTime.now(),
            colours: _colours(context),
            line: context.hc.plum200,
            pin: context.hc.plum700,
            label: Theme.of(context).textTheme.bodySmall!,
          ),
        ),
      ),
    );
  }
}

class _TimelinePainter extends CustomPainter {
  _TimelinePainter({
    required this.stops,
    required this.today,
    required this.colours,
    required this.line,
    required this.pin,
    required this.label,
  });
  final List<(String, List<String>, DateTime)> stops;
  final DateTime today;
  final MarkColours colours;
  final Color line, pin;
  final TextStyle label;

  @override
  void paint(Canvas canvas, Size size) {
    if (stops.isEmpty) return;
    const pad = 22.0, markR = 8.0, gap = 22.0;
    final baseY = size.height - 24;
    final step = stops.length == 1 ? 0.0 : (size.width - 2 * pad) / (stops.length - 1);
    double xOf(int i) => pad + i * step;

    canvas.drawLine(Offset(pad, baseY), Offset(size.width - pad, baseY),
        Paint()
          ..color = line
          ..strokeWidth = 3
          ..strokeCap = StrokeCap.round);

    for (var i = 0; i < stops.length; i++) {
      final (name, statuses, _) = stops[i];
      final x = xOf(i);
      canvas.drawCircle(Offset(x, baseY), 4, Paint()..color = line);
      for (var j = 0; j < statuses.length; j++) {
        paintMark(canvas, Offset(x, baseY - 18 - j * gap), markR, statuses[j], colours);
      }
      final short = name.replaceFirst(RegExp(r'^(At|Katika umri wa|Wakati wa)\s+'), '');
      _text(canvas, short, Offset(x, baseY + 6));
    }

    // Today: between the stop already passed and the next one.
    var pos = -1.0;
    for (var i = 0; i < stops.length; i++) {
      if (!stops[i].$3.isAfter(today)) pos = i.toDouble();
    }
    if (pos < stops.length - 1 && pos >= 0) {
      final a = stops[pos.toInt()].$3, b = stops[pos.toInt() + 1].$3;
      final span = b.difference(a).inDays;
      if (span > 0) pos += today.difference(a).inDays / span;
    }
    if (pos >= 0) {
      final x = pad + pos * step;
      final p = Paint()
        ..color = pin
        ..strokeWidth = 2;
      for (var y = 0.0; y < baseY; y += 6) {
        canvas.drawLine(Offset(x, y), Offset(x, math.min(y + 3, baseY)), p);
      }
      _text(canvas, tr('Today'), Offset(x, 0), bold: true, colour: pin);
    }
  }

  void _text(Canvas canvas, String s, Offset at, {bool bold = false, Color? colour}) {
    final tp = TextPainter(
      text: TextSpan(
          text: s,
          style: label.copyWith(
              fontWeight: bold ? FontWeight.w700 : null, color: colour, fontSize: 11)),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas, at.translate(-tp.width / 2, 0));
  }

  @override
  bool shouldRepaint(_TimelinePainter old) => true;
}

// ---------------------------------------------------------------------------
// Vitamin A and deworming dots
// ---------------------------------------------------------------------------

/// One mark per 6-monthly dose, labelled with the age.
class DoseDots extends StatelessWidget {
  const DoseDots({super.key, required this.doses});
  final List<Dose> doses;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 11);
    return Wrap(spacing: Space.s2, runSpacing: Space.s2, children: [
      for (final d in doses)
        Column(mainAxisSize: MainAxisSize.min, children: [
          DoseMark(d.status, size: 26),
          const SizedBox(height: 2),
          Text(d.visit.replaceAll(RegExp(r'[^0-9]'), '') + tr('m'), style: t),
        ]),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Growth with the WHO zones
// ---------------------------------------------------------------------------

/// WHO lines for one measure, month 0 to 60 (backend GET /children/{id}/growth-reference).
class GrowthReference {
  GrowthReference(this.rows);
  final List<(int, double, double, double, double)> rows; // month, -3, -2, median, +2

  factory GrowthReference.fromJson(List<dynamic> j) => GrowthReference([
        for (final r in j.cast<Map<String, dynamic>>())
          (
            r['month'] as int,
            (r['sd_m3'] as num).toDouble(),
            (r['sd_m2'] as num).toDouble(),
            (r['median'] as num).toDouble(),
            (r['sd_p2'] as num).toDouble(),
          )
      ]);
}

/// The booklet's growth chart: the healthy band (-2 to +2 SD), the "watch" band
/// (-3 to -2), "very low" below -3, the median line, and the child's measurements.
class GrowthZonesChart extends StatelessWidget {
  const GrowthZonesChart({
    super.key,
    required this.reference,
    required this.points,
    required this.unit,
    required this.maxValue,
  });
  final GrowthReference reference;
  final List<Offset> points; // x = age in months, y = kg or cm
  final String unit;
  final double maxValue;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final c = context.hc;
    Widget key(Color fill, String label, {bool hatch = false}) =>
        Row(mainAxisSize: MainAxisSize.min, children: [
          Container(
              width: 14,
              height: 14,
              decoration: BoxDecoration(color: fill, border: Border.all(color: c.plum200))),
          const SizedBox(width: 4),
          Text(label, style: t.bodySmall),
        ]);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      AspectRatio(
        aspectRatio: 1.45,
        child: CustomPaint(
          painter: _ZonesPainter(
            ref: reference,
            points: points,
            unit: unit,
            maxValue: maxValue,
            healthy: c.riskLowBg,
            watch: c.riskMediumBg,
            low: c.riskHighBg,
            median: c.riskLow,
            dot: c.plum700,
            axis: c.plum200,
            label: t.bodySmall!,
          ),
        ),
      ),
      const SizedBox(height: Space.s2),
      Wrap(spacing: Space.s3, runSpacing: Space.s1, children: [
        key(c.riskLowBg, tr('Healthy range')),
        key(c.riskMediumBg, tr('Watch (below -2)')),
        key(c.riskHighBg, tr('Very low (below -3)')),
      ]),
    ]);
  }
}

class _ZonesPainter extends CustomPainter {
  _ZonesPainter({
    required this.ref,
    required this.points,
    required this.unit,
    required this.maxValue,
    required this.healthy,
    required this.watch,
    required this.low,
    required this.median,
    required this.dot,
    required this.axis,
    required this.label,
  });
  final GrowthReference ref;
  final List<Offset> points;
  final String unit;
  final double maxValue;
  final Color healthy, watch, low, median, dot, axis;
  final TextStyle label;

  static const _left = 30.0, _bottom = 20.0, _top = 8.0;

  @override
  void paint(Canvas canvas, Size size) {
    final minValue = unit == 'cm' ? 40.0 : 0.0;
    final w = size.width - _left, h = size.height - _bottom - _top;
    Offset at(double m, double v) =>
        Offset(_left + m / 60 * w, _top + h - ((v - minValue) / (maxValue - minValue)) * h);

    // Zones as bands between the WHO lines.
    void band(double Function((int, double, double, double, double)) lo,
        double Function((int, double, double, double, double)) hi, Color colour) {
      final p = Path();
      for (var i = 0; i < ref.rows.length; i++) {
        final r = ref.rows[i];
        final o = at(r.$1.toDouble(), lo(r).clamp(minValue, maxValue));
        i == 0 ? p.moveTo(o.dx, o.dy) : p.lineTo(o.dx, o.dy);
      }
      for (final r in ref.rows.reversed) {
        final o = at(r.$1.toDouble(), hi(r).clamp(minValue, maxValue));
        p.lineTo(o.dx, o.dy);
      }
      canvas.drawPath(p..close(), Paint()..color = colour);
    }

    band((r) => minValue, (r) => r.$2, low);
    band((r) => r.$2, (r) => r.$3, watch);
    band((r) => r.$3, (r) => r.$5, healthy);

    // Grid and labels.
    final grid = Paint()
      ..color = axis
      ..strokeWidth = 1;
    for (var y = 0; y <= 5; y++) {
      final x = at(y * 12.0, minValue).dx;
      canvas.drawLine(Offset(x, _top), Offset(x, _top + h), grid);
      _text(canvas, y == 0 ? tr('Birth') : '$y y', Offset(x, _top + h + 4), centre: y != 0);
    }
    final stepV = unit == 'cm' ? 20 : 5;
    for (var v = minValue.toInt(); v <= maxValue; v += stepV) {
      final y = at(0, v.toDouble()).dy;
      canvas.drawLine(Offset(_left, y), Offset(size.width, y), grid);
      _text(canvas, '$v', Offset(0, y - 7));
    }
    _text(canvas, unit, const Offset(0, -2));

    // Median, dashed so it differs from the child's line in black and white.
    final mid = Paint()
      ..color = median
      ..strokeWidth = 1.5;
    for (var i = 1; i < ref.rows.length; i += 2) {
      final a = ref.rows[i - 1], b = ref.rows[i];
      canvas.drawLine(at(a.$1.toDouble(), a.$4), at(b.$1.toDouble(), b.$4), mid);
    }

    // The child's measurements.
    final sorted = [...points]..sort((a, b) => a.dx.compareTo(b.dx));
    final line = Paint()
      ..color = dot
      ..strokeWidth = 2.5;
    for (var i = 1; i < sorted.length; i++) {
      canvas.drawLine(at(sorted[i - 1].dx, sorted[i - 1].dy), at(sorted[i].dx, sorted[i].dy), line);
    }
    for (final p in sorted) {
      final o = at(p.dx, p.dy.clamp(minValue, maxValue));
      canvas.drawCircle(o, 5.5, Paint()..color = Colors.white);
      canvas.drawCircle(o, 4.5, Paint()..color = dot);
    }
  }

  void _text(Canvas canvas, String s, Offset where, {bool centre = false}) {
    final tp = TextPainter(
        text: TextSpan(text: s, style: label.copyWith(fontSize: 11)),
        textDirection: TextDirection.ltr)
      ..layout();
    tp.paint(canvas, centre ? where.translate(-tp.width / 2, 0) : where);
  }

  @override
  bool shouldRepaint(_ZonesPainter old) => old.points.length != points.length || old.unit != unit;
}

// ---------------------------------------------------------------------------
// The arm tape (MUAC)
// ---------------------------------------------------------------------------

/// The coloured arm tape from the booklet: red below 11.5 cm, yellow to 12.5 cm, green
/// above, with a pointer at the child's latest measurement.
class MuacTape extends StatelessWidget {
  const MuacTape({super.key, required this.muacCm});
  final double muacCm;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final c = context.hc;
    final (String zone, Color colour) = muacCm < 11.5
        ? (tr('Red: very thin. See a health worker now.'), c.riskHigh)
        : muacCm < 12.5
            ? (tr('Yellow: thin. See a health worker soon.'), c.riskMedium)
            : (tr('Green: healthy.'), c.riskLow);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      SizedBox(
        height: 54,
        child: CustomPaint(
          size: Size.infinite,
          painter: _TapePainter(muacCm, c.riskHigh, c.riskMedium, c.riskLow, c.plum900,
              t.bodySmall!),
        ),
      ),
      const SizedBox(height: Space.s1),
      Text('${muacCm.toStringAsFixed(1)} cm · $zone',
          style: t.bodyMedium?.copyWith(color: colour == c.riskLow ? null : c.plum900,
              fontWeight: FontWeight.w700)),
    ]);
  }
}

class _TapePainter extends CustomPainter {
  _TapePainter(this.value, this.red, this.yellow, this.green, this.ink, this.label);
  final double value;
  final Color red, yellow, green, ink;
  final TextStyle label;

  static const lo = 9.0, hi = 16.0;

  @override
  void paint(Canvas canvas, Size size) {
    double x(double cm) => (cm - lo) / (hi - lo) * size.width;
    const top = 14.0, bar = 18.0;
    final r = Radius.circular(bar / 2);
    canvas.drawRRect(
        RRect.fromRectAndCorners(Rect.fromLTRB(0, top, x(11.5), top + bar), topLeft: r, bottomLeft: r),
        Paint()..color = red);
    canvas.drawRect(Rect.fromLTRB(x(11.5), top, x(12.5), top + bar), Paint()..color = yellow);
    canvas.drawRRect(
        RRect.fromRectAndCorners(Rect.fromLTRB(x(12.5), top, size.width, top + bar),
            topRight: r, bottomRight: r),
        Paint()..color = green);
    // Zone letters, so the tape reads without colour.
    for (final (cm, s) in [(10.25, 'R'), (12.0, 'Y'), (14.25, 'G')]) {
      _text(canvas, s, Offset(x(cm), top + 2), colour: Colors.white, bold: true);
    }
    for (final cm in [10, 11.5, 12.5, 14, 16]) {
      _text(canvas, '$cm', Offset(x(cm.toDouble()).clamp(8, size.width - 8), top + bar + 3));
    }
    // Pointer.
    final px = x(value.clamp(lo, hi));
    final tri = Path()
      ..moveTo(px - 7, 0)
      ..lineTo(px + 7, 0)
      ..lineTo(px, top - 1)
      ..close();
    canvas.drawPath(tri, Paint()..color = ink);
    canvas.drawLine(Offset(px, top), Offset(px, top + bar),
        Paint()
          ..color = ink
          ..strokeWidth = 3);
  }

  void _text(Canvas canvas, String s, Offset at, {Color? colour, bool bold = false}) {
    final tp = TextPainter(
        text: TextSpan(
            text: s,
            style: label.copyWith(
                fontSize: 11, color: colour, fontWeight: bold ? FontWeight.w800 : null)),
        textDirection: TextDirection.ltr)
      ..layout();
    tp.paint(canvas, at.translate(-tp.width / 2, 0));
  }

  @override
  bool shouldRepaint(_TapePainter old) => old.value != value;
}

// ---------------------------------------------------------------------------
// Meals a day
// ---------------------------------------------------------------------------

/// Bars of meals and snacks a day by age (the feeding guide), with the child's age band
/// highlighted.
class MealsChart extends StatelessWidget {
  const MealsChart({super.key, required this.bands, required this.current});

  /// (label, meals, snacks); meals 0 means breast milk only.
  final List<(String, int, int)> bands;
  final int current;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final c = context.hc;
    const maxSlots = 5;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      for (var i = 0; i < bands.length; i++)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 3),
          child: Row(children: [
            SizedBox(
              width: 92,
              child: Text(bands[i].$1,
                  style: t.bodySmall?.copyWith(
                      fontWeight: i == current ? FontWeight.w800 : null, color: c.plum900)),
            ),
            Expanded(
              child: LayoutBuilder(builder: (context, box) {
                final slot = box.maxWidth / maxSlots;
                final (_, meals, snacks) = bands[i];
                if (meals == 0) {
                  return Container(
                    height: 20,
                    alignment: Alignment.centerLeft,
                    padding: const EdgeInsets.symmetric(horizontal: 6),
                    decoration: BoxDecoration(
                        color: i == current ? c.sky500 : c.sky100,
                        borderRadius: BorderRadius.circular(Radii.sm)),
                    child: Text(tr('Breast milk only'),
                        style: t.bodySmall?.copyWith(
                            fontSize: 11, color: i == current ? Colors.white : c.plum900)),
                  );
                }
                return Row(children: [
                  for (var m = 0; m < meals; m++)
                    _block(slot, i == current ? c.plum700 : c.plum200, Icons.restaurant_rounded,
                        i == current),
                  for (var s = 0; s < snacks; s++)
                    _block(slot, i == current ? c.sun500 : c.sun100, Icons.apple_rounded,
                        i == current),
                ]);
              }),
            ),
          ]),
        ),
      const SizedBox(height: Space.s1),
      Row(children: [
        Icon(Icons.restaurant_rounded, size: 14, color: c.plum700),
        const SizedBox(width: 4),
        Text(tr('Meal'), style: t.bodySmall),
        const SizedBox(width: Space.s3),
        Icon(Icons.apple_rounded, size: 14, color: c.sun500),
        const SizedBox(width: 4),
        Text(tr('Snack'), style: t.bodySmall),
      ]),
    ]);
  }

  Widget _block(double w, Color colour, IconData icon, bool on) => Container(
        width: w - 4,
        height: 20,
        margin: const EdgeInsets.only(right: 4),
        decoration: BoxDecoration(color: colour, borderRadius: BorderRadius.circular(4)),
        child: Icon(icon, size: 13, color: on ? Colors.white : Colors.black54),
      );
}
