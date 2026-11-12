import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../i18n/strings.dart';

enum Audience { caregiver, chw }

enum RiskChipKind { risk, domain, anomaly }

/// Risk shown with a word, an icon shape and a colour, so no single channel carries it.
class RiskChip extends StatelessWidget {
  const RiskChip.risk(this.level, {super.key, this.audience = Audience.caregiver})
      : kind = RiskChipKind.risk;
  const RiskChip.domain(bool needsSupport, {super.key})
      : level = needsSupport ? 'needs_support' : 'on_track',
        audience = Audience.caregiver,
        kind = RiskChipKind.domain;
  const RiskChip.anomaly({super.key})
      : level = 'anomaly',
        audience = Audience.chw,
        kind = RiskChipKind.anomaly;

  final String level;
  final Audience audience;
  final RiskChipKind kind;

  @override
  Widget build(BuildContext context) {
    final spec = _spec(context.hc);
    return Container(
      constraints: const BoxConstraints(minHeight: 32),
      padding: const EdgeInsets.fromLTRB(8, 4, 12, 4),
      decoration: BoxDecoration(
        color: spec.fill,
        borderRadius: BorderRadius.circular(999),
        border: spec.border,
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(spec.icon, size: 18, color: spec.text),
        const SizedBox(width: 6),
        Text(spec.label,
            style: Theme.of(context)
                .textTheme
                .labelLarge
                ?.copyWith(fontSize: 15, color: spec.text)),
      ]),
    );
  }

  _ChipSpec _spec(HatuaPalette c) {
    final caregiver = audience == Audience.caregiver;
    final low = _ChipSpec(caregiver ? tr('On track') : tr('Low'), c.riskLowBg,
        Border.all(color: c.riskLow, width: 2), Icons.check_circle_outline_rounded, c.riskLowText);
    final medium = _ChipSpec(caregiver ? tr('Watch') : tr('Medium'), c.riskMedium, null,
        Icons.change_history_rounded, c.onBright);
    switch (kind) {
      case RiskChipKind.anomaly:
        return _ChipSpec(tr('Answers look unusual'), c.surfaceCard,
            Border.all(color: c.plum700, width: 2), Icons.help_outline_rounded, c.plum900);
      case RiskChipKind.domain:
        return level == 'needs_support'
            ? _ChipSpec(tr('Needs support'), c.riskMedium, null, Icons.change_history_rounded,
                c.onBright)
            : _ChipSpec(tr('On track'), low.fill, low.border, low.icon, low.text);
      case RiskChipKind.risk:
        return switch (level) {
          'high' => _ChipSpec(caregiver ? tr('Check soon') : tr('High'), c.riskHigh, null,
              Icons.warning_amber_rounded, c.onBright),
          'medium' => medium,
          _ => low,
        };
    }
  }
}

class _ChipSpec {
  _ChipSpec(this.label, this.fill, this.border, this.icon, this.text);
  final String label;
  final Color fill;
  final BoxBorder? border;
  final IconData icon;
  final Color text;
}

/// Card background tint for a risk level (plain card for low).
Color riskTint(BuildContext context, String level) => switch (level) {
      'high' => context.hc.riskHighBg,
      'medium' => context.hc.riskMediumBg,
      _ => context.hc.surfaceCard,
    };
