import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../api/models.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/child_avatar.dart';
import '../../widgets/common.dart';
import '../../widgets/domain.dart';
import '../../widgets/risk_chip.dart';
import '../../widgets/sprout.dart';
import '../messages/thread_screen.dart';
import 'play_ideas.dart';
import '../../i18n/strings.dart';

/// Caregiver results: overall level, one card per domain, and things to try, built from
/// the top reasons the model gave. Worded as actions, never as a diagnosis.
class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.assessment, this.justSubmitted = false});
  final Assessment assessment;
  final bool justSubmitted;

  String get _headline => switch (assessment.riskLevel) {
        'high' => tr("Let's get {childName} checked by a health worker", {'childName': assessment.childName}),
        'medium' => tr("Let's keep an eye on {childName}", {'childName': assessment.childName}),
        _ => tr('{childName} is on track', {'childName': assessment.childName}),
      };

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final a = assessment;
    // Kinds of flag raised by answers (hearing, vision), as apart from growth.
    final screening = a.redFlags.map((f) => f.kind).where((k) => k != 'growth').toSet();
    // Areas not checked at this age (under 24 months) get a note, not a card.
    final domains = a.domains.where((d) => !d.notAssessed).toList()
      ..sort((x, y) => (y.needsSupport ? 1 : 0) - (x.needsSupport ? 1 : 0));
    final notChecked =
        notCheckedNote(context, a.domains.where((d) => d.notAssessed).map((d) => d.domain));

    return Scaffold(
      appBar: AppBar(
        title: Text(justSubmitted ? tr('Results') : tr('Check from {date}', {'date': DateFormat('d MMM yyyy').format(a.submittedAt)})),
        automaticallyImplyLeading: !justSubmitted,
      ),
      body: ListView(padding: EdgeInsets.all(Space.s4), children: [
        HatuaCard(
          padding: EdgeInsets.all(Space.s6),
          child: Column(children: [
            // Cheers only when on track; a concerning result gets the calm, gentle pose.
            Sprout(
                pose: a.riskLevel == 'low' ? SproutPose.cheering : SproutPose.gentle,
                size: 96),
            SizedBox(height: Space.s2),
            Container(
              padding: EdgeInsets.symmetric(horizontal: Space.s3, vertical: Space.s1),
              decoration: BoxDecoration(
                  color: context.hc.sun100, borderRadius: BorderRadius.circular(999)),
              child: Text(justSubmitted ? tr('CHECK COMPLETE') : tr('PAST CHECK'),
                  style: t.labelMedium?.copyWith(color: context.hc.plum900)),
            ),
            SizedBox(height: Space.s3),
            Text(_headline, style: t.headlineSmall, textAlign: TextAlign.center),
            SizedBox(height: Space.s3),
            RiskChip.risk(a.riskLevel),
            SizedBox(height: Space.s4),
            Container(
              padding: EdgeInsets.all(Space.s3),
              decoration: BoxDecoration(
                  color: context.hc.plum100, borderRadius: BorderRadius.circular(Radii.md)),
              child: Row(children: [
                ChildAvatar(childId: a.childId, avatarId: a.childAvatarId, size: 40),
                SizedBox(width: Space.s3),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(a.childName, style: t.labelLarge),
                    Text(
                        '${ageLabel(a.ageMonths)} · ${DateFormat('d MMM yyyy').format(a.submittedAt)}',
                        style: t.bodySmall),
                  ]),
                ),
                Text(
                    tr('{n} of {total} on track', {'n': domains.where((d) => !d.needsSupport).length, 'total': domains.length}),
                    style: t.bodySmall),
              ]),
            ),
            if (a.method == 'milestone_check') ...[
              SizedBox(height: Space.s3),
              Text(tr('At this age the check looks at movement only.'), style: t.bodySmall),
            ],
            if (notChecked != null) ...[
              SizedBox(height: Space.s3),
              Text(notChecked, style: t.bodySmall, textAlign: TextAlign.center),
            ],
          ]),
        ),
        if (a.caregiverMessage != null) ...[
          SizedBox(height: Space.s4),
          HatuaCard(
            color: context.hc.sun100,
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(Icons.health_and_safety_outlined, color: context.hc.plum900),
              SizedBox(width: Space.s3),
              Expanded(child: Text(a.caregiverMessage!, style: t.bodyMedium)),
            ]),
          ),
        ] else if (a.sentToChw) ...[
          SizedBox(height: Space.s4),
          HatuaCard(
            color: context.hc.sun100,
            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Icon(Icons.health_and_safety_outlined, color: context.hc.plum900),
              SizedBox(width: Space.s3),
              Expanded(
                child: Text(
                    tr('Your community health worker will look at this result and may get in touch with you.'),
                    style: t.bodyMedium),
              ),
            ]),
          ),
        ],
        // Hearing, eye and growth flags. Rules, not part of the result above.
        if (a.redFlags.isNotEmpty) ...[
          SizedBox(height: Space.s4),
          HatuaCard(
            color: context.hc.riskMediumBg,
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Icon(Icons.visibility_outlined, color: context.hc.plum900),
                SizedBox(width: Space.s3),
                Expanded(
                    child: Text(
                        tr('{kinds}: worth a check', {'kinds': a.redFlags.map((f) => f.kindLabel).toSet().join(tr(' and '))}),
                        style: t.titleMedium)),
              ]),
              // Hearing and eye flags come from answers; growth flags from the weight and
              // height entered (WHO standard). Each gets its own sentence.
              if (screening.isNotEmpty) ...[
                SizedBox(height: Space.s2),
                Text(
                    tr(screening.length > 1
                            ? "From your answers, {name}'s hearing and eyes should be looked at by a health worker. This is separate from the result above and is not a diagnosis."
                            : screening.contains('hearing')
                                ? "From your answers, {name}'s hearing should be looked at by a health worker. This is separate from the result above and is not a diagnosis."
                                : "From your answers, {name}'s eyes should be looked at by a health worker. This is separate from the result above and is not a diagnosis.",
                        {'name': a.childName}),
                    style: t.bodyMedium),
              ],
              if (a.redFlags.any((f) => f.kind == 'growth')) ...[
                SizedBox(height: Space.s2),
                Text(
                    tr("From the weight and height you entered, {name}'s growth should be checked by a health worker. This is separate from the result above and is not a diagnosis.",
                        {'name': a.childName}),
                    style: t.bodyMedium),
              ],
            ]),
          ),
        ],
        SizedBox(height: Space.s6),
        for (final d in domains) ...[
          _DomainCard(
            domain: d,
            reasons: a.topReasons.where((r) => r.domain == d.domain).toList(),
          ),
          SizedBox(height: Space.s3),
        ],
        SizedBox(height: Space.s3),
        HatuaCard(
          color: context.hc.plum100,
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(Icons.toys_outlined, color: context.hc.plum900),
            SizedBox(width: Space.s3),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(tr('SUGGESTED PLAY'), style: t.labelMedium),
                SizedBox(height: Space.s1),
                Text(playIdeaFor(a.ageMonths).title, style: t.titleMedium),
                SizedBox(height: Space.s1),
                Text(playIdeaFor(a.ageMonths).body.replaceAll('{name}', a.childName),
                    style: t.bodyMedium),
              ]),
            ),
          ]),
        ),
        SizedBox(height: Space.s4),
        Text(
          tr('This check gives a signal, not a diagnosis. If you are worried about your child, visit a health facility.'),
          style: t.bodySmall,
        ),
        SizedBox(height: Space.s4),
        OutlinedButton.icon(
          onPressed: () => Navigator.of(context).push(MaterialPageRoute(
              builder: (_) =>
                  ThreadScreen(predictionId: a.predictionId, aboutChild: a.childName))),
          icon: Icon(Icons.chat_bubble_outline_rounded),
          label: Text(tr('Ask your health worker about this')),
        ),
        SizedBox(height: Space.s2),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(justSubmitted ? tr('Back to home') : tr('Done')),
        ),
      ]),
    );
  }
}

/// Turns a reason's short wording into an action. Mood and behaviour items (ecd39,
/// ecd40) are not skills to practise, so they point to a conversation instead.
String _tip(Reason r) {
  if (r.item.endsWith('39') || r.item.endsWith('40')) {
    return tr('Talk with your health worker about {question}.', {'question': r.question});
  }
  // Movement is one area, but say whether it is big movements or hand skills.
  final kind = r.domain == 'motor' ? motorKindOfItem(r.item) : null;
  final prefix = kind == null ? '' : '${motorKindLabel(kind)}: ';
  final tip = tr('practise {question} together in everyday play.', {'question': r.question});
  return prefix.isEmpty ? '${tip[0].toUpperCase()}${tip.substring(1)}' : '$prefix$tip';
}

class _DomainCard extends StatelessWidget {
  const _DomainCard({required this.domain, required this.reasons});
  final DomainResult domain;
  final List<Reason> reasons;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final style = DomainStyle.of(context, domain.domain);
    return HatuaCard(
      color: domain.needsSupport ? context.hc.riskMediumBg : null,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          DomainBadge(domain.domain),
          SizedBox(width: Space.s3),
          Expanded(child: Text(style.label, style: t.titleLarge)),
        ]),
        SizedBox(height: Space.s2),
        RiskChip.domain(domain.needsSupport),
        if (domain.needsSupport && reasons.isNotEmpty) ...[
          SizedBox(height: Space.s3),
          Text(tr('Things to try this month:'), style: t.labelLarge),
          SizedBox(height: Space.s1),
          for (final r in reasons)
            Padding(
              padding: EdgeInsets.only(top: Space.s1),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('•  ', style: t.bodyMedium),
                Expanded(
                    child: Text(_tip(r), style: t.bodyMedium)),
              ]),
            ),
        ] else if (!domain.needsSupport) ...[
          SizedBox(height: Space.s2),
          Text(tr('Keep playing and talking together every day.'), style: t.bodyMedium),
        ],
      ]),
    );
  }
}
