import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../i18n/strings.dart';
import '../state/session.dart';
import '../theme/colors.dart';
import '../theme/theme.dart';

/// A strip at the top of the caregiver and CHW homes while the phone has no connection
/// and the screens show what was saved on the phone. Says how old that is and how many
/// changes are waiting to be sent. Hidden while online.
class OfflineBanner extends StatelessWidget {
  const OfflineBanner({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    return ValueListenableBuilder<DateTime?>(
      valueListenable: session.api.savedDataFrom,
      builder: (context, savedAt, _) {
        if (savedAt == null) return const SizedBox.shrink();
        final now = DateTime.now();
        final sameDay = savedAt.year == now.year && savedAt.month == now.month && savedAt.day == now.day;
        final when = DateFormat(sameDay ? 'HH:mm' : 'd MMM, HH:mm').format(savedAt);
        final waiting = session.waitingCount;
        final t = Theme.of(context).textTheme;
        return Material(
          color: context.hc.sun100,
          child: SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: Space.s4, vertical: Space.s2),
              child: Row(children: [
                Icon(Icons.cloud_off_rounded, size: 20, color: context.hc.plum900),
                const SizedBox(width: Space.s2),
                Expanded(
                  child: Text(
                    [
                      tr('Offline. Showing what was saved at {when}.', {'when': when}),
                      if (waiting == 1) tr('1 change waiting to send.'),
                      if (waiting > 1) tr('{n} changes waiting to send.', {'n': waiting}),
                    ].join(' '),
                    style: t.bodySmall?.copyWith(color: context.hc.plum900),
                  ),
                ),
              ]),
            ),
          ),
        );
      },
    );
  }
}
