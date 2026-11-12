import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/risk_chip.dart';
import 'caregiver_data.dart';
import 'result_screen.dart';
import '../../i18n/strings.dart';

/// Every check for every child as a timeline, newest first, filterable by child.
class HistoryTab extends StatefulWidget {
  const HistoryTab({super.key});

  @override
  State<HistoryTab> createState() => _HistoryTabState();
}

class _HistoryTabState extends State<HistoryTab> {
  Future<List<ChildWithChecks>>? _future;
  int _version = -1;
  String? _childFilter;

  void _load() {
    final s = context.read<Session>();
    _version = s.dataVersion;
    _future = loadChildrenWithChecks(s.api);
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (_future == null || _version != s.dataVersion) _load();
    return Scaffold(
      appBar: AppBar(title: Text(tr('History'))),
      body: AsyncView<List<ChildWithChecks>>(
        future: _future!,
        onRetry: () => setState(_load),
        builder: (context, items) => _body(context, items),
      ),
    );
  }

  Widget _body(BuildContext context, List<ChildWithChecks> items) {
    final t = Theme.of(context).textTheme;
    final df = DateFormat('d MMM yyyy');
    final checks = <Assessment>[
      for (final i in items)
        if (_childFilter == null || _childFilter == i.child.childId) ...i.checks,
    ]..sort((a, b) => b.submittedAt.compareTo(a.submittedAt));

    return ListView(padding: EdgeInsets.all(Space.s4), children: [
      if (items.length > 1)
        Wrap(spacing: Space.s2, runSpacing: Space.s2, children: [
          _filter(tr('All'), null),
          for (final i in items) _filter(i.child.firstName, i.child.childId),
        ]),
      SizedBox(height: Space.s4),
      if (checks.isEmpty)
        EmptyPanel(
          title: tr('No checks yet'),
          message: tr('Your checks will appear here so you can see how your child grows.'),
          icon: Icons.history_rounded,
        ),
      for (var k = 0; k < checks.length; k++)
        IntrinsicHeight(
          child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            SizedBox(
              width: 24,
              child: Column(children: [
                Container(
                  width: 14,
                  height: 14,
                  margin: EdgeInsets.only(top: 22),
                  decoration: BoxDecoration(
                      color: context.hc.plum700, shape: BoxShape.circle),
                ),
                if (k < checks.length - 1)
                  Expanded(child: Container(width: 2, color: context.hc.plum200)),
              ]),
            ),
            SizedBox(width: Space.s2),
            Expanded(
              child: Padding(
                padding: EdgeInsets.only(bottom: Space.s3),
                child: HatuaCard(
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => ResultScreen(assessment: checks[k]))),
                  child: Row(children: [
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(checks[k].childName, style: t.titleMedium),
                        Text('${df.format(checks[k].submittedAt)} · '
                            'at ${ageLabel(checks[k].ageMonths)}',
                            style: t.bodySmall),
                        if (checks[k].caregiverMessage != null)
                          Padding(
                            padding: EdgeInsets.only(top: Space.s1),
                            child: Text(tr('Health worker reviewed'), style: t.bodySmall),
                          ),
                      ]),
                    ),
                    RiskChip.risk(checks[k].riskLevel),
                  ]),
                ),
              ),
            ),
          ]),
        ),
    ]);
  }

  Widget _filter(String label, String? id) {
    final on = _childFilter == id;
    return ChoiceChip(
      label: Text(label),
      selected: on,
      showCheckmark: false,
      selectedColor: context.hc.plum700,
      backgroundColor: context.hc.plum100,
      labelStyle: Theme.of(context)
          .textTheme
          .labelLarge
          ?.copyWith(color: on ? context.hc.onPrimary : context.hc.plum900),
      shape: StadiumBorder(side: BorderSide(color: context.hc.plum200)),
      onSelected: (_) => setState(() => _childFilter = id),
    );
  }
}
