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
import '../../widgets/risk_chip.dart';
import 'chw_data.dart';

/// CHW review of one routed case: domain results with the main reasons, then one of
/// the three fixed outcomes. The caregiver sees a fixed message for the first two.
class CaseReviewScreen extends StatefulWidget {
  const CaseReviewScreen({super.key, required this.assessment});
  final Assessment assessment;

  @override
  State<CaseReviewScreen> createState() => _CaseReviewScreenState();
}

class _CaseReviewScreenState extends State<CaseReviewScreen> {
  String? _outcome;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _outcome = widget.assessment.chwOutcome;
  }

  Future<void> _save() async {
    setState(() => _busy = true);
    final session = context.read<Session>();
    try {
      await session.api.post('/chw/cases/${widget.assessment.predictionId}/outcome',
          {'outcome': _outcome});
      session.dataChanged();
      if (mounted) {
        showMessage(context, 'Outcome saved for ${widget.assessment.childName}.');
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final a = widget.assessment;
    final domains = [...a.domains]
      ..sort((x, y) => (y.needsSupport ? 1 : 0) - (x.needsSupport ? 1 : 0));

    return Scaffold(
      appBar: AppBar(title: Text(a.childName)),
      body: ListView(padding: EdgeInsets.all(Space.s4), children: [
        HatuaCard(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              ChildAvatar(childId: a.childId, avatarId: a.childAvatarId, size: 56),
              SizedBox(width: Space.s3),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${a.childName}, ${ageLabel(a.ageMonths)}', style: t.titleLarge),
                  if (a.caregiverName != null)
                    Text('Caregiver: ${a.caregiverName} · ${a.caregiverPhone ?? ''}',
                        style: t.bodySmall),
                  if (a.location != null) Text(a.location!, style: t.bodySmall),
                  Text('Checked ${DateFormat('d MMM yyyy, HH:mm').format(a.submittedAt)}',
                      style: t.bodySmall),
                ]),
              ),
            ]),
            SizedBox(height: Space.s3),
            Wrap(spacing: Space.s2, runSpacing: Space.s2, children: [
              RiskChip.risk(a.riskLevel, audience: Audience.chw),
              if (a.anomalyFlag) RiskChip.anomaly(),
            ]),
            if (a.anomalyFlag) ...[
              SizedBox(height: Space.s2),
              Text(
                'Some answers do not fit together the way they usually do. Go through the '
                'questions with the caregiver before deciding.',
                style: t.bodyMedium,
              ),
            ],
            if (a.method == 'milestone_check') ...[
              SizedBox(height: Space.s2),
              Text('Under 24 months: WHO movement milestones only.', style: t.bodySmall),
            ],
          ]),
        ),
        SizedBox(height: Space.s4),
        for (final d in domains) ...[
          _ReviewDomain(
              domain: d,
              reasons: a.topReasons.where((r) => r.domain == d.domain).toList(),
              answers: a.answers),
          SizedBox(height: Space.s2),
        ],
        SizedBox(height: Space.s4),
        Text('Log outcome', style: t.titleLarge),
        SizedBox(height: Space.s1),
        Text('The caregiver sees a short message for the first two.', style: t.bodySmall),
        SizedBox(height: Space.s3),
        for (final e in outcomeLabels.entries) ...[
          ChoiceOption(
            label: e.value,
            selected: _outcome == e.key,
            onTap: () => setState(() => _outcome = e.key),
          ),
          SizedBox(height: Space.s2),
        ],
        SizedBox(height: Space.s3),
        FilledButton(
          onPressed: _outcome == null || _busy ? null : _save,
          child: Text(_busy ? 'Saving...' : 'Save outcome'),
        ),
        if (a.reviewedAt != null) ...[
          SizedBox(height: Space.s2),
          Text('Last saved ${DateFormat('d MMM yyyy').format(a.reviewedAt!)}.',
              style: t.bodySmall, textAlign: TextAlign.center),
        ],
      ]),
    );
  }
}

class _ReviewDomain extends StatelessWidget {
  const _ReviewDomain({required this.domain, required this.reasons, required this.answers});
  final DomainResult domain;
  final List<Reason> reasons;
  final Map<String, String> answers;

  /// The caregiver's stored answer value, readable ("dont_know" -> "don't know").
  String _answer(String item) {
    final v = answers[item];
    if (v == null) return '';
    final text = v == 'dont_know' ? "don't know" : v.replaceAll('_', ' ');
    return ' (answered: $text)';
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return HatuaCard(
      color: domain.needsSupport ? context.hc.riskMediumBg : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          DomainBadge(domain.domain),
          SizedBox(width: Space.s3),
          Expanded(child: Text(DomainStyle.of(context, domain.domain).label, style: t.titleMedium)),
          RiskChip.domain(domain.needsSupport),
        ]),
        if (reasons.isNotEmpty) ...[
          SizedBox(height: Space.s3),
          Text('Main reasons', style: t.labelLarge),
          for (final r in reasons)
            Padding(
              padding: EdgeInsets.only(top: Space.s1),
              child: Text('•  ${r.question}${_answer(r.item)}', style: t.bodyMedium),
            ),
        ],
      ]),
    );
  }
}
