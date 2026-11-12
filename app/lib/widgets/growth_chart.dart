import 'package:flutter/material.dart';

import '../api/models.dart';
import '../theme/colors.dart';
import '../i18n/strings.dart';

/// WHO Child Growth Standards, weight-for-age, birth to 5 years: the 3rd percentile,
/// the median and the 97th percentile in kg at selected ages in months. Copied from the
/// WHO simplified field tables (percentiles), the same curves printed on the growth
/// chart in the Mother and Child Health Handbook.
/// (months, 3rd, median, 97th)
const _boys = [
  (0, 2.5, 3.3, 4.3), (3, 5.1, 6.4, 7.9), (6, 6.4, 7.9, 9.7), (9, 7.2, 8.9, 10.9),
  (12, 7.8, 9.6, 11.8), (15, 8.4, 10.3, 12.7), (18, 8.9, 10.9, 13.5), (21, 9.3, 11.5, 14.3),
  (24, 9.8, 12.2, 15.1), (27, 10.2, 12.7, 15.9), (36, 11.4, 14.3, 18.0),
  (42, 12.2, 15.3, 19.4), (48, 12.9, 16.3, 20.9), (54, 13.6, 17.3, 22.3),
  (60, 14.3, 18.3, 23.8),
];
const _girls = [
  (0, 2.4, 3.2, 4.2), (3, 4.6, 5.8, 7.4), (6, 5.8, 7.3, 9.2), (9, 6.6, 8.2, 10.4),
  (12, 7.1, 8.9, 11.3), (15, 7.7, 9.6, 12.2), (18, 8.2, 10.2, 13.0), (21, 8.7, 10.9, 13.8),
  (24, 9.2, 11.5, 14.6), (27, 9.6, 12.1, 15.4), (36, 11.0, 13.9, 17.8),
  (42, 11.8, 15.0, 19.5), (48, 12.5, 16.1, 21.1), (54, 13.2, 17.2, 22.8),
  (60, 14.0, 18.2, 24.4),
];

/// Age in months (with a fraction) on the day of a measurement.
double ageInMonthsOn(DateTime dateOfBirth, DateTime day) =>
    day.difference(dateOfBirth).inDays / 30.4375;

/// The 3rd, median and 97th percentile weight at an age, by straight-line interpolation
/// between the table rows. Ages outside 0 to 60 months are clamped.
(double, double, double) weightReference(String sex, double months) {
  final rows = sex == 'female' ? _girls : _boys;
  final m = months.clamp(0, 60).toDouble();
  for (var i = 1; i < rows.length; i++) {
    final a = rows[i - 1], b = rows[i];
    if (m <= b.$1) {
      final f = (m - a.$1) / (b.$1 - a.$1);
      return (a.$2 + (b.$2 - a.$2) * f, a.$3 + (b.$3 - a.$3) * f, a.$4 + (b.$4 - a.$4) * f);
    }
  }
  final last = rows.last;
  return (last.$2, last.$3, last.$4);
}

/// Weight-for-age chart: the child's weights as dots over the band where most healthy
/// children's weights fall (3rd to 97th percentile), with the median as a line.
class WeightChart extends StatelessWidget {
  const WeightChart({super.key, required this.child});
  final Child child;

  @override
  Widget build(BuildContext context) {
    final points = [
      for (final g in child.growth)
        if (g.weightKg != null)
          Offset(ageInMonthsOn(child.dateOfBirth, g.measuredOn).clamp(0, 60).toDouble(),
              g.weightKg!),
    ];
    final t = Theme.of(context).textTheme;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Semantics(
        label: tr(points.length == 1 ? 'Weight for age chart with 1 measurement' : 'Weight for age chart with {n} measurements',
            {'n': points.length}),
        child: AspectRatio(
          aspectRatio: 1.6,
          child: CustomPaint(
            painter: _WeightPainter(
              sex: child.sex,
              points: points,
              band: context.hc.sky100,
              median: context.hc.sky500,
              dot: context.hc.plum700,
              axis: context.hc.plum200,
              label: t.bodySmall!,
            ),
          ),
        ),
      ),
      const SizedBox(height: 8),
      Text(
        tr("Dots: {firstName}'s weights. Shaded area: where most healthy children of this age fall (WHO growth standards). Line: the middle.", {'firstName': child.firstName}),
        style: t.bodySmall,
      ),
    ]);
  }
}

class _WeightPainter extends CustomPainter {
  _WeightPainter({
    required this.sex,
    required this.points,
    required this.band,
    required this.median,
    required this.dot,
    required this.axis,
    required this.label,
  });
  final String sex;
  final List<Offset> points; // x = age in months, y = kg
  final Color band, median, dot, axis;
  final TextStyle label;

  static const _maxKg = 26.0;
  static const _left = 28.0, _bottom = 20.0;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width - _left, h = size.height - _bottom;
    Offset at(double months, double kg) =>
        Offset(_left + months / 60 * w, h - (kg / _maxKg) * h);

    // Grid: every year across, every 5 kg up.
    final grid = Paint()
      ..color = axis
      ..strokeWidth = 1;
    for (var y = 0; y <= 5; y++) {
      final x = at(y * 12.0, 0).dx;
      canvas.drawLine(Offset(x, 0), Offset(x, h), grid);
      _text(canvas, y == 0 ? tr('Birth') : '$y y', Offset(x, h + 4), centre: y != 0);
    }
    for (var kg = 0; kg <= 25; kg += 5) {
      final y = at(0, kg.toDouble()).dy;
      canvas.drawLine(Offset(_left, y), Offset(size.width, y), grid);
      if (kg > 0) _text(canvas, '$kg', Offset(0, y - 7));
    }
    _text(canvas, 'kg', const Offset(0, 0));

    // Band between the 3rd and 97th percentiles, and the median line.
    final low = Path(), high = <Offset>[], mid = Path();
    for (var m = 0; m <= 60; m++) {
      final (p3, p50, p97) = weightReference(sex, m.toDouble());
      final a = at(m.toDouble(), p3), c = at(m.toDouble(), p50);
      high.add(at(m.toDouble(), p97));
      if (m == 0) {
        low.moveTo(a.dx, a.dy);
        mid.moveTo(c.dx, c.dy);
      } else {
        low.lineTo(a.dx, a.dy);
        mid.lineTo(c.dx, c.dy);
      }
    }
    for (final p in high.reversed) {
      low.lineTo(p.dx, p.dy);
    }
    low.close();
    canvas.drawPath(low, Paint()..color = band);
    canvas.drawPath(
        mid,
        Paint()
          ..color = median
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2);

    // The child's weights, joined in date order.
    final line = Paint()
      ..color = dot
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;
    final sorted = [...points]..sort((a, b) => a.dx.compareTo(b.dx));
    for (var i = 1; i < sorted.length; i++) {
      canvas.drawLine(at(sorted[i - 1].dx, sorted[i - 1].dy), at(sorted[i].dx, sorted[i].dy), line);
    }
    for (final p in sorted) {
      canvas.drawCircle(at(p.dx, p.dy.clamp(0, _maxKg).toDouble()), 5, Paint()..color = dot);
    }
  }

  void _text(Canvas canvas, String s, Offset where, {bool centre = false}) {
    final tp = TextPainter(text: TextSpan(text: s, style: label), textDirection: TextDirection.ltr)
      ..layout();
    tp.paint(canvas, centre ? where.translate(-tp.width / 2, 0) : where);
  }

  @override
  bool shouldRepaint(_WeightPainter old) =>
      old.sex != sex || old.points.length != points.length || old.band != band;
}
