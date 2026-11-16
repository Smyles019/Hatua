import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import '../messages/danger_signs.dart';
import '../messages/thread_screen.dart';
import '../../i18n/strings.dart';

/// The Hatua assistant: an AI that answers caregivers' questions about development,
/// play and general child care (backend/app/services/assistant.py has the safety
/// design). Only the chosen child's age is sent with a question, never a name. The
/// conversation is saved on the caregiver's account and can be cleared here.
class AssistantScreen extends StatefulWidget {
  const AssistantScreen({super.key, this.childId});

  /// The child to start with (the one open on the home screen); the caregiver can
  /// change it or choose none.
  final String? childId;

  @override
  State<AssistantScreen> createState() => _AssistantScreenState();
}

class _AssistantScreenState extends State<AssistantScreen> {
  final _text = TextEditingController();
  final _scroll = ScrollController();
  Map<String, dynamic>? _state;
  List<Child> _children = [];
  String? _childId;
  Object? _error;
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _childId = widget.childId;
    _load();
  }

  @override
  void dispose() {
    _text.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final api = context.read<Session>().api;
    try {
      final results = await Future.wait([api.get('/assistant'), api.get('/children')]);
      if (!mounted) return;
      setState(() {
        _state = results[0] as Map<String, dynamic>;
        _children = (results[1] as List)
            .map((c) => Child.fromJson(c as Map<String, dynamic>))
            .toList();
        if (_childId != null && !_children.any((c) => c.childId == _childId)) _childId = null;
        _error = null;
      });
      _toEnd();
    } catch (e) {
      if (mounted) setState(() => _error = e);
    }
  }

  void _toEnd() => WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scroll.hasClients) _scroll.jumpTo(_scroll.position.maxScrollExtent);
      });

  Future<void> _send() async {
    final body = _text.text.trim();
    if (body.isEmpty || _sending) return;
    setState(() => _sending = true);
    try {
      final data = await context.read<Session>().api.post('/assistant', {
        'body': body,
        if (_childId != null) 'child_id': _childId,
      });
      _text.clear();
      if (!mounted) return;
      setState(() => _state = data as Map<String, dynamic>);
      _toEnd();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _clear() async {
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(tr('Clear this conversation?')),
        content: Text(tr('Your questions and the answers are deleted from your account.')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('Cancel'))),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(tr('Clear'))),
        ],
      ),
    );
    if (yes != true || !mounted) return;
    try {
      await context.read<Session>().api.delete('/assistant');
      await _load();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = _state;
    final available = s?['available'] == true;
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('Hatua assistant')),
        actions: [
          if (s != null && (s['messages'] as List).isNotEmpty)
            IconButton(
              tooltip: tr('Clear conversation'),
              icon: const Icon(Icons.delete_outline_rounded),
              onPressed: _clear,
            ),
        ],
      ),
      body: SafeArea(
        child: _error != null
            ? ErrorPanel(message: '$_error', onRetry: _load)
            : s == null
                ? Center(child: CircularProgressIndicator(color: context.hc.plum700))
                : Column(children: [
                    Expanded(child: _messages(context, s)),
                    if (available) _composer(context, s) else _off(context),
                  ]),
      ),
    );
  }

  Widget _messages(BuildContext context, Map<String, dynamic> s) {
    final t = Theme.of(context).textTheme;
    final messages = (s['messages'] as List).cast<Map<String, dynamic>>();
    return ListView(controller: _scroll, padding: const EdgeInsets.all(Space.s4), children: [
      HatuaCard(
        color: context.hc.sun100,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(Icons.info_outline_rounded, color: context.hc.plum900),
            const SizedBox(width: Space.s3),
            Expanded(
              child: Text(
                tr('Answers come from AI and can be wrong. It does not diagnose or suggest medicines, and it is not for emergencies. Do not type names or other personal details.'),
                style: t.bodySmall?.copyWith(color: context.hc.plum900),
              ),
            ),
          ]),
          const SizedBox(height: Space.s2),
          Wrap(spacing: Space.s2, children: [
            TextButton.icon(
              onPressed: () => showDangerSigns(context, readOnly: true),
              icon: const Icon(Icons.emergency_outlined),
              label: Text(tr('When to go to a health facility now')),
            ),
            TextButton.icon(
              onPressed: () => Navigator.of(context)
                  .push(MaterialPageRoute(builder: (_) => const ThreadScreen())),
              icon: const Icon(Icons.chat_bubble_outline_rounded),
              label: Text(tr('Chat with your health worker')),
            ),
          ]),
        ]),
      ),
      const SizedBox(height: Space.s3),
      if (messages.isEmpty)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: Space.s6),
          child: Text(
            tr('Ask about how your child is growing, play ideas, feeding, sleep or everyday care.'),
            style: t.bodyMedium,
            textAlign: TextAlign.center,
          ),
        ),
      for (final m in messages) _Bubble(m),
      if (_sending)
        Align(
          alignment: Alignment.centerLeft,
          child: Padding(
            padding: const EdgeInsets.all(Space.s2),
            child: Text(tr('Writing an answer...'), style: t.bodySmall),
          ),
        ),
    ]);
  }

  Widget _off(BuildContext context) => Padding(
        padding: const EdgeInsets.all(Space.s4),
        child: Text(tr('The assistant is not switched on yet.'),
            style: Theme.of(context).textTheme.bodyMedium, textAlign: TextAlign.center),
      );

  Widget _composer(BuildContext context, Map<String, dynamic> s) {
    final t = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(Space.s4, Space.s2, Space.s4, Space.s3),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        if (_children.isNotEmpty)
          SizedBox(
            height: 40,
            child: ListView(scrollDirection: Axis.horizontal, children: [
              Padding(
                padding: const EdgeInsets.only(right: Space.s2),
                child: Center(child: Text(tr('About:'), style: t.labelMedium)),
              ),
              for (final c in _children)
                Padding(
                  padding: const EdgeInsets.only(right: Space.s2),
                  child: ChoiceChip(
                    label: Text('${c.firstName}, ${ageLabel(c.ageMonths)}'),
                    selected: _childId == c.childId,
                    onSelected: (on) => setState(() => _childId = on ? c.childId : null),
                  ),
                ),
            ]),
          ),
        const SizedBox(height: Space.s2),
        Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Expanded(
            child: TextField(
              controller: _text,
              minLines: 1,
              maxLines: 4,
              maxLength: 1000,
              textCapitalization: TextCapitalization.sentences,
              decoration: InputDecoration(hintText: tr('Ask a question'), counterText: ''),
            ),
          ),
          const SizedBox(width: Space.s2),
          IconButton.filled(
            tooltip: tr('Send'),
            onPressed: _sending ? null : _send,
            icon: const Icon(Icons.send_rounded),
          ),
        ]),
        const SizedBox(height: Space.s1),
        Text(
          tr('{used} of {limit} questions today', {'used': s['used_today'], 'limit': s['daily_limit']}),
          style: t.bodySmall,
        ),
      ]),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble(this.message);
  final Map<String, dynamic> message;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final mine = message['role'] == 'user';
    final urgent = message['flagged'] == true && !mine;
    final fg = mine ? context.hc.onPrimary : context.hc.plum900;
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: Space.s2),
        padding: const EdgeInsets.all(Space.s3),
        constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.82),
        decoration: BoxDecoration(
          color: urgent ? context.hc.riskHigh.withValues(alpha: 0.15) : mine ? context.hc.plum700 : context.hc.plum100,
          border: urgent ? Border.all(color: context.hc.riskHigh, width: 2) : null,
          borderRadius: BorderRadius.circular(Radii.md),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
          if (urgent) ...[
            Icon(Icons.emergency_outlined, color: context.hc.riskHigh),
            const SizedBox(width: Space.s2),
          ],
          Flexible(child: Text('${message['body']}', style: t.bodyMedium?.copyWith(color: fg))),
        ]),
      ),
    );
  }
}
