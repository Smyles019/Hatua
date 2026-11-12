import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/child_avatar.dart';
import '../../widgets/common.dart';
import '../../widgets/risk_chip.dart';
import '../../widgets/sprout.dart';
import 'add_child_screen.dart';
import 'caregiver_data.dart';
import 'caregiver_shell.dart';
import 'child_profile_screen.dart';
import 'play_ideas.dart';
import 'result_screen.dart';

/// Caregiver home: a child switcher, then the selected child's latest result, next
/// check, quick tools and a play idea for their age.
class CaregiverHomeTab extends StatefulWidget {
  const CaregiverHomeTab({super.key});

  @override
  State<CaregiverHomeTab> createState() => _CaregiverHomeTabState();
}

class _CaregiverHomeTabState extends State<CaregiverHomeTab> {
  Future<List<ChildWithChecks>>? _future;
  int _version = -1;
  String? _selectedId;

  void _load() {
    final session = context.read<Session>();
    _version = session.dataVersion;
    _future = loadChildrenWithChecks(session.api);
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    if (_future == null || _version != session.dataVersion) _load();
    final name = session.user?.firstName ?? '';

    return RefreshIndicator(
      color: context.hc.plum700,
      onRefresh: () async {
        setState(_load);
        await _future;
      },
      child: ListView(padding: EdgeInsets.zero, children: [
        BlobHeader(
          title: 'Hi, $name',
          subtitle: "Let's see how your children are growing.",
          height: 180,
        ),
        Padding(
          padding: const EdgeInsets.all(Space.s4),
          child: AsyncView<List<ChildWithChecks>>(
            future: _future!,
            onRetry: () => setState(_load),
            builder: (context, items) => _body(context, items),
          ),
        ),
      ]),
    );
  }

  Future<void> _addChild() => Navigator.of(context)
      .push(MaterialPageRoute(builder: (_) => const AddChildScreen()));

  Widget _body(BuildContext context, List<ChildWithChecks> items) {
    final t = Theme.of(context).textTheme;
    if (items.isEmpty) {
      return Column(children: [
        const EmptyPanel(
          title: "Let's get started",
          message: 'Add your child to start checking how they are growing.',
        ),
        FilledButton(onPressed: _addChild, child: const Text('Add a child')),
      ]);
    }
    final item = items.firstWhere((i) => i.child.childId == _selectedId,
        orElse: () => items.first);

    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      SizedBox(
        height: 56,
        child: ListView(scrollDirection: Axis.horizontal, children: [
          for (final i in items) ...[
            _ChildChip(
              item: i,
              selected: i == item,
              onTap: () => setState(() => _selectedId = i.child.childId),
            ),
            const SizedBox(width: Space.s2),
          ],
          ActionChip(
            avatar: Icon(Icons.add_rounded, color: context.hc.plum900),
            label: const Text('Add'),
            onPressed: _addChild,
          ),
        ]),
      ),
      const SizedBox(height: Space.s4),
      if (item.latest?.caregiverMessage != null) ...[
        HatuaCard(
          color: context.hc.sun100,
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(Icons.health_and_safety_outlined, color: context.hc.onBright),
            const SizedBox(width: Space.s3),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('From your health worker',
                    style: t.labelLarge?.copyWith(color: context.hc.onBright)),
                const SizedBox(height: Space.s1),
                Text(item.latest!.caregiverMessage!,
                    style: t.bodyMedium?.copyWith(color: context.hc.onBright)),
              ]),
            ),
          ]),
        ),
        const SizedBox(height: Space.s3),
      ],
      _SummaryCard(item: item),
      const SizedBox(height: Space.s3),
      _NextCheckCard(item: item),
      const SizedBox(height: Space.s6),
      Text('Quick tools', style: t.titleLarge),
      const SizedBox(height: Space.s3),
      GridView.count(
        crossAxisCount: 2,
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: Space.s3,
        crossAxisSpacing: Space.s3,
        childAspectRatio: 1.5,
        children: [
          _Tool(
            icon: Icons.route_rounded,
            color: context.hc.sky100,
            title: 'Journey',
            subtitle: 'Checks by age',
            onTap: () => _openProfile(item),
          ),
          _Tool(
            icon: Icons.monitor_weight_outlined,
            color: context.hc.sun100,
            title: 'Growth',
            subtitle: 'Weight and height',
            onTap: () => _openProfile(item),
          ),
          _Tool(
            icon: Icons.history_rounded,
            color: context.hc.blush100,
            title: 'Past results',
            subtitle: '${item.checks.length} check${item.checks.length == 1 ? '' : 's'}',
            onTap: item.latest == null
                ? () => showMessage(context, 'No checks yet.')
                : () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => ResultScreen(assessment: item.latest!))),
          ),
          _Tool(
            icon: Icons.person_add_alt_rounded,
            color: context.hc.plum100,
            title: 'Add a child',
            subtitle: 'Under five',
            onTap: _addChild,
          ),
        ],
      ),
      const SizedBox(height: Space.s6),
      _PlayCard(idea: playIdeaFor(item.child.ageMonths), childName: item.child.firstName),
      const SizedBox(height: Space.s4),
    ]);
  }

  void _openProfile(ChildWithChecks item) => Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => ChildProfileScreen(childId: item.child.childId)));
}

class _ChildChip extends StatelessWidget {
  const _ChildChip({required this.item, required this.selected, required this.onTap});
  final ChildWithChecks item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Semantics(
      button: true,
      selected: selected,
      child: Material(
        color: selected ? context.hc.plum100 : context.hc.surfaceCard,
        shape: StadiumBorder(
            side: BorderSide(
                color: selected ? context.hc.plum700 : context.hc.plum200, width: 2)),
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(6, 6, Space.s4, 6),
            child: Row(children: [
              ChildAvatar(childId: item.child.childId, avatarId: item.child.avatarId, size: 36),
              const SizedBox(width: Space.s2),
              Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item.child.firstName, style: t.labelLarge),
                    Text(ageLabel(item.child.ageMonths), style: t.bodySmall),
                  ]),
            ]),
          ),
        ),
      ),
    );
  }
}

/// Plum card with the latest result, or a prompt when there is none.
class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.item});
  final ChildWithChecks item;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final latest = item.latest;
    final name = item.child.firstName;
    final on = context.hc.onHeader;
    final headline = latest == null
        ? 'No checks yet for $name'
        : switch (latest.riskLevel) {
            'high' => "Let's get $name checked by a health worker",
            'medium' => "Let's keep an eye on $name",
            _ => '$name is on track',
          };
    final needs = latest?.domains.where((d) => d.needsSupport).length ?? 0;
    return Container(
      padding: const EdgeInsets.all(Space.s4),
      decoration: BoxDecoration(
          color: context.hc.header, borderRadius: BorderRadius.circular(Radii.lg)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          if (latest != null) RiskChip.risk(latest.riskLevel),
          const Spacer(),
          if (latest != null)
            Text(DateFormat('d MMM yyyy').format(latest.submittedAt),
                style: t.bodySmall?.copyWith(color: on)),
        ]),
        const SizedBox(height: Space.s3),
        Text(headline, style: t.titleLarge?.copyWith(color: on)),
        const SizedBox(height: Space.s1),
        Text(
          latest == null
              ? 'A check takes about 5 minutes. You answer simple questions about what $name '
                  'can do.'
              : needs == 0
                  ? 'All four areas look on track. Keep playing and talking together.'
                  : '$needs area${needs == 1 ? '' : 's'} could use more practice. See the '
                      'results for things to try.',
          style: t.bodyMedium?.copyWith(color: on),
        ),
        if (latest != null) ...[
          const SizedBox(height: Space.s3),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton.icon(
              style: TextButton.styleFrom(foregroundColor: on),
              onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => ResultScreen(assessment: latest))),
              icon: const Icon(Icons.arrow_forward_rounded),
              label: const Text('Full results'),
            ),
          ),
        ],
      ]),
    );
  }
}

class _NextCheckCard extends StatelessWidget {
  const _NextCheckCard({required this.item});
  final ChildWithChecks item;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final due = nextCheckDue(item.child, item.latest);
    final now = DateTime.now();
    final isDue = due != null && !due.isAfter(now);
    final text = due == null
        ? 'All checks for this age are done. You can still start a new one.'
        : isDue
            ? item.latest == null
                ? 'Start the first check for ${item.child.firstName}.'
                : 'A new check is due for ${item.child.firstName}.'
            : 'Next check around ${DateFormat('d MMM yyyy').format(due)}.';
    return HatuaCard(
      color: context.hc.sun100,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          Icon(Icons.event_available_rounded, color: context.hc.onBright),
          const SizedBox(width: Space.s3),
          Expanded(
              child: Text(text, style: t.bodyMedium?.copyWith(color: context.hc.onBright))),
        ]),
        const SizedBox(height: Space.s3),
        FilledButton.icon(
          onPressed: () => startCheck(context, child: item.child),
          icon: const Icon(Icons.play_arrow_rounded),
          label: Text(item.latest == null ? 'Start first check' : 'Start a check'),
        ),
      ]),
    );
  }
}

class _Tool extends StatelessWidget {
  const _Tool({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });
  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return HatuaCard(
      onTap: onTap,
      padding: const EdgeInsets.all(Space.s3),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          child: Icon(icon, color: context.hc.onBright, size: 22),
        ),
        const Spacer(),
        Text(title, style: t.labelLarge),
        Text(subtitle, style: t.bodySmall),
      ]),
    );
  }
}

class _PlayCard extends StatelessWidget {
  const _PlayCard({required this.idea, required this.childName});
  final PlayIdea idea;
  final String childName;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return HatuaCard(
      color: context.hc.plum100,
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Sprout(pose: SproutPose.waving, size: 64, bob: false),
        const SizedBox(width: Space.s3),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('PLAY IDEA FOR TODAY', style: t.labelMedium),
            const SizedBox(height: Space.s1),
            Text(idea.title, style: t.titleMedium),
            const SizedBox(height: Space.s1),
            Text(idea.body.replaceAll('{name}', childName), style: t.bodyMedium),
          ]),
        ),
      ]),
    );
  }
}
