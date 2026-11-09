import 'package:flutter/material.dart';

import '../theme/colors.dart';

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
          'Language', c.sun500, c.sun100, Icons.chat_bubble_outline_rounded),
      'cognitive' => DomainStyle(
          'Thinking and learning', c.blush500, c.blush100, Icons.lightbulb_outline_rounded),
      'social_emotional' => DomainStyle(
          'Social and emotional', c.domainSocial, c.plum100, Icons.people_outline_rounded),
      _ => DomainStyle('Movement', c.sky500, c.sky100, Icons.directions_walk_rounded),
    };
  }

  /// Which domain a question belongs to (hatua_ml/models/explain.py DOMAINS).
  /// Under-24-month WHO questions are all movement.
  static String domainOfItem(String item) {
    if (item.startsWith('who_')) return 'motor';
    final n = int.tryParse(item.replaceAll(RegExp(r'[^0-9]'), '')) ?? 0;
    if (n >= 21 && n <= 24) return 'motor';
    if (n >= 25 && n <= 29) return 'language';
    if (n >= 30 && n <= 35) return 'cognitive';
    return 'social_emotional';
  }
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
