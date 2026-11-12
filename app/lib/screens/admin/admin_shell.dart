import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../widgets/nav_shell.dart';
import '../profile_screen.dart';
import 'summary_screen.dart';
import 'users_screen.dart';

/// Administrators get a plain working layout: no blob header, no playful layer.
class AdminShell extends StatelessWidget {
  const AdminShell({super.key});

  @override
  Widget build(BuildContext context) {
    return NavShell(tabs: [
      NavTab('Users', Icons.manage_accounts_outlined, (_) => UsersScreen()),
      NavTab('Summary', Icons.bar_chart_rounded, (_) => SummaryScreen()),
      NavTab('Profile', Icons.person_outline_rounded, (_) => ProfileScreen()),
    ]);
  }
}

/// Plum app bar used on admin screens.
PreferredSizeWidget adminAppBar(BuildContext context, String title, {List<Widget>? actions}) =>
    AppBar(
      title: Text(title),
      backgroundColor: context.hc.header,
      foregroundColor: context.hc.onHeader,
      titleTextStyle:
          Theme.of(context).textTheme.titleMedium?.copyWith(color: context.hc.onHeader),
      actions: actions,
    );
