import 'package:flutter/material.dart';

import '../../i18n/strings.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/record_charts.dart';

/// The feeding pages of the purple book by age: what to give, how often and how much.
/// General guidance for healthy children (WHO and MOH infant and young child feeding);
/// a child who is sick, very thin or not growing well needs advice from a health worker.
class FeedingBand {
  const FeedingBand(this.from, this.to, this.label, this.meals, this.snacks, this.tips);
  final int from, to; // age in months
  final String label;
  final int meals, snacks; // 0 meals: breast milk only
  final List<String> tips;
}

const feedingBands = [
  FeedingBand(0, 5, '0 to 5 months', 0, 0, [
    'Give breast milk only, day and night, at least 8 times in 24 hours.',
    'No water, no other drinks and no food, even in hot weather.',
    'Feed when the baby shows hunger: turning the head, sucking fingers, being restless.',
  ]),
  FeedingBand(6, 8, '6 to 8 months', 2, 1, [
    'Keep breastfeeding, and start soft foods: thick porridge or mashed food.',
    '2 to 3 meals a day. Start with 2 to 3 spoonfuls and slowly give more.',
    'Add mashed beans, egg, fish or meat, and orange or green vegetables.',
  ]),
  FeedingBand(9, 11, '9 to 11 months', 3, 1, [
    'Keep breastfeeding. Give 3 to 4 meals a day, about half a cup each, and 1 to 2 snacks.',
    'Chop or mash family food finely. Let the baby hold soft pieces.',
    'Use the child\'s own plate or bowl, so you can see how much they eat.',
  ]),
  FeedingBand(12, 23, '1 to 2 years', 3, 2, [
    'Keep breastfeeding to 2 years or more.',
    '3 to 4 meals a day, three quarters to one cup each, and 1 to 2 snacks.',
    'Give family foods cut small: a food from animals, beans or nuts, and fruit or vegetables every day.',
  ]),
  FeedingBand(24, 59, '2 to 5 years', 3, 2, [
    '3 meals and 2 snacks a day from the family pot.',
    'Different foods each day: grains, beans, milk, eggs, fish or meat, fruit and vegetables.',
    'Sit with the child at meals and encourage them, without forcing.',
  ]),
];

int feedingBandFor(int ageMonths) =>
    feedingBands.indexWhere((b) => ageMonths >= b.from && ageMonths <= b.to).clamp(0, feedingBands.length - 1);

class FeedingGuideScreen extends StatelessWidget {
  const FeedingGuideScreen({super.key, required this.childName, required this.ageMonths});
  final String childName;
  final int ageMonths;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final c = context.hc;
    final current = feedingBandFor(ageMonths);
    return Scaffold(
      appBar: AppBar(title: Text(tr('Feeding guide'))),
      body: ListView(padding: const EdgeInsets.all(Space.s4), children: [
        HatuaCard(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(tr('Meals a day by age'), style: t.titleMedium),
            const SizedBox(height: Space.s3),
            MealsChart(
              bands: [for (final b in feedingBands) (tr(b.label), b.meals, b.snacks)],
              current: current,
            ),
          ]),
        ),
        for (var i = 0; i < feedingBands.length; i++) ...[
          const SizedBox(height: Space.s3),
          HatuaCard(
            color: i == current ? c.sun100 : null,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text(tr(feedingBands[i].label), style: t.titleMedium)),
                if (i == current)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: Space.s2, vertical: 2),
                    decoration: BoxDecoration(
                        color: c.plum700, borderRadius: BorderRadius.circular(999)),
                    child: Text(tr("{name}'s age", {'name': childName}),
                        style: t.labelSmall?.copyWith(color: c.onPrimary)),
                  ),
              ]),
              for (final tip in feedingBands[i].tips)
                Padding(
                  padding: const EdgeInsets.only(top: Space.s1),
                  child: Text('•  ${tr(tip)}', style: t.bodyMedium?.copyWith(color: c.plum900)),
                ),
            ]),
          ),
        ],
        const SizedBox(height: Space.s3),
        Text(
          tr('Wash your hands and the child\'s hands before eating. If your child is sick, very thin or not growing well, ask a health worker how to feed them.'),
          style: t.bodySmall,
        ),
        const SizedBox(height: Space.s6),
      ]),
    );
  }
}
