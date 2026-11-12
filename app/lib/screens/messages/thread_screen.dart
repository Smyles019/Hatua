import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import 'danger_signs.dart';
import '../../i18n/strings.dart';

/// Ask a CHW: one caregiver's message thread with their community health worker.
///
/// Not live chat: the caregiver writes, the CHW replies when they can. The same screen
/// serves both sides. For a caregiver [caregiverId] is null (their own thread); for a
/// CHW it is the caregiver whose thread is open.
class ThreadScreen extends StatefulWidget {
  const ThreadScreen(
      {super.key, this.caregiverId, this.caregiverName, this.predictionId, this.aboutChild});

  final String? caregiverId;
  final String? caregiverName;

  /// Caregiver only: the check this question is about (asked from a result screen).
  final String? predictionId;
  final String? aboutChild;

  bool get asChw => caregiverId != null;

  @override
  State<ThreadScreen> createState() => _ThreadScreenState();
}

class _ThreadScreenState extends State<ThreadScreen> {
  late Future<MessageThread> _future;
  final _text = TextEditingController();
  final _scroll = ScrollController();
  bool _sending = false;

  /// The danger signs are shown once per visit to this screen, before the first send.
  bool _sawDangerSigns = false;

  String get _path => widget.asChw ? '/messages/threads/${widget.caregiverId}' : '/messages';

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  @override
  void dispose() {
    _text.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<MessageThread> _load() async {
    final data = await context.read<Session>().api.get(_path);
    return MessageThread.fromJson(data as Map<String, dynamic>);
  }

  Future<void> _send() async {
    final body = _text.text.trim();
    if (body.isEmpty) return;
    if (!widget.asChw && !_sawDangerSigns) {
      final go = await showDangerSigns(context);
      if (go != true || !mounted) return;
      _sawDangerSigns = true;
    }
    setState(() => _sending = true);
    final session = context.read<Session>();
    try {
      final data = await session.api.post(_path, {
        'body': body,
        if (!widget.asChw && widget.predictionId != null) 'prediction_id': widget.predictionId,
      });
      final thread = MessageThread.fromJson(data as Map<String, dynamic>);
      _text.clear();
      session.dataChanged();
      if (!mounted) return;
      setState(() => _future = Future.value(thread));
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scroll.hasClients) _scroll.jumpTo(_scroll.position.maxScrollExtent);
      });
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title:
            Text(widget.asChw ? (widget.caregiverName ?? tr('Question')) : tr('Ask your health worker')),
        actions: [
          IconButton(
            tooltip: tr('Refresh'),
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => setState(() => _future = _load()),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(children: [
          Expanded(
            child: AsyncView<MessageThread>(
              future: _future,
              onRetry: () => setState(() => _future = _load()),
              builder: (context, thread) => _messages(context, thread),
            ),
          ),
          _composer(context),
        ]),
      ),
    );
  }

  Widget _messages(BuildContext context, MessageThread thread) {
    final t = Theme.of(context).textTheme;
    return ListView(controller: _scroll, padding: const EdgeInsets.all(Space.s4), children: [
      if (!widget.asChw) ...[
        HatuaCard(
          color: context.hc.sun100,
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(Icons.info_outline_rounded, color: context.hc.plum900),
            const SizedBox(width: Space.s3),
            Expanded(
              child: Text(
                thread.chwName == null
                    ? tr('You are not linked to a community health worker yet. You can still write your question; it will reach them once you are linked.')
                    : tr('{chwName} is your community health worker. They reply when they can, often within a day or two. This is not for emergencies.', {'chwName': thread.chwName}),
                style: t.bodySmall?.copyWith(color: context.hc.plum900),
              ),
            ),
          ]),
        ),
        const SizedBox(height: Space.s2),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: () => showDangerSigns(context, readOnly: true),
            icon: const Icon(Icons.emergency_outlined),
            label: Text(tr('When to go to a health facility now')),
          ),
        ),
        const SizedBox(height: Space.s2),
      ],
      if (thread.messages.isEmpty)
        Padding(
          padding: const EdgeInsets.symmetric(vertical: Space.s6),
          child: Text(
            widget.asChw
                ? tr('No messages yet.')
                : widget.aboutChild == null
                    ? tr('Write your question below.')
                    : tr("Write your question about {aboutChild}'s check below.", {'aboutChild': widget.aboutChild}),
            style: t.bodyMedium,
            textAlign: TextAlign.center,
          ),
        ),
      for (final m in thread.messages) _Bubble(m),
      if (thread.messages.isNotEmpty) ...[
        const SizedBox(height: Space.s2),
        Center(
          child: Text(
            thread.waitingForChw
                ? (widget.asChw ? tr('Waiting for your reply') : tr('Sent. Waiting for a reply.'))
                : (widget.asChw ? tr('You replied') : tr('Answered')),
            style: t.labelMedium,
          ),
        ),
      ],
    ]);
  }

  Widget _composer(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(Space.s4, Space.s2, Space.s4, Space.s3),
      child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
        Expanded(
          child: TextField(
            controller: _text,
            minLines: 1,
            maxLines: 4,
            maxLength: 1000,
            textCapitalization: TextCapitalization.sentences,
            decoration: InputDecoration(
              hintText: widget.asChw ? tr('Write your reply') : tr('Write your question'),
              counterText: '',
            ),
          ),
        ),
        const SizedBox(width: Space.s2),
        IconButton.filled(
          tooltip: tr('Send'),
          onPressed: _sending ? null : _send,
          icon: const Icon(Icons.send_rounded),
        ),
      ]),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble(this.message);
  final ThreadMessage message;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final mine = message.fromMe;
    final fg = mine ? context.hc.onPrimary : context.hc.plum900;
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: Space.s2),
        padding: const EdgeInsets.all(Space.s3),
        constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.78),
        decoration: BoxDecoration(
          color: mine ? context.hc.plum700 : context.hc.plum100,
          borderRadius: BorderRadius.circular(Radii.md),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (message.aboutChild != null) ...[
            Text(tr("About {aboutChild}'s check", {'aboutChild': message.aboutChild}),
                style: t.labelMedium?.copyWith(color: fg)),
            const SizedBox(height: Space.s1),
          ],
          Text(message.body, style: t.bodyMedium?.copyWith(color: fg)),
          const SizedBox(height: Space.s1),
          Text(
            '${mine ? 'You' : message.senderName} · '
            '${DateFormat('d MMM, HH:mm').format(message.createdAt)}',
            style: t.bodySmall?.copyWith(color: fg),
          ),
        ]),
      ),
    );
  }
}
