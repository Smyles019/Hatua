import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import 'admin_shell.dart';
import '../../i18n/strings.dart';

/// Usage summary over a date range (GET /admin/summary). All figures come from the API.
class SummaryScreen extends StatefulWidget {
  const SummaryScreen({super.key});

  @override
  State<SummaryScreen> createState() => _SummaryScreenState();
}

class _SummaryScreenState extends State<SummaryScreen> {
  Future<UsageSummary>? _future;
  int _version = -1;
  DateTimeRange? _range;
  final _fmt = DateFormat('yyyy-MM-dd');

  void _load() {
    final s = context.read<Session>();
    _version = s.dataVersion;
    _future = s.api.get('/admin/summary', {
      'start': _range == null ? null : _fmt.format(_range!.start),
      'end': _range == null ? null : _fmt.format(_range!.end),
    }).then((d) => UsageSummary(d as Map<String, dynamic>));
  }

  Future<void> _pickRange() async {
    final now = DateTime.now();
    final picked = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2025),
      lastDate: now,
      initialDateRange: _range ?? DateTimeRange(start: now.subtract(Duration(days: 30)), end: now),
    );
    if (picked != null) {
      setState(() {
        _range = picked;
        _load();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (_future == null || _version != s.dataVersion) _load();
    final t = Theme.of(context).textTheme;
    final df = DateFormat('d MMM yyyy');
    return Scaffold(
      appBar: adminAppBar(context, tr('Usage summary')),
      body: RefreshIndicator(
        color: context.hc.plum700,
        onRefresh: () async {
          setState(_load);
          await _future;
        },
        child: ListView(padding: EdgeInsets.all(Space.s4), children: [
          Row(children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _pickRange,
                icon: Icon(Icons.date_range_rounded),
                label: Text(_range == null
                    ? tr('All time')
                    : '${df.format(_range!.start)} to ${df.format(_range!.end)}'),
              ),
            ),
            if (_range != null)
              IconButton(
                tooltip: tr('Show all time'),
                onPressed: () => setState(() {
                  _range = null;
                  _load();
                }),
                icon: Icon(Icons.close_rounded),
              ),
          ]),
          SizedBox(height: Space.s4),
          AsyncView<UsageSummary>(
            future: _future!,
            onRetry: () => setState(_load),
            builder: (context, u) => Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: NeverScrollableScrollPhysics(),
                mainAxisSpacing: Space.s3,
                crossAxisSpacing: Space.s3,
                childAspectRatio: 1.6,
                children: [
                  _stat(tr('Assessments completed'), u.assessments),
                  _stat(tr('Flagged for CHW'), u.flagged),
                  _stat(tr('Referred to facility'), u.outcomes['refer_to_facility'] ?? 0),
                  _stat(tr('Reviewed, not concerning'), u.outcomes['reviewed_not_concerning'] ?? 0),
                  _stat(tr('Could not reach'), u.outcomes['unreachable'] ?? 0),
                  _stat(tr('Awaiting review now'), u.awaiting),
                ],
              ),
              SizedBox(height: Space.s6),
              Text(tr('Assessments by risk level'), style: t.titleLarge),
              SizedBox(height: Space.s3),
              _Bars(values: {
                'Low': u.byRisk['low'] ?? 0,
                'Medium': u.byRisk['medium'] ?? 0,
                'High': u.byRisk['high'] ?? 0,
              }),
              SizedBox(height: Space.s6),
              Text(tr('Active accounts'), style: t.titleLarge),
              SizedBox(height: Space.s2),
              Text(tr('Caregivers: {caregivers}  ·  CHWs: {chws}  ·  Admins: {admins}', {'caregivers': u.users['caregiver'] ?? 0, 'chws': u.users['chw'] ?? 0, 'admins': u.users['admin'] ?? 0}), style: t.bodyMedium),
              Text(tr('Children registered: {children}', {'children': u.children}), style: t.bodyMedium),
              Text(tr('Unusual-answer flags: {anomalies}', {'anomalies': u.anomalies}), style: t.bodyMedium),
            ]),
          ),
        ]),
      ),
    );
  }

  Widget _stat(String label, int value) {
    final t = Theme.of(context).textTheme;
    return HatuaCard(
      padding: EdgeInsets.all(Space.s3),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
        Text('$value', style: t.headlineSmall),
        Text(label, style: t.bodySmall?.copyWith(color: context.hc.plum900), maxLines: 2),
      ]),
    );
  }
}

/// Horizontal plum bars with the count written beside each, so no value relies on
/// reading bar length alone.
class _Bars extends StatelessWidget {
  const _Bars({required this.values});
  final Map<String, int> values;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final max = values.values.fold<int>(0, (a, b) => a > b ? a : b);
    return HatuaCard(
      child: Column(children: [
        for (final e in values.entries)
          Padding(
            padding: EdgeInsets.symmetric(vertical: Space.s1),
            child: Row(children: [
              SizedBox(width: 72, child: Text(e.key, style: t.bodyMedium)),
              Expanded(
                child: LayoutBuilder(
                  builder: (_, c) => Align(
                    alignment: Alignment.centerLeft,
                    child: Container(
                      height: 20,
                      width: max == 0 ? 0 : c.maxWidth * e.value / max,
                      decoration: BoxDecoration(
                          color: context.hc.plum700,
                          borderRadius: BorderRadius.circular(Radii.sm)),
                    ),
                  ),
                ),
              ),
              SizedBox(
                  width: 48,
                  child: Text('${e.value}', style: t.labelLarge, textAlign: TextAlign.end)),
            ]),
          ),
      ]),
    );
  }
}
