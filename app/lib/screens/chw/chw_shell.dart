import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../state/session.dart';
import '../../widgets/nav_shell.dart';
import '../profile_screen.dart';
import 'caregivers_tab.dart';
import 'chw_data.dart';
import 'chw_home_tab.dart';
import 'flagged_screen.dart';
import 'outcomes_tab.dart';
import '../../i18n/strings.dart';

class ChwShell extends StatefulWidget {
  const ChwShell({super.key});

  @override
  State<ChwShell> createState() => _ChwShellState();
}

class _ChwShellState extends State<ChwShell> {
  int? _open;
  int _version = -1;

  Future<void> _count() async {
    final s = context.read<Session>();
    _version = s.dataVersion;
    try {
      final cases = await loadCases(s.api);
      if (mounted) setState(() => _open = cases.length);
    } catch (_) {
      // The badge is a convenience; the Flagged screen shows the real error.
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = context.select<Session, int>((s) => s.dataVersion);
    if (v != _version) {
      _version = v;
      WidgetsBinding.instance.addPostFrameCallback((_) => _count());
    }
    return NavShell(
      tabs: [
        NavTab(tr('Home'), Icons.home_outlined, (_) => ChwHomeTab()),
        NavTab(tr('Caregivers'), Icons.people_outline_rounded, (_) => CaregiversTab()),
        NavTab(tr('Outcomes'), Icons.fact_check_outlined, (_) => OutcomesTab()),
        NavTab(tr('Profile'), Icons.person_outline_rounded, (_) => ProfileScreen()),
      ],
      centreLabel: tr('Flagged'),
      centreIcon: Icons.flag_outlined,
      centreBadge: _open,
      onCentre: (ctx) => Navigator.of(ctx)
          .push(MaterialPageRoute(builder: (_) => FlaggedScreen())),
    );
  }
}
