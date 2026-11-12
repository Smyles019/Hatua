import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/theme.dart';
import '../../widgets/child_avatar.dart';
import '../../widgets/common.dart';
import '../../widgets/nav_shell.dart';
import '../profile_screen.dart';
import 'add_child_screen.dart';
import 'check_screen.dart';
import 'children_tab.dart';
import 'history_tab.dart';
import 'home_tab.dart';
import '../../i18n/strings.dart';

class CaregiverShell extends StatelessWidget {
  const CaregiverShell({super.key});

  @override
  Widget build(BuildContext context) {
    return NavShell(
      tabs: [
        NavTab(tr('Home'), Icons.home_outlined, (_) => CaregiverHomeTab()),
        NavTab(tr('Children'), Icons.child_care_rounded, (_) => ChildrenTab()),
        NavTab(tr('History'), Icons.history_rounded, (_) => HistoryTab()),
        NavTab(tr('Profile'), Icons.person_outline_rounded, (_) => ProfileScreen()),
      ],
      centreLabel: tr('Start check'),
      centreIcon: Icons.add_rounded,
      onCentre: startCheck,
    );
  }
}

/// Centre button: pick which child to check (or add one first), then open the check.
Future<void> startCheck(BuildContext context, {Child? child}) async {
  final api = context.read<Session>().api;
  if (child != null) {
    await openCheck(context, child);
    return;
  }
  List<Child> children;
  try {
    final data = await api.get('/children') as List;
    children = data.map((c) => Child.fromJson(c as Map<String, dynamic>)).toList();
  } catch (e) {
    if (context.mounted) showError(context, e);
    return;
  }
  if (!context.mounted) return;
  if (children.isEmpty) {
    showMessage(context, tr('Add a child first, then start a check.'));
    await Navigator.of(context)
        .push(MaterialPageRoute(builder: (_) => const AddChildScreen()));
    return;
  }
  if (children.length == 1) {
    await openCheck(context, children.first);
    return;
  }
  final picked = await showModalBottomSheet<Child>(
    context: context,
    showDragHandle: true,
    builder: (ctx) => SafeArea(
      child: ListView(shrinkWrap: true, padding: const EdgeInsets.all(Space.s4), children: [
        Text(tr('Which child are you checking?'), style: Theme.of(ctx).textTheme.titleLarge),
        const SizedBox(height: Space.s3),
        for (final c in children)
          Padding(
            padding: const EdgeInsets.only(bottom: Space.s2),
            child: HatuaCard(
              onTap: () => Navigator.of(ctx).pop(c),
              child: Row(children: [
                ChildAvatar(childId: c.childId, avatarId: c.avatarId),
                const SizedBox(width: Space.s3),
                Expanded(
                    child: Text(c.firstName, style: Theme.of(ctx).textTheme.titleMedium)),
                Text(ageLabel(c.ageMonths), style: Theme.of(ctx).textTheme.bodySmall),
              ]),
            ),
          ),
      ]),
    ),
  );
  if (picked != null && context.mounted) await openCheck(context, picked);
}

Future<void> openCheck(BuildContext context, Child child) =>
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => CheckScreen(child: child)));
