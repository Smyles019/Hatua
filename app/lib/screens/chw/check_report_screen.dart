import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../api/api_client.dart';
import '../../i18n/strings.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/domain.dart';
import '../../widgets/risk_chip.dart';

/// CHW only: the full report of one check, every question the caregiver was asked and
/// the answer they gave, by area, with the hearing and eye questions at the end
/// (backend app/services/report.py). The PDF opens in the phone's browser through a
/// link that works for a few minutes.
class CheckReportScreen extends StatefulWidget {
  const CheckReportScreen({super.key, required this.predictionId, required this.childName});
  final String predictionId;
  final String childName;

  @override
  State<CheckReportScreen> createState() => _CheckReportScreenState();
}

class _CheckReportScreenState extends State<CheckReportScreen> {
  late Future<Map<String, dynamic>> _future;
  bool _opening = false;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Map<String, dynamic>> _load() async {
    final data = await context
        .read<Session>()
        .api
        .get('/chw/cases/${widget.predictionId}/report');
    return data as Map<String, dynamic>;
  }

  Future<void> _openPdf() async {
    setState(() => _opening = true);
    try {
      final data = await context
          .read<Session>()
          .api
          .post('/chw/cases/${widget.predictionId}/report-link');
      final url = Uri.parse((data as Map<String, dynamic>)['url'] as String);
      final ok = await launchUrl(url, mode: LaunchMode.externalApplication);
      if (!ok) throw ApiException(0, tr('Could not open the PDF on this phone.'));
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _opening = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('Full report: {name}', {'name': widget.childName})),
        actions: [
          IconButton(
            tooltip: tr('Open as PDF'),
            icon: const Icon(Icons.picture_as_pdf_outlined),
            onPressed: _opening ? null : _openPdf,
          ),
        ],
      ),
      body: AsyncView<Map<String, dynamic>>(
        future: _future,
        onRetry: () => setState(() => _future = _load()),
        builder: (context, r) => _report(context, r),
      ),
    );
  }

  Widget _report(BuildContext context, Map<String, dynamic> r) {
    final t = Theme.of(context).textTheme;
    final child = r['child'] as Map<String, dynamic>;
    final caregiver = r['caregiver'] as Map<String, dynamic>;
    final counts = r['counts'] as Map<String, dynamic>;
    final flags = (r['red_flags'] as List).cast<Map<String, dynamic>>();
    final sections = (r['sections'] as List).cast<Map<String, dynamic>>();
    final screening = (r['screening'] as List).cast<Map<String, dynamic>>();
    final when = DateFormat('d MMM yyyy, HH:mm')
        .format(DateTime.parse(r['submitted_at'] as String).toLocal());

    return ListView(padding: const EdgeInsets.all(Space.s4), children: [
      HatuaCard(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${child['first_name']}, ${ageLabel(r['age_months'] as int)}', style: t.titleLarge),
          Text(tr('Caregiver: {name} · {phone}',
              {'name': caregiver['full_name'], 'phone': caregiver['phone_number'] ?? ''}),
              style: t.bodySmall),
          Text(tr('Checked {when}', {'when': when}), style: t.bodySmall),
          const SizedBox(height: Space.s2),
          Wrap(spacing: Space.s2, runSpacing: Space.s2, children: [
            RiskChip.risk(r['risk_level'] as String, audience: Audience.chw),
            if (r['anomaly_flag'] == true) RiskChip.anomaly(),
          ]),
          if (r['outcome_label'] != null) ...[
            const SizedBox(height: Space.s2),
            Text(tr('Outcome: {outcome}', {'outcome': r['outcome_label']}), style: t.bodyMedium),
          ],
          const SizedBox(height: Space.s2),
          Text(
            tr('{done} achieved, {not_yet} not yet, {dont_know} not sure.', {
              'done': counts['done'],
              'not_yet': counts['not_yet'],
              'dont_know': counts['dont_know'],
            }),
            style: t.bodyMedium,
          ),
        ]),
      ),
      if (flags.isNotEmpty) ...[
        const SizedBox(height: Space.s3),
        HatuaCard(
          color: context.hc.riskHighBg,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(tr('Hearing, vision and growth flags'), style: t.titleMedium),
            for (final f in flags)
              Padding(
                padding: const EdgeInsets.only(top: Space.s1),
                child: Text('•  ${f['kind_label']}: ${f['label']}', style: t.bodyMedium),
              ),
          ]),
        ),
      ],
      for (final s in sections) ...[
        const SizedBox(height: Space.s4),
        Row(children: [
          DomainBadge(s['domain'] as String),
          const SizedBox(width: Space.s3),
          Expanded(child: Text(s['label'] as String, style: t.titleMedium)),
          if (s['status'] != 'not_assessed') RiskChip.domain(s['status'] == 'needs_support'),
        ]),
        const SizedBox(height: Space.s2),
        for (final a in (s['answers'] as List).cast<Map<String, dynamic>>()) _AnswerRow(a),
      ],
      if (screening.isNotEmpty) ...[
        const SizedBox(height: Space.s4),
        Text(tr('Hearing and eyes'), style: t.titleMedium),
        const SizedBox(height: Space.s2),
        for (final a in screening) _AnswerRow(a),
      ],
      const SizedBox(height: Space.s4),
      FilledButton.icon(
        onPressed: _opening ? null : _openPdf,
        icon: const Icon(Icons.picture_as_pdf_outlined),
        label: Text(_opening ? tr('Opening...') : tr('Open as PDF')),
      ),
      const SizedBox(height: Space.s2),
      Text(tr('The PDF opens in your browser, where you can save, print or share it.'),
          style: t.bodySmall, textAlign: TextAlign.center),
    ]);
  }
}

/// One question and the caregiver's answer. The icon carries the meaning as well as the
/// colour, so the list reads the same in black and white.
class _AnswerRow extends StatelessWidget {
  const _AnswerRow(this.a);
  final Map<String, dynamic> a;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final (IconData icon, String meaning) = switch (a['result']) {
      'done' => (Icons.check_circle_outline_rounded, tr('Achieved')),
      'not_yet' => (Icons.remove_circle_outline_rounded, tr('Not yet')),
      'concern' => (Icons.error_outline_rounded, tr('Needs a look')),
      'ok' => (Icons.check_circle_outline_rounded, ''),
      _ => (Icons.help_outline_rounded, tr('Not sure')),
    };
    final highlight = a['result'] == 'not_yet' || a['result'] == 'concern';
    return Container(
      margin: const EdgeInsets.only(bottom: Space.s2),
      padding: const EdgeInsets.all(Space.s3),
      decoration: BoxDecoration(
        color: highlight ? context.hc.riskMediumBg : context.hc.plum100.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(Radii.md),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon, size: 20, color: context.hc.plum900),
        const SizedBox(width: Space.s3),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(a['question'] as String, style: t.bodyMedium?.copyWith(color: context.hc.plum900)),
            const SizedBox(height: Space.s1),
            Text(
              meaning.isEmpty
                  ? tr('Answer: {answer}', {'answer': a['answer_label']})
                  : tr('Answer: {answer} ({meaning})', {'answer': a['answer_label'], 'meaning': meaning}),
              style: t.bodySmall?.copyWith(color: context.hc.plum900, fontWeight: FontWeight.w600),
            ),
          ]),
        ),
      ]),
    );
  }
}
