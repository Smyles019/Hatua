import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../i18n/strings.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/child_avatar.dart';
import '../../widgets/common.dart';
import '../../widgets/record_charts.dart';
import '../caregiver/child_profile_screen.dart';
import '../messages/thread_screen.dart';

/// A child of one of the CHW's families with vaccines more than 4 weeks overdue (backend
/// GET /chw/missed-doses: only doses that fell due after the child joined Hatua).
class MissedChild {
  MissedChild(this.childId, this.childName, this.avatarId, this.ageMonths, this.caregiverId,
      this.caregiverName, this.caregiverPhone, this.doses, this.mostDaysOverdue);
  final String childId, childName;
  final String? avatarId;
  final int ageMonths;
  final String caregiverId, caregiverName;
  final String? caregiverPhone;
  final List<(String, int)> doses; // name, days overdue
  final int mostDaysOverdue;

  factory MissedChild.fromJson(Map<String, dynamic> j) {
    final cg = j['caregiver'] as Map<String, dynamic>;
    return MissedChild(
      j['child_id'] as String,
      j['child_name'] as String,
      j['child_avatar_id'] as String?,
      j['age_months'] as int,
      cg['user_id'] as String,
      cg['full_name'] as String,
      cg['phone_number'] as String?,
      [
        for (final d in (j['doses'] as List).cast<Map<String, dynamic>>())
          (d['name'] as String, d['days_overdue'] as int)
      ],
      j['most_days_overdue'] as int,
    );
  }
}

Future<List<MissedChild>> loadMissed(Session s) async {
  final data = await s.api.get('/chw/missed-doses') as List;
  return data.map((m) => MissedChild.fromJson(m as Map<String, dynamic>)).toList();
}

class MissedDosesScreen extends StatefulWidget {
  const MissedDosesScreen({super.key});

  @override
  State<MissedDosesScreen> createState() => _MissedDosesScreenState();
}

class _MissedDosesScreenState extends State<MissedDosesScreen> {
  late Future<List<MissedChild>> _future = loadMissed(context.read<Session>());

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('Missed vaccines'))),
      body: RefreshIndicator(
        onRefresh: () async {
          setState(() => _future = loadMissed(context.read<Session>()));
          await _future;
        },
        child: AsyncView<List<MissedChild>>(
          future: _future,
          onRetry: () => setState(() => _future = loadMissed(context.read<Session>())),
          builder: (context, list) => list.isEmpty
              ? ListView(padding: const EdgeInsets.all(Space.s4), children: [
                  EmptyPanel(
                    title: tr('No missed vaccines'),
                    message: tr('Every child in your families is up to date with the doses due since they joined Hatua.'),
                    icon: Icons.verified_outlined,
                  ),
                ])
              : _list(context, list),
        ),
      ),
    );
  }

  Widget _list(BuildContext context, List<MissedChild> list) {
    final t = Theme.of(context).textTheme;
    // How many children are missing each vaccine, for the bar graph.
    final byVaccine = <String, int>{};
    for (final c in list) {
      for (final (name, _) in c.doses) {
        byVaccine[name] = (byVaccine[name] ?? 0) + 1;
      }
    }
    final bars = byVaccine.entries.toList()..sort((a, b) => b.value.compareTo(a.value));
    final most = bars.isEmpty ? 1 : bars.first.value;

    return ListView(padding: const EdgeInsets.all(Space.s4), children: [
      Text(
          tr('Doses more than 4 weeks late, due since the child joined Hatua. Check the booklet with the caregiver: the dose may have been given but not ticked.'),
          style: t.bodySmall),
      const SizedBox(height: Space.s3),
      HatuaCard(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('Children missing each vaccine'), style: t.titleMedium),
          const SizedBox(height: Space.s2),
          for (final b in bars.take(8))
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(children: [
                SizedBox(width: 140, child: Text(b.key, style: t.bodySmall)),
                Expanded(
                  child: LayoutBuilder(
                    builder: (context, box) => Row(children: [
                      Container(
                        width: box.maxWidth * 0.85 * b.value / most,
                        height: 16,
                        decoration: BoxDecoration(
                            color: context.hc.riskMedium,
                            borderRadius: BorderRadius.circular(4)),
                      ),
                      const SizedBox(width: 6),
                      Text('${b.value}', style: t.labelLarge),
                    ]),
                  ),
                ),
              ]),
            ),
        ]),
      ),
      for (final c in list) ...[
        const SizedBox(height: Space.s3),
        HatuaCard(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              ChildAvatar(childId: c.childId, avatarId: c.avatarId, size: 44),
              const SizedBox(width: Space.s3),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${c.childName}, ${ageLabel(c.ageMonths)}', style: t.titleMedium),
                  Text(c.caregiverName, style: t.bodySmall),
                ]),
              ),
            ]),
            const SizedBox(height: Space.s2),
            for (final (name, days) in c.doses)
              Padding(
                padding: const EdgeInsets.only(top: Space.s1),
                child: Row(children: [
                  const DoseMark('overdue', size: 16),
                  const SizedBox(width: Space.s2),
                  Expanded(child: Text(name, style: t.bodyMedium)),
                  Text(tr('{n} weeks late', {'n': days ~/ 7}), style: t.bodySmall),
                ]),
              ),
            const SizedBox(height: Space.s2),
            Wrap(spacing: Space.s2, children: [
              if (c.caregiverPhone != null)
                OutlinedButton.icon(
                  onPressed: () => launchUrl(Uri.parse('tel:${c.caregiverPhone}')),
                  icon: const Icon(Icons.call_outlined),
                  label: Text(tr('Call')),
                ),
              OutlinedButton.icon(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) =>
                        ThreadScreen(caregiverId: c.caregiverId, caregiverName: c.caregiverName))),
                icon: const Icon(Icons.chat_bubble_outline_rounded),
                label: Text(tr('Message')),
              ),
              TextButton(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => ChildProfileScreen(childId: c.childId))),
                child: Text(tr('Open record')),
              ),
            ]),
          ]),
        ),
      ],
      const SizedBox(height: Space.s6),
    ]);
  }
}
