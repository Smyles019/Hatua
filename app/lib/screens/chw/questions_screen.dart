import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import '../messages/thread_screen.dart';
import 'chw_data.dart';
import '../../i18n/strings.dart';

/// The CHW's Questions inbox (Ask a CHW): one row per linked caregiver who has written,
/// with the questions still waiting for a reply on top.
class QuestionsScreen extends StatefulWidget {
  const QuestionsScreen({super.key});

  @override
  State<QuestionsScreen> createState() => _QuestionsScreenState();
}

class _QuestionsScreenState extends State<QuestionsScreen> {
  Future<List<ThreadSummary>>? _future;
  int _version = -1;

  void _load() {
    final s = context.read<Session>();
    _version = s.dataVersion;
    _future = loadThreads(s.api);
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (_future == null || _version != s.dataVersion) _load();
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: Text(tr('Questions from caregivers'))),
      body: RefreshIndicator(
        color: context.hc.plum700,
        onRefresh: () async {
          setState(_load);
          await _future;
        },
        child: ListView(padding: const EdgeInsets.all(Space.s4), children: [
          AsyncView<List<ThreadSummary>>(
            future: _future!,
            onRetry: () => setState(_load),
            builder: (context, threads) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (threads.isEmpty)
                  EmptyPanel(
                    title: tr('No questions yet'),
                    message: tr('When a caregiver linked to you asks a question, it shows here.'),
                    icon: Icons.chat_bubble_outline_rounded,
                  ),
                for (final th in threads) ...[
                  _row(context, t, th),
                  const SizedBox(height: Space.s2),
                ],
              ],
            ),
          ),
        ]),
      ),
    );
  }

  Widget _row(BuildContext context, TextTheme t, ThreadSummary th) {
    // Waiting rows sit on the yellow tint, which needs the dark "on bright" text.
    final fg = th.waitingForChw ? context.hc.plum900 : null;
    return HatuaCard(
      color: th.waitingForChw ? context.hc.sun100 : null,
      onTap: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) =>
              ThreadScreen(caregiverId: th.caregiverId, caregiverName: th.caregiverName))),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        InitialAvatar(th.caregiverName),
        const SizedBox(width: Space.s3),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(th.caregiverName, style: t.titleMedium?.copyWith(color: fg)),
            Text(th.lastBody,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: t.bodyMedium?.copyWith(color: fg)),
            const SizedBox(height: Space.s1),
            Text(
              '${th.waitingForChw ? 'Waiting for your reply' : 'You replied'} · '
              '${DateFormat('d MMM, HH:mm').format(th.lastAt)}',
              style: t.bodySmall?.copyWith(color: fg),
            ),
          ]),
        ),
      ]),
    );
  }
}
