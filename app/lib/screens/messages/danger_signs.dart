import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../i18n/strings.dart';

/// "When to return immediately" from the MOH Mother and Child Health Handbook, in plain
/// words. Shown before a caregiver sends a question to their CHW, so an emergency goes
/// to a health facility and not into a message queue.
List<String> get dangerSigns => [
      tr('Cannot drink or breastfeed, or is feeding very poorly'),
      tr('Has fast or difficult breathing'),
      tr('Has a fever, or feels unusually hot or unusually cold'),
      tr('Has fits (convulsions)'),
      tr('Has blood in the stool'),
      tr('Is getting sicker, very sleepy or hard to wake'),
      tr('A young baby whose palms, soles or eyes look yellow'),
    ];

/// Returns true when the caregiver says none of the signs apply and wants to send.
/// With [readOnly] the sheet only shows the list.
Future<bool?> showDangerSigns(BuildContext context, {bool readOnly = false}) {
  return showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (ctx) {
      final t = Theme.of(ctx).textTheme;
      return SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(Space.s4, 0, Space.s4, Space.s4),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(children: [
                Icon(Icons.emergency_outlined, color: ctx.hc.riskHigh),
                const SizedBox(width: Space.s2),
                Expanded(
                    child: Text(tr('Go to a health facility now if your child:'),
                        style: t.titleLarge)),
              ]),
              const SizedBox(height: Space.s3),
              for (final sign in dangerSigns)
                Padding(
                  padding: const EdgeInsets.only(bottom: Space.s2),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('•  ', style: t.bodyMedium),
                    Expanded(child: Text(sign, style: t.bodyMedium)),
                  ]),
                ),
              const SizedBox(height: Space.s2),
              Text(
                tr('Do not wait for a reply here. Messages are answered when your health worker is free, which can take a day or more.'),
                style: t.bodySmall,
              ),
              const SizedBox(height: Space.s4),
              if (readOnly)
                FilledButton(
                    onPressed: () => Navigator.pop(ctx), child: Text(tr('Close')))
              else ...[
                FilledButton(
                  onPressed: () => Navigator.pop(ctx, true),
                  child: Text(tr('None of these. Send my question')),
                ),
                const SizedBox(height: Space.s2),
                TextButton(
                  onPressed: () => Navigator.pop(ctx, false),
                  child: Text(tr('Go back')),
                ),
              ],
            ],
          ),
        ),
      );
    },
  );
}
