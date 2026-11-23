import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../i18n/strings.dart';
import '../../state/outbox.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/record_charts.dart';

/// The purple book's immunization and vitamin A pages, as tick boxes with the date given
/// and graphs (backend GET /children/{id}/record). The caregiver ticks a dose when the
/// clinic gives it, or copies older ones from the booklet. Ticks made with no signal are
/// kept on the phone and sent later. The CHW sees the same pages without tick boxes.
class HealthRecordScreen extends StatefulWidget {
  const HealthRecordScreen({super.key, required this.child, this.canEdit = true});
  final Child child;
  final bool canEdit;

  @override
  State<HealthRecordScreen> createState() => _HealthRecordScreenState();
}

class _HealthRecordScreenState extends State<HealthRecordScreen> {
  late Future<HealthRecord> _future;

  /// Ticked here with no signal, waiting to be sent: item -> date.
  final Map<String, DateTime> _waiting = {};
  late List<String> _extra = [...widget.child.extraVaccines];

  String get _path => '/children/${widget.child.childId}/record';

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<HealthRecord> _load() async {
    final data = await context.read<Session>().api.get(_path);
    return HealthRecord.fromJson(data as Map<String, dynamic>);
  }

  String _status(Dose d) => _waiting.containsKey(d.item) ? 'given' : d.status;

  Future<void> _tick(Dose d) async {
    final today = DateTime.now();
    final dob = widget.child.dateOfBirth;
    var initial = d.dueOn.isAfter(today) ? today : d.dueOn;
    if (initial.isBefore(dob)) initial = dob;
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: dob,
      lastDate: today,
      helpText: tr('When was {dose} given?', {'dose': d.name}),
    );
    if (picked == null || !mounted) return;
    final session = context.read<Session>();
    try {
      final data = await session.sendOrQueue(
        kind: 'record',
        method: 'put',
        path: '$_path/${d.item}',
        body: {'given_on': DateFormat('yyyy-MM-dd').format(picked)},
        label: tr('{dose} for {name}', {'dose': d.name, 'name': widget.child.firstName}),
      );
      if (!mounted) return;
      setState(() => _future = Future.value(HealthRecord.fromJson(data as Map<String, dynamic>)));
    } on SavedForLater {
      if (!mounted) return;
      setState(() => _waiting[d.item] = picked);
      showMessage(context, tr('No connection. Saved on this phone and will be sent when you are back online.'));
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  Future<void> _untick(Dose d) async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(tr('Untick {dose}?', {'dose': d.name})),
        content: Text(tr('Only do this if it was ticked by mistake.')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('Cancel'))),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: Text(tr('Untick'))),
        ],
      ),
    );
    if (yes != true || !mounted) return;
    try {
      final data = await context.read<Session>().api.delete('$_path/${d.item}');
      if (!mounted) return;
      setState(() => _future = Future.value(HealthRecord.fromJson(data as Map<String, dynamic>)));
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  Future<void> _setExtra(String key, bool on) async {
    final next = {..._extra};
    on ? next.add(key) : next.remove(key);
    try {
      await context
          .read<Session>()
          .api
          .patch('/children/${widget.child.childId}', {'extra_vaccines': next.toList()});
      if (!mounted) return;
      setState(() {
        _extra = next.toList();
        _future = _load();
      });
      context.read<Session>().dataChanged();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text(tr("{name}'s health booklet", {'name': widget.child.firstName})),
          bottom: TabBar(tabs: [
            Tab(text: tr('Vaccines')),
            Tab(text: tr('Vitamin A and deworming')),
          ]),
        ),
        body: AsyncView<HealthRecord>(
          future: _future,
          onRetry: () => setState(() => _future = _load()),
          builder: (context, r) => TabBarView(children: [
            _vaccines(context, r),
            _supplements(context, r),
          ]),
        ),
      ),
    );
  }

  // ---- Vaccines ----

  Widget _vaccines(BuildContext context, HealthRecord r) {
    final t = Theme.of(context).textTheme;
    final c = context.hc;
    final doses = r.of('vaccine');
    final statuses = doses.map(_status).toList();
    int n(String s) => statuses.where((x) => x == s).length;
    final next = doses.where((d) => _status(d) == 'upcoming' || _status(d) == 'due').firstOrNull;
    final visits = <String, List<Dose>>{};
    for (final d in doses) {
      visits.putIfAbsent(d.visit, () => []).add(d);
    }

    return ListView(padding: const EdgeInsets.all(Space.s4), children: [
      HatuaCard(
        child: Row(children: [
          ProgressRing(done: n('given'), total: doses.length),
          const SizedBox(width: Space.s4),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(tr('Vaccines given'), style: t.titleMedium),
              const SizedBox(height: Space.s1),
              if (n('overdue') > 0)
                _line(context, 'overdue',
                    tr('{n} overdue: take the booklet to the clinic.', {'n': n('overdue')})),
              if (n('due') > 0) _line(context, 'due', tr('{n} due now', {'n': n('due')})),
              if (n('not_recorded') > 0)
                _line(context, 'not_recorded',
                    tr('{n} not copied from the booklet yet', {'n': n('not_recorded')})),
              if (next != null)
                Text(tr('Next: {dose}, {date}', {
                  'dose': next.name,
                  'date': DateFormat('d MMM yyyy').format(next.dueOn),
                }), style: t.bodySmall),
              if (n('given') == doses.length && doses.isNotEmpty)
                Text(tr('All vaccines given. Well done!'), style: t.bodyMedium),
            ]),
          ),
        ]),
      ),
      const SizedBox(height: Space.s3),
      HatuaCard(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('Vaccine timeline'), style: t.titleMedium),
          const SizedBox(height: Space.s3),
          VaccineTimeline(
            doses: [
              for (final d in doses)
                Dose(item: d.item, kind: d.kind, name: d.name, visit: d.visit, dueOn: d.dueOn,
                    status: _status(d), givenOn: d.givenOn, optional: d.optional),
            ],
            dateOfBirth: widget.child.dateOfBirth,
          ),
          const SizedBox(height: Space.s3),
          const DoseLegend(),
        ]),
      ),
      if (widget.canEdit) ...[
        const SizedBox(height: Space.s3),
        Text(tr('Tick each vaccine when it is given, or copy it from the booklet.'),
            style: t.bodySmall),
      ],
      for (final v in visits.entries) ...[
        const SizedBox(height: Space.s4),
        Row(children: [
          Expanded(child: Text(v.key, style: t.titleMedium)),
          Text(DateFormat('d MMM yyyy').format(v.value.first.dueOn), style: t.bodySmall),
        ]),
        const SizedBox(height: Space.s2),
        HatuaCard(
          padding: EdgeInsets.zero,
          child: Column(children: [for (final d in v.value) _doseRow(context, d)]),
        ),
      ],
      const SizedBox(height: Space.s6),
      Text(tr('Only in some counties'), style: t.titleMedium),
      Text(tr('Switch these on if your clinic gives them.'), style: t.bodySmall),
      const SizedBox(height: Space.s2),
      HatuaCard(
        padding: EdgeInsets.zero,
        child: Column(children: [
          for (final (key, label) in [
            ('malaria', tr('Malaria vaccine (4 doses, 6 to 24 months)')),
            ('yellow_fever', tr('Yellow fever vaccine (at 9 months)')),
          ])
            SwitchListTile(
              value: _extra.contains(key),
              onChanged: widget.canEdit ? (on) => _setExtra(key, on) : null,
              title: Text(label, style: t.bodyMedium),
            ),
        ]),
      ),
      const SizedBox(height: Space.s3),
      Text(
          tr('The schedule follows the Ministry of Health booklet. The booklet and the clinic stay the official record.'),
          style: t.bodySmall?.copyWith(color: c.muted)),
      const SizedBox(height: Space.s6),
    ]);
  }

  Widget _line(BuildContext context, String status, String text) => Padding(
        padding: const EdgeInsets.only(bottom: 2),
        child: Row(children: [
          DoseMark(status, size: 14),
          const SizedBox(width: 6),
          Expanded(child: Text(text, style: Theme.of(context).textTheme.bodySmall)),
        ]),
      );

  Widget _doseRow(BuildContext context, Dose d) {
    final t = Theme.of(context).textTheme;
    final df = DateFormat('d MMM yyyy');
    final status = _status(d);
    final waiting = _waiting[d.item];
    final sub = switch (status) {
      'given' => waiting != null
          ? tr('Given {date} · waiting to send', {'date': df.format(waiting)})
          : tr('Given {date}', {'date': df.format(d.givenOn!)}),
      'overdue' => tr('Overdue since {date}', {'date': df.format(d.dueOn)}),
      'due' => tr('Due now'),
      'not_recorded' => tr('Not ticked yet. Copy it from the booklet.'),
      _ => tr('Due {date}', {'date': df.format(d.dueOn)}),
    };
    return ListTile(
      leading: DoseMark(status, size: 22),
      title: Text(d.name, style: t.bodyMedium),
      subtitle: Text(sub, style: t.bodySmall),
      trailing: widget.canEdit
          ? Checkbox(
              value: status == 'given',
              onChanged: (_) => status == 'given'
                  ? (waiting == null ? _untick(d) : null)
                  : (d.dueOn.isAfter(DateTime.now()) ? _notYet(d) : _tick(d)),
            )
          : null,
      onTap: !widget.canEdit
          ? null
          : status == 'given'
              ? (waiting == null ? () => _untick(d) : null)
              : () => d.dueOn.isAfter(DateTime.now()) ? _notYet(d) : _tick(d),
    );
  }

  /// A dose that is not due yet can still be ticked (the clinic gave it early), after
  /// a check that this is really what happened.
  Future<void> _notYet(Dose d) async {
    final go = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(tr('Not due yet')),
        content: Text(tr('{dose} is due on {date}. Tick it only if the clinic has already given it.', {
          'dose': d.name,
          'date': DateFormat('d MMM yyyy').format(d.dueOn),
        })),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('Cancel'))),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: Text(tr('It was given'))),
        ],
      ),
    );
    if (go == true) await _tick(d);
  }

  // ---- Vitamin A and deworming ----

  Widget _supplements(BuildContext context, HealthRecord r) {
    final t = Theme.of(context).textTheme;
    Widget section(String kind, String title, String about) {
      final doses = r.of(kind);
      final shown = [
        for (final d in doses)
          Dose(item: d.item, kind: d.kind, name: d.name, visit: d.visit, dueOn: d.dueOn,
              status: _status(d), givenOn: d.givenOn),
      ];
      final given = shown.where((d) => d.given).length;
      return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        HatuaCard(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              ProgressRing(done: given, total: shown.length, size: 72),
              const SizedBox(width: Space.s4),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(title, style: t.titleMedium),
                  Text(about, style: t.bodySmall),
                ]),
              ),
            ]),
            const SizedBox(height: Space.s3),
            DoseDots(doses: shown),
          ]),
        ),
        const SizedBox(height: Space.s2),
        HatuaCard(
          padding: EdgeInsets.zero,
          child: Column(children: [
            for (final d in doses)
              Builder(builder: (context) {
                final row = _doseRow(context, d);
                return row is ListTile
                    ? ListTile(
                        leading: row.leading,
                        title: Text(d.visit, style: t.bodyMedium),
                        subtitle: row.subtitle,
                        trailing: row.trailing,
                        onTap: row.onTap)
                    : row;
              }),
          ]),
        ),
      ]);
    }

    return ListView(padding: const EdgeInsets.all(Space.s4), children: [
      section('vitamin_a', tr('Vitamin A'),
          tr('Every 6 months from 6 months to 5 years. Helps the eyes and fights infection.')),
      const SizedBox(height: Space.s4),
      section('deworming', tr('Deworming'),
          tr('Every 6 months from 1 year to 5 years.')),
      const SizedBox(height: Space.s3),
      const DoseLegend(),
      const SizedBox(height: Space.s6),
    ]);
  }
}
