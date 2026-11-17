import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../i18n/strings.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/record_charts.dart';
import 'feeding_guide_screen.dart';
import 'health_record_screen.dart';

/// The purple-book sections of a child's profile: the health booklet summary, birth and
/// home details, the feeding guide for the child's age and the sick visits.

final _df = DateFormat('d MMM yyyy');

// ---------------------------------------------------------------------------
// Health booklet summary
// ---------------------------------------------------------------------------

class BookletCard extends StatefulWidget {
  const BookletCard({super.key, required this.child, required this.canEdit});
  final Child child;
  final bool canEdit;

  @override
  State<BookletCard> createState() => _BookletCardState();
}

class _BookletCardState extends State<BookletCard> {
  Future<HealthRecord>? _future;
  int _version = -1;

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (_future == null || _version != s.dataVersion) {
      _version = s.dataVersion;
      _future = s.api
          .get('/children/${widget.child.childId}/record')
          .then((d) => HealthRecord.fromJson(d as Map<String, dynamic>));
    }
    final t = Theme.of(context).textTheme;
    return InkWell(
      borderRadius: BorderRadius.circular(Radii.lg),
      onTap: () async {
        await Navigator.of(context).push(MaterialPageRoute(
            builder: (_) => HealthRecordScreen(child: widget.child, canEdit: widget.canEdit)));
        if (mounted) setState(() => _future = null);
      },
      child: HatuaCard(
        child: FutureBuilder<HealthRecord>(
          future: _future,
          builder: (context, snap) {
            final r = snap.data;
            final given = r?.count('vaccine', 'given') ?? 0;
            final total = r?.count('vaccine', 'total') ?? 0;
            final overdue = r?.count('vaccine', 'overdue') ?? 0;
            final due = r?.count('vaccine', 'due') ?? 0;
            return Row(children: [
              ProgressRing(done: given, total: total, size: 64),
              const SizedBox(width: Space.s3),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(tr('Health booklet'), style: t.titleMedium),
                  Text(tr('Vaccines, vitamin A and deworming'), style: t.bodySmall),
                  if (overdue > 0)
                    Row(children: [
                      const DoseMark('overdue', size: 14),
                      const SizedBox(width: 4),
                      Text(tr('{n} overdue', {'n': overdue}),
                          style: t.bodySmall?.copyWith(fontWeight: FontWeight.w700)),
                    ])
                  else if (due > 0)
                    Row(children: [
                      const DoseMark('due', size: 14),
                      const SizedBox(width: 4),
                      Text(tr('{n} due now', {'n': due}), style: t.bodySmall),
                    ]),
                ]),
              ),
              const Icon(Icons.chevron_right_rounded),
            ]);
          },
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Birth and home
// ---------------------------------------------------------------------------

class BirthHomeCard extends StatelessWidget {
  const BirthHomeCard({super.key, required this.child, required this.canEdit});
  final Child child;
  final bool canEdit;

  static Map<String, String> get places => {
        'facility': tr('At a health facility'),
        'home': tr('At home'),
        'on_the_way': tr('On the way to a facility'),
      };

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final b = child.birth;
    String yn(bool? v) => v == null ? tr('Not answered') : (v ? tr('Yes') : tr('No'));
    Widget row(IconData icon, String label, String value, {bool warn = false}) => Padding(
          padding: const EdgeInsets.only(top: Space.s2),
          child: Row(children: [
            Icon(icon, size: 20, color: context.hc.plum700),
            const SizedBox(width: Space.s2),
            Expanded(child: Text(label, style: t.bodyMedium)),
            Text(value,
                style: t.bodyMedium?.copyWith(fontWeight: warn ? FontWeight.w800 : FontWeight.w600)),
          ]),
        );
    return HatuaCard(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(tr('Birth and home'), style: t.titleMedium)),
          if (canEdit)
            TextButton(
                onPressed: () => showModalBottomSheet(
                    context: context,
                    isScrollControlled: true,
                    showDragHandle: true,
                    builder: (_) => _BirthHomeSheet(child: child)),
                child: Text(tr('Edit'))),
        ]),
        row(Icons.monitor_weight_outlined, tr('Birth weight'),
            b.weightKg == null ? '-' : '${b.weightKg!.toStringAsFixed(1)} kg'),
        row(Icons.calendar_month_outlined, tr('Weeks of pregnancy at birth'),
            b.gestationWeeks == null ? '-' : '${b.gestationWeeks}'),
        row(Icons.local_hospital_outlined, tr('Born'), places[b.place] ?? '-'),
        row(Icons.badge_outlined, tr('Birth certificate'), yn(child.birthCertificate),
            warn: child.birthCertificate == false),
        row(Icons.bed_outlined, tr('Sleeps under a treated net'), yn(child.bedNet),
            warn: child.bedNet == false),
        if (child.birthCertificate == false)
          Padding(
            padding: const EdgeInsets.only(top: Space.s2),
            child: Text(
                tr('A birth certificate is free at the civil registration office before the child turns 6 months.'),
                style: t.bodySmall),
          ),
        if (child.bedNet == false)
          Padding(
            padding: const EdgeInsets.only(top: Space.s2),
            child: Text(tr('Ask at the clinic for a treated mosquito net: it protects against malaria.'),
                style: t.bodySmall),
          ),
      ]),
    );
  }
}

class _BirthHomeSheet extends StatefulWidget {
  const _BirthHomeSheet({required this.child});
  final Child child;

  @override
  State<_BirthHomeSheet> createState() => _BirthHomeSheetState();
}

class _BirthHomeSheetState extends State<_BirthHomeSheet> {
  final _form = GlobalKey<FormState>();
  late final _weight = TextEditingController(
      text: widget.child.birth.weightKg?.toStringAsFixed(1) ?? '');
  late final _weeks = TextEditingController(text: widget.child.birth.gestationWeeks?.toString() ?? '');
  late String? _place = widget.child.birth.place;
  late bool? _cert = widget.child.birthCertificate;
  late bool? _net = widget.child.bedNet;
  bool _busy = false;

  @override
  void dispose() {
    _weight.dispose();
    _weeks.dispose();
    super.dispose();
  }

  double? _num(String s) => double.tryParse(s.trim().replaceAll(',', '.'));

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    final session = context.read<Session>();
    try {
      await session.api.patch('/children/${widget.child.childId}', {
        'birth': BirthDetails(
          weightKg: _num(_weight.text),
          gestationWeeks: int.tryParse(_weeks.text.trim()),
          place: _place,
        ).toJson(),
        'birth_certificate': _cert,
        'bed_net': _net,
      });
      session.dataChanged();
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _yesNo(String label, bool? value, ValueChanged<bool?> onChanged) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: Space.s1),
          SegmentedButton<int>(
            segments: [
              ButtonSegment(value: 1, label: Text(tr('Yes'))),
              ButtonSegment(value: 0, label: Text(tr('No'))),
              ButtonSegment(value: -1, label: Text(tr('Not sure'))),
            ],
            selected: {value == null ? -1 : (value ? 1 : 0)},
            onSelectionChanged: (s) => onChanged(s.first == -1 ? null : s.first == 1),
          ),
        ],
      );

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Padding(
      padding: EdgeInsets.fromLTRB(
          Space.s4, 0, Space.s4, MediaQuery.viewInsetsOf(context).bottom + Space.s4),
      child: Form(
        key: _form,
        child: SingleChildScrollView(
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text(tr('Birth and home'), style: t.titleLarge),
            Text(tr('From the birth page of the clinic booklet.'), style: t.bodySmall),
            const SizedBox(height: Space.s3),
            LabeledField(
              label: tr('Birth weight (kg)'),
              controller: _weight,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              validator: (v) {
                if (v == null || v.trim().isEmpty) return null;
                final x = _num(v);
                return x == null || x < 0.4 || x > 6.5 ? tr('Between {lo} and {hi}', {'lo': 0.4, 'hi': 6.5}) : null;
              },
            ),
            const SizedBox(height: Space.s3),
            LabeledField(
              label: tr('Weeks of pregnancy at birth'),
              controller: _weeks,
              keyboardType: TextInputType.number,
              validator: (v) {
                if (v == null || v.trim().isEmpty) return null;
                final x = int.tryParse(v.trim());
                return x == null || x < 22 || x > 44 ? tr('Between {lo} and {hi}', {'lo': 22, 'hi': 44}) : null;
              },
            ),
            const SizedBox(height: Space.s3),
            Text(tr('Where was the child born?'), style: t.labelLarge),
            RadioGroup<String>(
              groupValue: _place,
              onChanged: (v) => setState(() => _place = v),
              child: Column(children: [
                for (final e in BirthHomeCard.places.entries)
                  RadioListTile<String>(
                      contentPadding: EdgeInsets.zero, value: e.key, title: Text(e.value)),
              ]),
            ),
            const SizedBox(height: Space.s2),
            _yesNo(tr('Does the child have a birth certificate?'), _cert, (v) => setState(() => _cert = v)),
            const SizedBox(height: Space.s3),
            _yesNo(tr('Does the child sleep under a treated mosquito net?'), _net,
                (v) => setState(() => _net = v)),
            const SizedBox(height: Space.s4),
            FilledButton(
                onPressed: _busy ? null : _save, child: Text(_busy ? tr('Saving...') : tr('Save'))),
          ]),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Next clinic visit
// ---------------------------------------------------------------------------

class NextClinicCard extends StatelessWidget {
  const NextClinicCard({super.key, required this.child, required this.canEdit});
  final Child child;
  final bool canEdit;

  Future<void> _set(BuildContext context, DateTime? date) async {
    final session = context.read<Session>();
    try {
      await session.api.patch('/children/${child.childId}', {
        'next_clinic_on': date == null ? null : DateFormat('yyyy-MM-dd').format(date),
      });
      session.dataChanged();
    } catch (e) {
      if (context.mounted) showError(context, e);
    }
  }

  Future<void> _pick(BuildContext context) async {
    final today = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: child.nextClinicOn ?? today.add(const Duration(days: 28)),
      firstDate: today,
      lastDate: today.add(const Duration(days: 365)),
      helpText: tr('Date written in the booklet for the next visit'),
    );
    if (picked != null && context.mounted) await _set(context, picked);
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final next = child.nextClinicOn;
    final days = next?.difference(DateUtils.dateOnly(DateTime.now())).inDays;
    return HatuaCard(
      color: context.hc.sky100,
      child: Row(children: [
        Icon(Icons.event_available_outlined, color: context.hc.plum900),
        const SizedBox(width: Space.s3),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(tr('Next clinic visit'), style: t.titleSmall?.copyWith(color: context.hc.plum900)),
            Text(
              next == null
                  ? tr('Add the date the nurse wrote in the booklet, and Hatua will remind you the day before.')
                  : days == 0
                      ? tr('Today, {date}', {'date': _df.format(next)})
                      : days == 1
                          ? tr('Tomorrow, {date}', {'date': _df.format(next)})
                          : tr('{date}, in {n} days', {'date': _df.format(next), 'n': days}),
              style: t.bodySmall?.copyWith(color: context.hc.plum900),
            ),
          ]),
        ),
        if (canEdit) ...[
          TextButton(onPressed: () => _pick(context), child: Text(next == null ? tr('Add') : tr('Change'))),
          if (next != null)
            IconButton(
                tooltip: tr('Remove'),
                onPressed: () => _set(context, null),
                icon: const Icon(Icons.close_rounded)),
        ],
      ]),
    );
  }
}

// ---------------------------------------------------------------------------
// Feeding
// ---------------------------------------------------------------------------

class FeedingCard extends StatelessWidget {
  const FeedingCard({super.key, required this.child});
  final Child child;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final band = feedingBands[feedingBandFor(child.ageMonths)];
    return InkWell(
      borderRadius: BorderRadius.circular(Radii.lg),
      onTap: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) =>
              FeedingGuideScreen(childName: child.firstName, ageMonths: child.ageMonths))),
      child: HatuaCard(
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(Icons.restaurant_menu_rounded, color: context.hc.plum700),
          const SizedBox(width: Space.s3),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(tr('Feeding at {age}', {'age': tr(band.label)}), style: t.titleMedium),
              const SizedBox(height: Space.s1),
              Text(tr(band.tips.first), style: t.bodyMedium),
              const SizedBox(height: Space.s1),
              Text(tr('See the full feeding guide'),
                  style: t.labelLarge?.copyWith(color: context.hc.plum700)),
            ]),
          ),
        ]),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Sick visits
// ---------------------------------------------------------------------------

class SickVisitsSection extends StatelessWidget {
  const SickVisitsSection({super.key, required this.child, required this.canEdit});
  final Child child;
  final bool canEdit;

  Future<void> _delete(BuildContext context, SickVisit v) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(tr('Delete this visit?')),
        content: Text('${_df.format(v.visitOn)}: ${v.illness}'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('Cancel'))),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: Text(tr('Delete'))),
        ],
      ),
    );
    if (yes != true || !context.mounted) return;
    final session = context.read<Session>();
    try {
      await session.api.delete('/children/${child.childId}/sick-visits/${v.visitId}');
      session.dataChanged();
    } catch (e) {
      if (context.mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final visits = child.sickVisits;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Row(children: [
        Expanded(child: Text(tr('Sick visits'), style: t.titleLarge)),
        if (canEdit)
          TextButton.icon(
            onPressed: () => showDialog(context: context, builder: (_) => _SickVisitDialog(child: child)),
            icon: const Icon(Icons.add_rounded),
            label: Text(tr('Add')),
          ),
      ]),
      Text(tr('Your own notes of when the child was ill and what the clinic gave.'),
          style: t.bodySmall),
      const SizedBox(height: Space.s2),
      if (visits.isEmpty)
        HatuaCard(child: Text(tr('No sick visits noted.'), style: t.bodyMedium))
      else
        HatuaCard(
          padding: EdgeInsets.zero,
          child: Column(children: [
            for (final v in visits)
              ListTile(
                leading: Icon(Icons.healing_outlined, color: context.hc.plum700),
                title: Text(v.illness, style: t.bodyMedium),
                subtitle: Text(
                    [_df.format(v.visitOn), if (v.treatment != null) v.treatment!].join(' · '),
                    style: t.bodySmall),
                trailing: canEdit
                    ? IconButton(
                        tooltip: tr('Delete'),
                        icon: const Icon(Icons.delete_outline_rounded),
                        onPressed: () => _delete(context, v))
                    : null,
              ),
          ]),
        ),
    ]);
  }
}

class _SickVisitDialog extends StatefulWidget {
  const _SickVisitDialog({required this.child});
  final Child child;

  @override
  State<_SickVisitDialog> createState() => _SickVisitDialogState();
}

class _SickVisitDialogState extends State<_SickVisitDialog> {
  final _form = GlobalKey<FormState>();
  final _illness = TextEditingController();
  final _treatment = TextEditingController();
  DateTime _on = DateTime.now();
  bool _busy = false;

  @override
  void dispose() {
    _illness.dispose();
    _treatment.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    final session = context.read<Session>();
    try {
      await session.api.post('/children/${widget.child.childId}/sick-visits', {
        'visit_on': DateFormat('yyyy-MM-dd').format(_on),
        'illness': _illness.text.trim(),
        if (_treatment.text.trim().isNotEmpty) 'treatment': _treatment.text.trim(),
      });
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
      title: Text(tr('Add a sick visit')),
      content: Form(
        key: _form,
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            OutlinedButton.icon(
              onPressed: () async {
                final d = await showDatePicker(
                    context: context,
                    initialDate: _on,
                    firstDate: widget.child.dateOfBirth,
                    lastDate: DateTime.now());
                if (d != null) setState(() => _on = d);
              },
              icon: const Icon(Icons.calendar_today_outlined),
              label: Text(_df.format(_on)),
            ),
            const SizedBox(height: Space.s3),
            LabeledField(
              label: tr('Illness'),
              controller: _illness,
              hint: tr('For example: diarrhoea, cough, fever'),
              validator: (v) => (v == null || v.trim().isEmpty) ? tr('Write what the illness was') : null,
            ),
            const SizedBox(height: Space.s3),
            LabeledField(
              label: tr('What the clinic gave (optional)'),
              controller: _treatment,
              textInputAction: TextInputAction.done,
            ),
          ]),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text(tr('Cancel'))),
        TextButton(onPressed: _busy ? null : _save, child: Text(tr('Save'))),
      ],
    );
  }
}
