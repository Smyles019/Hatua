import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../i18n/strings.dart';

/// Visual identity of the four developmental domains. Labels match the backend
/// (services/results.py DOMAIN_LABELS); colour and icon never change across the app.
class DomainStyle {
  const DomainStyle(this.label, this.color, this.tint, this.icon);
  final String label;
  final Color color;
  final Color tint;
  final IconData icon;

  static DomainStyle of(BuildContext context, String domain) {
    final c = context.hc;
    return switch (domain) {
      'language' => DomainStyle(
          tr('Language'), c.sun500, c.sun100, Icons.chat_bubble_outline_rounded),
      'cognitive' => DomainStyle(
          tr('Thinking and learning'), c.blush500, c.blush100, Icons.lightbulb_outline_rounded),
      'social_emotional' => DomainStyle(
          tr('Social and emotional'), c.domainSocial, c.plum100, Icons.people_outline_rounded),
      _ => DomainStyle(tr('Movement'), c.sky500, c.sky100, Icons.directions_walk_rounded),
    };
  }

  /// Which domain a question belongs to (hatua_ml/models/explain.py DOMAINS).
  /// Under-24-month WHO questions are all movement. Under-24 model questions (ddi...)
  /// carry their area in letters 4 and 5: cm = language, fm and gm = movement.
  static String domainOfItem(String item) {
    if (item.startsWith('who_')) return 'motor';
    if (item.startsWith('ddi') && item.length >= 5) {
      return item.substring(3, 5) == 'cm' ? 'language' : 'motor';
    }
    final n = int.tryParse(item.replaceAll(RegExp(r'[^0-9]'), '')) ?? 0;
    if (n >= 21 && n <= 24) return 'motor';
    if (n >= 25 && n <= 29) return 'language';
    if (n >= 30 && n <= 35) return 'cognitive';
    return 'social_emotional';
  }
}

/// One line naming the areas a check did not cover (not_assessed), or null if it
/// covered all four. Used on the caregiver result and the CHW case review.
String? notCheckedNote(BuildContext context, Iterable<String> domains) {
  final labels = domains.map((d) => DomainStyle.of(context, d).label).toList();
  if (labels.isEmpty) return null;
  return tr(labels.length == 1
          ? 'Not checked at this age: {areas}. This is checked from 24 months.'
          : 'Not checked at this age: {areas}. These are checked from 24 months.', {'areas': labels.join(', ')});
}

/// Round domain badge with a line icon (brand board "highlights").
class DomainBadge extends StatelessWidget {
  const DomainBadge(this.domain, {super.key, this.size = 40});
  final String domain;
  final double size;

  @override
  Widget build(BuildContext context) {
    final s = DomainStyle.of(context, domain);
    return Semantics(
      label: s.label,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(color: s.color, shape: BoxShape.circle),
        child: Icon(s.icon, size: size * 0.5, color: context.hc.onBright),
      ),
    );
  }
}

/// Small pill tag naming a domain, used above milestone questions.
class DomainTag extends StatelessWidget {
  const DomainTag(this.domain, {super.key});
  final String domain;

  @override
  Widget build(BuildContext context) {
    final s = DomainStyle.of(context, domain);
    return Container(
      padding: const EdgeInsets.fromLTRB(8, 4, 12, 4),
      decoration: BoxDecoration(color: s.tint, borderRadius: BorderRadius.circular(999)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(s.icon, size: 18, color: context.hc.plum900),
        const SizedBox(width: 4),
        Text(s.label.toUpperCase(),
            style: Theme.of(context).textTheme.labelMedium?.copyWith(color: context.hc.plum900)),
      ]),
    );
  }
}


/// For a movement question: 'gross' (big movements like sitting and walking) or 'fine'
/// (hand and finger skills like grasping and stacking). Null for other domains.
/// Movement stays one scored category; this only says which kind a concern came from.
String? motorKindOfItem(String item) {
  if (item.startsWith('who_')) return 'gross';
  if (item.startsWith('ddi') && item.length >= 5) {
    return switch (item.substring(3, 5)) { 'gm' => 'gross', 'fm' => 'fine', _ => null };
  }
  final n = int.tryParse(item.replaceAll(RegExp(r'[^0-9]'), '')) ?? 0;
  if (n == 21 || n == 22) return 'gross'; // walking on uneven ground, jumping
  if (n == 23 || n == 24) return 'fine'; // dressing, buttons
  return null;
}

String motorKindLabel(String kind) =>
    kind == 'gross' ? tr('Big movements') : tr('Hand and finger skills');

/// Pill tag above the hearing and eye questions (not one of the four domains).
class ScreeningTag extends StatelessWidget {
  const ScreeningTag(this.kind, {super.key});
  final String kind; // hearing | vision

  @override
  Widget build(BuildContext context) {
    final hearing = kind == 'hearing';
    return Container(
      padding: const EdgeInsets.fromLTRB(8, 4, 12, 4),
      decoration:
          BoxDecoration(color: context.hc.plum100, borderRadius: BorderRadius.circular(999)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(hearing ? Icons.hearing_rounded : Icons.visibility_outlined,
            size: 18, color: context.hc.plum900),
        const SizedBox(width: 4),
        Text(hearing ? tr('HEARING') : tr('EYES AND SEEING'),
            style: Theme.of(context).textTheme.labelMedium?.copyWith(color: context.hc.plum900)),
      ]),
    );
  }
}
