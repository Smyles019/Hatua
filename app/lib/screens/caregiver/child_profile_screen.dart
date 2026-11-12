import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/child_avatar.dart';
import '../../widgets/common.dart';
import '../../widgets/domain.dart';
import '../../widgets/growth_chart.dart';
import '../../widgets/journey_path.dart';
import '../../widgets/risk_chip.dart';
import 'caregiver_data.dart';
import 'caregiver_shell.dart';
import 'result_screen.dart';
import '../../i18n/strings.dart';

class ChildProfileScreen extends StatefulWidget {
  const ChildProfileScreen({super.key, required this.childId});
  final String childId;

  @override
  State<ChildProfileScreen> createState() => _ChildProfileScreenState();
}

class _ChildProfileScreenState extends State<ChildProfileScreen> {
  Future<ChildWithChecks>? _future;
  int _version = -1;

  void _load() {
    final s = context.read<Session>();
    _version = s.dataVersion;
    _future = () async {
      final data = await s.api.get('/children/${widget.childId}');
      final child = Child.fromJson(data as Map<String, dynamic>);
      return ChildWithChecks(child, await loadChecks(s.api, child.childId));
    }();
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (_future == null || _version != s.dataVersion) _load();
    final isCaregiver = s.user?.role == 'caregiver';
    return Scaffold(
      appBar: AppBar(title: Text(tr('Child profile'))),
      body: AsyncView<ChildWithChecks>(
        future: _future!,
        onRetry: () => setState(_load),
        builder: (context, item) => _body(context, item, isCaregiver),
      ),
    );
  }

  Widget _body(BuildContext context, ChildWithChecks item, bool isCaregiver) {
    final t = Theme.of(context).textTheme;
    final c = item.child;
    final latest = item.latest;
    final df = DateFormat('d MMM yyyy');
    final due = nextCheckDue(c, latest);

    return ListView(padding: EdgeInsets.all(Space.s4), children: [
      HatuaCard(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            ChildAvatar(childId: c.childId, avatarId: c.avatarId, size: 72, ring: true),
            SizedBox(width: Space.s4),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(c.firstName, style: t.headlineSmall),
                Text('${ageLabel(c.ageMonths)} · ${c.sex == 'female' ? 'Girl' : 'Boy'}',
                    style: t.bodySmall),
                Text(c.location, style: t.bodySmall),
                if (isCaregiver)
                  TextButton.icon(
                    style: TextButton.styleFrom(padding: EdgeInsets.zero),
                    onPressed: () => _changeAvatar(context, c),
                    icon: Icon(Icons.edit_outlined, size: 18),
                    label: Text(tr('Change animal')),
                  ),
              ]),
            ),
          ]),
          if (latest != null) ...[
            SizedBox(height: Space.s4),
            Text(tr('LATEST CHECK'), style: t.labelMedium),
            SizedBox(height: Space.s1),
            RiskChip.risk(latest.riskLevel),
            SizedBox(height: Space.s4),
            Wrap(spacing: Space.s4, runSpacing: Space.s3, children: [
              for (final d in latest.domains)
                SizedBox(
                  width: 140,
                  child: Row(children: [
                    DomainBadge(d.domain, size: 32),
                    SizedBox(width: Space.s2),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(DomainStyle.of(context, d.domain).label,
                            style: t.bodySmall?.copyWith(color: context.hc.plum900)),
                        Text(
                            d.notAssessed
                                ? tr('From 24 months')
                                : d.needsSupport
                                    ? tr('Needs support')
                                    : tr('On track'),
                            style: t.labelLarge?.copyWith(fontSize: 14)),
                      ]),
                    ),
                  ]),
                ),
            ]),
          ],
        ]),
      ),
      SizedBox(height: Space.s3),
      if (due != null)
        HatuaCard(
          color: context.hc.sun100,
          child: Row(children: [
            Icon(Icons.event_rounded, color: context.hc.plum900),
            SizedBox(width: Space.s3),
            Expanded(
              child: Text(
                due.isAfter(DateTime.now())
                    ? tr('Next check: around {date}', {'date': df.format(due)})
                    : latest == null
                        ? tr('No checks yet. Start the first one now.')
                        : tr('A new check is due.'),
                style: t.bodyMedium,
              ),
            ),
          ]),
        ),
      SizedBox(height: Space.s3),
      // Reasons for special care (Mother and Child Health Handbook), shown to the CHW.
      HatuaCard(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(tr('Good for the health worker to know'), style: t.titleMedium)),
            if (isCaregiver)
              TextButton(
                  onPressed: () => _editCareFactors(context, c), child: Text(tr('Edit'))),
          ]),
          if (c.careFactors.isEmpty)
            Text(tr('Nothing ticked.'), style: t.bodySmall)
          else
            for (final f in c.careFactors)
              Padding(
                padding: EdgeInsets.only(top: Space.s1),
                child: Text('•  ${careFactorLabels[f] ?? f}', style: t.bodyMedium),
              ),
        ]),
      ),
      SizedBox(height: Space.s6),
      _GrowthSection(child: c, canAdd: isCaregiver),
      SizedBox(height: Space.s6),
      Text(tr("{firstName}'s journey", {'firstName': c.firstName}), style: t.titleLarge),
      Text(tr('One step for each age, from birth to five.'), style: t.bodySmall),
      SizedBox(height: Space.s4),
      JourneyPath(
        ageMonths: c.ageMonths,
        checks: item.checks,
        onOpen: (a) => Navigator.of(context)
            .push(MaterialPageRoute(builder: (_) => ResultScreen(assessment: a))),
        onStart: isCaregiver ? () => startCheck(context, child: c) : null,
      ),
      // The current band already has a check: a repeat check is still allowed.
      if (isCaregiver && latest != null && _sameBand(latest.ageMonths, c.ageMonths)) ...[
        SizedBox(height: Space.s4),
        OutlinedButton(
          onPressed: () => startCheck(context, child: c),
          child: Text(tr('Start a new check')),
        ),
      ],
      SizedBox(height: Space.s6),
    ]);
  }

  static bool _sameBand(int a, int b) =>
      ageBands.any((band) => a >= band.$1 && a <= band.$2 && b >= band.$1 && b <= band.$2);

  Future<void> _editCareFactors(BuildContext context, Child child) async {
    final session = context.read<Session>();
    var picked = child.careFactors.toSet();
    final result = await showModalBottomSheet<Set<String>>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheet) => SafeArea(
          child: Padding(
            padding: EdgeInsets.all(Space.s4),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text(tr('Does any of this apply to {firstName}?', {'firstName': child.firstName}),
                  style: Theme.of(ctx).textTheme.titleLarge),
              SizedBox(height: Space.s2),
              CareFactorChecks(
                  selected: picked,
                  labels: careFactorLabels,
                  onChanged: (f) => setSheet(() => picked = f)),
              SizedBox(height: Space.s4),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                    onPressed: () => Navigator.of(ctx).pop(picked), child: Text(tr('Save'))),
              ),
            ]),
          ),
        ),
      ),
    );
    if (result == null) return;
    try {
      await session.api
          .patch('/children/${child.childId}', {'care_factors': result.toList()});
      session.dataChanged();
    } catch (e) {
      if (context.mounted) showError(context, e);
    }
  }

  Future<void> _changeAvatar(BuildContext context, Child child) async {
    final session = context.read<Session>();
    var picked = avatarIds.contains(child.avatarId) ? child.avatarId! : defaultAvatar(child.childId);
    final result = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSheet) => SafeArea(
          child: Padding(
            padding: EdgeInsets.all(Space.s4),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text(tr('Pick an animal'), style: Theme.of(ctx).textTheme.titleLarge),
              SizedBox(height: Space.s4),
              AvatarPicker(selected: picked, onPick: (id) => setSheet(() => picked = id)),
              SizedBox(height: Space.s4),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                    onPressed: () => Navigator.of(ctx).pop(picked), child: Text(tr('Save'))),
              ),
            ]),
          ),
        ),
      ),
    );
    if (result == null || result == child.avatarId) return;
    try {
      await session.api.patch('/children/${child.childId}', {'avatar_id': result});
      session.dataChanged();
    } catch (e) {
      if (context.mounted) showError(context, e);
    }
  }
}

/// Weight and height entries from the API, newest first, with a way to add one.
class _GrowthSection extends StatelessWidget {
  const _GrowthSection({required this.child, required this.canAdd});
  final Child child;
  final bool canAdd;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final entries = child.growth.reversed.toList();
    final df = DateFormat('d MMM yyyy');
    String n(double? v, String unit) => v == null ? '-' : '${v.toStringAsFixed(1)} $unit';
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Expanded(child: Text(tr('Growth'), style: t.titleLarge)),
        if (canAdd)
          TextButton.icon(
            onPressed: () => showDialog(
                context: context, builder: (_) => _GrowthDialog(child: child)),
            icon: Icon(Icons.add_rounded),
            label: Text(tr('Add')),
          ),
      ]),
      SizedBox(height: Space.s2),
      if (entries.isEmpty)
        HatuaCard(
          child: Text(
              tr('No weight or height yet. Add them from the clinic booklet after a visit.'),
              style: t.bodyMedium),
        )
      else ...[
        Row(children: [
          Expanded(
              child: _Measure(
                  icon: Icons.monitor_weight_outlined,
                  label: tr('Weight'),
                  value: n(entries.first.weightKg, 'kg'),
                  color: context.hc.sun100)),
          SizedBox(width: Space.s3),
          Expanded(
              child: _Measure(
                  icon: Icons.straighten_rounded,
                  label: tr('Height'),
                  value: n(entries.first.heightCm, 'cm'),
                  color: context.hc.sky100)),
        ]),
        if (entries.any((e) => e.weightKg != null)) ...[
          SizedBox(height: Space.s3),
          HatuaCard(child: WeightChart(child: child)),
        ],
        SizedBox(height: Space.s3),
        HatuaCard(
          padding: EdgeInsets.zero,
          child: Column(children: [
            for (final e in entries.take(5))
              ListTile(
                dense: true,
                title: Text(df.format(e.measuredOn), style: t.bodyMedium),
                trailing: Text('${n(e.weightKg, 'kg')}  ·  ${n(e.heightCm, 'cm')}',
                    style: t.bodySmall),
              ),
          ]),
        ),
      ],
    ]);
  }
}

class _Measure extends StatelessWidget {
  const _Measure(
      {required this.icon, required this.label, required this.value, required this.color});
  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return HatuaCard(
      color: color,
      child: Row(children: [
        Icon(icon, color: context.hc.plum900),
        SizedBox(width: Space.s2),
        Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(label, style: t.bodySmall?.copyWith(color: context.hc.plum900)),
          Text(value, style: t.titleMedium?.copyWith(color: context.hc.plum900)),
        ]),
      ]),
    );
  }
}

class _GrowthDialog extends StatefulWidget {
  const _GrowthDialog({required this.child});
  final Child child;

  @override
  State<_GrowthDialog> createState() => _GrowthDialogState();
}

class _GrowthDialogState extends State<_GrowthDialog> {
  final _form = GlobalKey<FormState>();
  final _weight = TextEditingController();
  final _height = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _weight.dispose();
    _height.dispose();
    super.dispose();
  }

  double? _num(String s) => double.tryParse(s.trim().replaceAll(',', '.'));

  String? _range(String? v, double lo, double hi) {
    if (v == null || v.trim().isEmpty) return null;
    final x = _num(v);
    return (x == null || x < lo || x > hi) ? tr('Between {lo} and {hi}', {'lo': lo, 'hi': hi}) : null;
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    final w = _num(_weight.text), h = _num(_height.text);
    if (w == null && h == null) {
      showMessage(context, tr('Enter a weight, a height or both.'));
      return;
    }
    setState(() => _busy = true);
    final session = context.read<Session>();
    try {
      final entry = GrowthEntry(measuredOn: DateTime.now(), weightKg: w, heightCm: h);
      await session.api.post('/children/${widget.child.childId}/growth', entry.toJson());
      session.dataChanged();
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(tr('Add weight and height')),
      content: Form(
        key: _form,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          LabeledField(
            label: tr('Weight (kg)'),
            controller: _weight,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            validator: (v) => _range(v, 1, 35),
          ),
          SizedBox(height: Space.s3),
          LabeledField(
            label: tr('Height or length (cm)'),
            controller: _height,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            textInputAction: TextInputAction.done,
            validator: (v) => _range(v, 40, 130),
          ),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text(tr('Cancel'))),
        TextButton(onPressed: _busy ? null : _save, child: Text(tr('Save'))),
      ],
    );
  }
}
