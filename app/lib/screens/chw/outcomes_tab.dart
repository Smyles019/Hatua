import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/risk_chip.dart';
import 'case_review_screen.dart';
import 'chw_data.dart';

/// Cases this CHW has already logged an outcome for. Tapping one allows a correction.
class OutcomesTab extends StatefulWidget {
  const OutcomesTab({super.key});

  @override
  State<OutcomesTab> createState() => _OutcomesTabState();
}

class _OutcomesTabState extends State<OutcomesTab> {
  Future<List<Assessment>>? _future;
  int _version = -1;

  void _load() {
    final s = context.read<Session>();
    _version = s.dataVersion;
    _future = loadCases(s.api, includeReviewed: true).then((all) => all
        .where((a) => a.chwOutcome != null)
        .toList()
      ..sort((a, b) => b.reviewedAt!.compareTo(a.reviewedAt!)));
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (_future == null || _version != s.dataVersion) _load();
    final t = Theme.of(context).textTheme;
    final df = DateFormat('d MMM yyyy');
    return Scaffold(
      appBar: AppBar(title: Text('Outcomes')),
      body: RefreshIndicator(
        color: context.hc.plum700,
        onRefresh: () async {
          setState(_load);
          await _future;
        },
        child: ListView(padding: EdgeInsets.all(Space.s4), children: [
          AsyncView<List<Assessment>>(
            future: _future!,
            onRetry: () => setState(_load),
            builder: (context, done) => Column(children: [
              if (done.isEmpty)
                EmptyPanel(
                  title: 'No outcomes yet',
                  message: 'Outcomes you log for flagged children appear here.',
                  icon: Icons.fact_check_outlined,
                ),
              for (final a in done) ...[
                HatuaCard(
                  onTap: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => CaseReviewScreen(assessment: a))),
                  child: Row(children: [
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(a.childName, style: t.titleMedium),
                        Text(outcomeLabels[a.chwOutcome] ?? '', style: t.bodyMedium),
                        Text('Logged ${df.format(a.reviewedAt!)}', style: t.bodySmall),
                      ]),
                    ),
                    RiskChip.risk(a.riskLevel, audience: Audience.chw),
                  ]),
                ),
                SizedBox(height: Space.s2),
              ],
            ]),
          ),
        ]),
      ),
    );
  }
}
