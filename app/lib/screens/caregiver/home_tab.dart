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
import '../messages/thread_screen.dart';
import 'add_child_screen.dart';
import 'care_schedule.dart';
import 'caregiver_data.dart';
import 'caregiver_shell.dart';
import 'child_profile_screen.dart';
import 'play_ideas.dart';
import 'result_screen.dart';
import '../../i18n/strings.dart';

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
    // Quietly retry checks saved while offline (#8). Only speaks up if something
    // was sent or could not be used; "still offline" stays silent here.
    if (session.pending.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _sendPending(quiet: true));
    }
  }

  Future<void> _sendPending({bool quiet = false}) async {
    final report = await context.read<Session>().sendPending();
    if (!mounted) return;
    final msg = report.message;
    final onlyStillWaiting = report.sent.isEmpty && report.rejected.isEmpty;
    if (msg != null && !(quiet && onlyStillWaiting)) showMessage(context, msg);
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
          title: tr('Hi, {name}', {'name': name}),
          subtitle: tr("Let's see how your children are growing."),
          height: 180,
        ),
        if (session.pending.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(Space.s4, Space.s4, Space.s4, 0),
            child: _PendingCard(
              names: session.pending.map((p) => p.childName).toList(),
              sending: session.sendingPending,
              onSend: () => _sendPending(),
            ),
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
        EmptyPanel(
          title: tr("Let's get started"),
          message: tr('Add your child to start checking how they are growing.'),
        ),
        FilledButton(onPressed: _addChild, child: Text(tr('Add a child'))),
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
            label: Text(tr('Add')),
            onPressed: _addChild,
          ),
        ]),
      ),
      const SizedBox(height: Space.s4),
      if (item.latest?.caregiverMessage != null) ...[
        HatuaCard(
          color: context.hc.sun100,
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(Icons.health_and_safety_outlined, color: context.hc.plum900),
            const SizedBox(width: Space.s3),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(tr('From your health worker'),
                    style: t.labelLarge?.copyWith(color: context.hc.plum900)),
                const SizedBox(height: Space.s1),
                Text(item.latest!.caregiverMessage!,
                    style: t.bodyMedium?.copyWith(color: context.hc.plum900)),
              ]),
            ),
          ]),
        ),
        const SizedBox(height: Space.s3),
      ],
      _SummaryCard(item: item),
      const SizedBox(height: Space.s3),
      _NextCheckCard(item: item),
      const SizedBox(height: Space.s3),
      _CareCard(item: item),
      const SizedBox(height: Space.s6),
      Text(tr('Quick tools'), style: t.titleLarge),
      const SizedBox(height: Space.s3),
      // Two per row. Tiles grow to fit their text (long Swahili titles, large phone
      // fonts) instead of a fixed height that overflows.
      _ToolGrid(
        children: [
          _Tool(
            icon: Icons.route_rounded,
            color: context.hc.sky100,
            title: tr('Journey'),
            subtitle: tr('Checks by age'),
            onTap: () => _openProfile(item),
          ),
          _Tool(
            icon: Icons.monitor_weight_outlined,
            color: context.hc.sun100,
            title: tr('Growth'),
            subtitle: tr('Weight and height'),
            onTap: () => _openProfile(item),
          ),
          _Tool(
            icon: Icons.history_rounded,
            color: context.hc.blush100,
            title: tr('Past results'),
            subtitle: item.checks.length == 1
                ? tr('1 check')
                : tr('{n} checks', {'n': item.checks.length}),
            onTap: item.latest == null
                ? () => showMessage(context, tr('No checks yet.'))
                : () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => ResultScreen(assessment: item.latest!))),
          ),
          _Tool(
            icon: Icons.chat_bubble_outline_rounded,
            color: context.hc.plum100,
            title: tr('Ask a health worker'),
            subtitle: tr('Send a question'),
            onTap: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => const ThreadScreen())),
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

/// Checks finished while offline and still waiting to be sent (#8).
class _PendingCard extends StatelessWidget {
  const _PendingCard({required this.names, required this.sending, required this.onSend});
  final List<String> names;
  final bool sending;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final one = names.length == 1;
    return HatuaCard(
      color: context.hc.sun100,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(Icons.cloud_upload_outlined, color: context.hc.plum900),
          SizedBox(width: Space.s3),
          Expanded(
            child: Text(
                one
                    ? tr("{first}'s check is saved on this phone and waiting to be sent.", {'first': names.first})
                    : tr('{n} checks are saved on this phone and waiting to be sent: {names}.', {'n': names.length, 'names': names.join(', ')}),
                style: t.bodyMedium),
          ),
        ]),
        SizedBox(height: Space.s3),
        Align(
          alignment: Alignment.centerRight,
          child: FilledButton(
            onPressed: sending ? null : onSend,
            child: Text(sending ? tr('Sending...') : tr('Send now')),
          ),
        ),
      ]),
    );
  }
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
        ? tr('No checks yet for {name}', {'name': name})
        : switch (latest.riskLevel) {
            'high' => tr("Let's get {name} checked by a health worker", {'name': name}),
            'medium' => tr("Let's keep an eye on {name}", {'name': name}),
            _ => tr('{name} is on track', {'name': name}),
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
              ? tr('A check takes about 5 minutes. You answer simple questions about what {name} can do.', {'name': name})
              : needs == 0
                  ? tr('All four areas look on track. Keep playing and talking together.')
                  : (needs == 1
                      ? tr('1 area could use more practice. See the results for things to try.')
                      : tr('{n} areas could use more practice. See the results for things to try.', {'n': needs})),
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
              label: Text(tr('Full results')),
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
        ? tr('All checks for this age are done. You can still start a new one.')
        : isDue
            ? item.latest == null
                ? tr('Start the first check for {firstName}.', {'firstName': item.child.firstName})
                : tr('A new check is due for {firstName}.', {'firstName': item.child.firstName})
            : tr('Next check around {date}.', {'date': DateFormat('d MMM yyyy').format(due)});
    return HatuaCard(
      color: context.hc.sun100,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Row(children: [
          Icon(Icons.event_available_rounded, color: context.hc.plum900),
          const SizedBox(width: Space.s3),
          Expanded(
              child: Text(text, style: t.bodyMedium?.copyWith(color: context.hc.plum900))),
        ]),
        const SizedBox(height: Space.s3),
        FilledButton.icon(
          onPressed: () => startCheck(context, child: item.child),
          icon: const Icon(Icons.play_arrow_rounded),
          label: Text(item.latest == null ? tr('Start first check') : tr('Start a check')),
        ),
      ]),
    );
  }
}

/// "Coming up at the clinic": the next vitamin A, deworming, vaccine and monthly visit,
/// from the routine schedule in the Mother and Child Health Handbook.
class _CareCard extends StatelessWidget {
  const _CareCard({required this.item});
  final ChildWithChecks item;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final today = DateTime.now();
    final care = nextCare(item.child.dateOfBirth, today: today);
    if (care.isEmpty) return const SizedBox.shrink();
    return HatuaCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.local_hospital_outlined, color: context.hc.plum900),
          const SizedBox(width: Space.s2),
          Expanded(child: Text(tr('Coming up at the clinic'), style: t.titleMedium)),
        ]),
        const SizedBox(height: Space.s2),
        for (final c in care)
          Padding(
            padding: const EdgeInsets.only(top: Space.s2),
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(c.title, style: t.labelLarge),
                  Text(c.detail, style: t.bodySmall),
                ]),
              ),
              const SizedBox(width: Space.s2),
              Text(
                c.dueNow(today) ? tr('Due now') : DateFormat('d MMM yyyy').format(c.due),
                style: t.labelLarge,
              ),
            ]),
          ),
        const SizedBox(height: Space.s3),
        Text(
          tr('These are the usual ages. The app does not know what {firstName} has already had, so check the clinic booklet.', {'firstName': item.child.firstName}),
          style: t.bodySmall,
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
        const SizedBox(height: Space.s3),
        Text(title, style: t.labelLarge),
        Text(subtitle, style: t.bodySmall),
      ]),
    );
  }
}

/// Lays tools out two per row; both tiles in a row take the height of the taller one.
class _ToolGrid extends StatelessWidget {
  const _ToolGrid({required this.children});
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final rows = <Widget>[];
    for (var i = 0; i < children.length; i += 2) {
      if (i > 0) rows.add(const SizedBox(height: Space.s3));
      rows.add(IntrinsicHeight(
        child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Expanded(child: children[i]),
          const SizedBox(width: Space.s3),
          Expanded(child: i + 1 < children.length ? children[i + 1] : const SizedBox()),
        ]),
      ));
    }
    return Column(children: rows);
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
            Text(tr('PLAY IDEA FOR TODAY'), style: t.labelMedium),
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
