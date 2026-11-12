import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/pending_check.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/child_avatar.dart';
import '../../widgets/common.dart';
import '../../widgets/domain.dart';
import '../../widgets/sprout.dart';
import 'result_screen.dart';
import '../../i18n/strings.dart';

/// The caregiver milestone check: one question per screen, answers as the backend
/// offers them (Yes / No / Don't know, or frequency options for two items).
class CheckScreen extends StatefulWidget {
  const CheckScreen({super.key, required this.child});
  final Child child;

  @override
  State<CheckScreen> createState() => _CheckScreenState();
}

class _CheckScreenState extends State<CheckScreen> {
  late Future<Questionnaire> _future;
  final Map<String, String> _answers = {};
  int _index = 0;
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Questionnaire> _load() async {
    final api = context.read<Session>().api;
    final data = await api.get('/assessments/questions', {'child_id': widget.child.childId});
    return Questionnaire.fromJson(data as Map<String, dynamic>);
  }

  Future<bool> _confirmLeave() async {
    if (_answers.isEmpty) return true;
    final leave = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(tr('Stop this check?')),
        content: Text(tr('Your answers so far will not be saved.')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('Keep going'))),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: Text(tr('Stop'))),
        ],
      ),
    );
    return leave ?? false;
  }

  Future<void> _submit(Questionnaire q) async {
    setState(() => _sending = true);
    final session = context.read<Session>();
    try {
      final data = await session.api
          .post('/assessments', {'child_id': q.childId, 'responses': _answers});
      final result = Assessment.fromJson(data as Map<String, dynamic>);
      session.dataChanged();
      if (!mounted) return;
      await Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => ResultScreen(assessment: result, justSubmitted: true)));
    } catch (e) {
      if (classifySendError(e) == SendFailure.retryLater) {
        // No connection or the server is down: keep the answers on the phone (#8).
        await session.savePending(PendingCheck(
          childId: q.childId,
          childName: widget.child.firstName,
          responses: Map.of(_answers),
          savedAt: DateTime.now(),
        ));
        if (!mounted) return;
        await _showSavedForLater();
        if (mounted) Navigator.of(context).pop();
        return;
      }
      if (mounted) {
        showError(context, e);
        setState(() => _sending = false);
      }
    }
  }

  Future<void> _showSavedForLater() => showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text(tr('Saved on this phone')),
          content: Text(tr("We couldn't send {firstName}'s check right now. Your answers are saved and will be sent when you are back online. You can also send them from the home screen.", {'firstName': widget.child.firstName})),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx), child: Text(tr('OK'))),
          ],
        ),
      );

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        if (_index > 0) {
          setState(() => _index--);
          return;
        }
        final nav = Navigator.of(context);
        if (await _confirmLeave()) nav.pop();
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(tr("{firstName}'s check", {'firstName': widget.child.firstName})),
          leading: IconButton(
            tooltip: tr('Close'),
            icon: Icon(Icons.close_rounded),
            onPressed: () async {
              final nav = Navigator.of(context);
              if (await _confirmLeave()) nav.pop();
            },
          ),
        ),
        body: AsyncView<Questionnaire>(
          future: _future,
          onRetry: () => setState(() {
            _future = _load();
          }),
          builder: (context, q) => _question(context, q),
        ),
      ),
    );
  }

  Widget _question(BuildContext context, Questionnaire q) {
    final t = Theme.of(context).textTheme;
    final total = q.questions.length;
    final question = q.questions[_index];
    final selected = _answers[question.item];
    final last = _index == total - 1;

    return SafeArea(
      child: ListView(padding: EdgeInsets.all(Space.s4), children: [
        Row(children: [
          ChildAvatar(childId: widget.child.childId, avatarId: widget.child.avatarId, size: 40),
          SizedBox(width: Space.s3),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(tr('Check for {firstName}', {'firstName': widget.child.firstName}), style: t.titleMedium),
              Text(ageLabel(widget.child.ageMonths), style: t.bodySmall),
            ]),
          ),
          Container(
            padding: EdgeInsets.symmetric(horizontal: Space.s3, vertical: Space.s1),
            decoration: BoxDecoration(
                color: context.hc.sun100, borderRadius: BorderRadius.circular(999)),
            child: Text('${_index + 1} of $total',
                style: t.labelMedium?.copyWith(color: context.hc.plum900)),
          ),
        ]),
        SizedBox(height: Space.s3),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: LinearProgressIndicator(
            value: (_index + 1) / total,
            minHeight: 8,
            backgroundColor: context.hc.plum100,
            color: context.hc.plum700,
          ),
        ),
        SizedBox(height: Space.s4),
        HatuaCard(
          padding: EdgeInsets.all(Space.s4),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              // The last few questions are the hearing and eye checks, not a domain.
              question.screening == null
                  ? DomainTag(DomainStyle.domainOfItem(question.item))
                  : ScreeningTag(question.screening!),
              Spacer(),
              const Sprout(pose: SproutPose.thinking, size: 56, bob: false),
            ]),
            SizedBox(height: Space.s3),
            Text(question.text, style: t.headlineSmall),
            // The example under the question, so the question itself stays short.
            if (question.hint != null) ...[
              SizedBox(height: Space.s1),
              Text(question.hint!, style: t.bodyLarge),
            ],
            SizedBox(height: Space.s2),
            Text(
                question.screening == null
                    ? tr('Think about what {firstName} does on most days.', {'firstName': widget.child.firstName})
                    : tr("A quick check of hearing and eyes. If you are not sure, choose Don't know."),
                style: t.bodySmall),
          ]),
        ),
        SizedBox(height: Space.s4),
        for (final o in question.options) ...[
          ChoiceOption(
            label: o.label,
            selected: selected == o.value,
            onTap: () => setState(() => _answers[question.item] = o.value),
          ),
          SizedBox(height: Space.s2),
        ],
        SizedBox(height: Space.s4),
        FilledButton(
          onPressed: selected == null || _sending
              ? null
              : () {
                  if (last) {
                    _submit(q);
                  } else {
                    setState(() => _index++);
                  }
                },
          child: Text(_sending
              ? tr('Getting results...')
              : last
                  ? tr('See results')
                  : tr('Next question')),
        ),
        if (_index > 0) ...[
          SizedBox(height: Space.s2),
          TextButton(
            onPressed: _sending ? null : () => setState(() => _index--),
            child: Text(tr('Back to previous question')),
          ),
        ],
      ]),
    );
  }
}
