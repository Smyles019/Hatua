import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import 'chw_data.dart';
import 'link_caregiver_screen.dart';

/// The CHW's part of the profile: their caseload, the outcomes they have logged, and
/// a shortcut to link a caregiver. Built from /chw/caregivers and /chw/cases.
class ChwProfileSection extends StatefulWidget {
  const ChwProfileSection({super.key});

  @override
  State<ChwProfileSection> createState() => _ChwProfileSectionState();
}

class _ChwWork {
  _ChwWork(this.caregivers, this.cases);
  final List<LinkedCaregiver> caregivers;
  final List<Assessment> cases; // open and reviewed

  int get children => caregivers.fold(0, (n, c) => n + c.children);
  List<Assessment> get open => cases.where((a) => a.chwOutcome == null).toList();
  List<Assessment> get logged => cases.where((a) => a.chwOutcome != null).toList();

  int outcomes(String key) => logged.where((a) => a.chwOutcome == key).length;

  DateTime? get lastLogged => logged.isEmpty
      ? null
      : logged.map((a) => a.reviewedAt!).reduce((a, b) => a.isAfter(b) ? a : b);

  int get loggedLast30Days {
    final since = DateTime.now().subtract(const Duration(days: 30));
    return logged.where((a) => a.reviewedAt!.isAfter(since)).length;
  }
}

class _ChwProfileSectionState extends State<ChwProfileSection> {
  Future<_ChwWork>? _future;
  int _version = -1;

  void _load() {
    final s = context.read<Session>();
    _version = s.dataVersion;
    _future = () async {
      final r = await Future.wait([
        loadCaregivers(s.api),
        loadCases(s.api, includeReviewed: true),
      ]);
      return _ChwWork(r[0] as List<LinkedCaregiver>, r[1] as List<Assessment>);
    }();
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (_future == null || _version != s.dataVersion) _load();
    return AsyncView<_ChwWork>(
      future: _future!,
      onRetry: () => setState(_load),
      builder: (context, w) => _body(context, w),
    );
  }

  Widget _body(BuildContext context, _ChwWork w) {
    final t = Theme.of(context).textTheme;
    final c = context.hc;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      GridView.count(
        crossAxisCount: 2,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: Space.s3,
        crossAxisSpacing: Space.s3,
        childAspectRatio: 1.7,
        children: [
          _Stat(Icons.people_outline_rounded, '${w.caregivers.length}', 'Caregivers linked',
              c.sky100),
          _Stat(Icons.child_care_rounded, '${w.children}', 'Children', c.sun100),
          _Stat(Icons.flag_outlined, '${w.open.length}', 'Open cases', c.riskMediumBg),
          _Stat(Icons.fact_check_outlined, '${w.logged.length}', 'Outcomes logged', c.plum100),
        ],
      ),
      const SizedBox(height: Space.s6),
      Text('Your outcomes', style: t.titleLarge),
      const SizedBox(height: Space.s1),
      Text(
        w.lastLogged == null
            ? 'No outcomes logged yet.'
            : '${w.loggedLast30Days} in the last 30 days · last on '
                '${DateFormat('d MMM yyyy').format(w.lastLogged!)}',
        style: t.bodySmall,
      ),
      const SizedBox(height: Space.s3),
      HatuaCard(
        child: Column(children: [
          for (final (key, color) in [
            ('refer_to_facility', c.riskHigh),
            ('reviewed_not_concerning', c.riskLow),
            ('unreachable', c.plum500),
          ]) ...[
            _OutcomeBar(
              label: outcomeLabels[key]!,
              count: w.outcomes(key),
              total: w.logged.length,
              color: color,
            ),
            if (key != 'unreachable') const SizedBox(height: Space.s3),
          ],
        ]),
      ),
      const SizedBox(height: Space.s4),
      HatuaCard(
        color: c.sun100,
        onTap: () => Navigator.of(context)
            .push(MaterialPageRoute(builder: (_) => const LinkCaregiverScreen())),
        child: Row(children: [
          Icon(Icons.person_add_alt_rounded, color: c.onBright),
          const SizedBox(width: Space.s3),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('Link a caregiver', style: t.labelLarge?.copyWith(color: c.onBright)),
              Text('Enrol a new caregiver or link one by phone number.',
                  style: t.bodySmall?.copyWith(color: c.onBright)),
            ]),
          ),
          Icon(Icons.chevron_right_rounded, color: c.onBright),
        ]),
      ),
    ]);
  }
}

class _Stat extends StatelessWidget {
  const _Stat(this.icon, this.value, this.label, this.color);
  final IconData icon;
  final String value;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final on = context.hc.onBright;
    return HatuaCard(
      color: color,
      padding: const EdgeInsets.all(Space.s3),
      child: Row(children: [
        Icon(icon, color: on),
        const SizedBox(width: Space.s3),
        Expanded(
          child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(value, style: t.headlineSmall?.copyWith(color: on)),
                Text(label, style: t.bodySmall?.copyWith(color: on), maxLines: 2),
              ]),
        ),
      ]),
    );
  }
}

class _OutcomeBar extends StatelessWidget {
  const _OutcomeBar(
      {required this.label, required this.count, required this.total, required this.color});
  final String label;
  final int count;
  final int total;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Semantics(
      label: '$label: $count',
      excludeSemantics: true,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(label, style: t.bodyMedium)),
          Text('$count', style: t.labelLarge),
        ]),
        const SizedBox(height: Space.s1),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            value: total == 0 ? 0 : count / total,
            minHeight: 8,
            backgroundColor: context.hc.plum100,
            color: color,
          ),
        ),
      ]),
    );
  }
}
