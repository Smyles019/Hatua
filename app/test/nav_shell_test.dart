import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hatua/widgets/nav_shell.dart';

NavTab _tab(String name, IconData icon) => NavTab(name, icon, (_) => Text('$name body'));

void main() {
  testWidgets('tapping a tab shows its body; the centre action opens without selecting',
      (tester) async {
    var centreTaps = 0;
    await tester.pumpWidget(MaterialApp(
      home: NavShell(
        tabs: [
          _tab('Home', Icons.home_outlined),
          _tab('Children', Icons.child_care_rounded),
          _tab('History', Icons.history_rounded),
          _tab('Profile', Icons.person_outline_rounded),
        ],
        centreLabel: 'Start check',
        centreIcon: Icons.add_rounded,
        onCentre: (_) => centreTaps++,
      ),
    ));

    final state = tester.state<NavShellState>(find.byType(NavShell));
    expect(state.index, 0);

    await tester.tap(find.text('History'));
    await tester.pumpAndSettle();
    expect(state.index, 2);
    expect(find.text('History body'), findsOneWidget);

    await tester.tap(find.text('Start check'));
    await tester.pumpAndSettle();
    expect(centreTaps, 1);
    expect(state.index, 2);
  });

  testWidgets('works without a centre action', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: NavShell(tabs: [
        _tab('Users', Icons.manage_accounts_outlined),
        _tab('Summary', Icons.bar_chart_rounded),
        _tab('Profile', Icons.person_outline_rounded),
      ]),
    ));

    await tester.tap(find.text('Profile'));
    await tester.pumpAndSettle();
    expect(tester.state<NavShellState>(find.byType(NavShell)).index, 2);
    expect(find.text('Profile body'), findsOneWidget);
  });
}
