import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import 'case_review_screen.dart';
import 'chw_data.dart';
import 'flagged_screen.dart';
import 'link_caregiver_screen.dart';
import 'questions_screen.dart';
import '../../i18n/strings.dart';

class _HomeData {
  _HomeData(this.open, this.all, this.caregivers, this.threads);
  final List<Assessment> open;
  final List<Assessment> all;
  final List<LinkedCaregiver> caregivers;
  final List<ThreadSummary> threads;

  int get questionsWaiting => threads.where((t) => t.waitingForChw).length;

  int get reviewedThisWeek {
    final since = DateTime.now().subtract(Duration(days: 7));
    return all.where((a) => a.reviewedAt != null && a.reviewedAt!.isAfter(since)).length;
  }
}

class ChwHomeTab extends StatefulWidget {
  const ChwHomeTab({super.key});

  @override
  State<ChwHomeTab> createState() => _ChwHomeTabState();
}

class _ChwHomeTabState extends State<ChwHomeTab> {
  Future<_HomeData>? _future;
  int _version = -1;

  void _load() {
    final s = context.read<Session>();
    _version = s.dataVersion;
    _future = () async {
      final r = await Future.wait([
        loadCases(s.api),
        loadCases(s.api, includeReviewed: true),
        loadCaregivers(s.api),
        loadThreads(s.api),
      ]);
      return _HomeData(r[0] as List<Assessment>, r[1] as List<Assessment>,
          r[2] as List<LinkedCaregiver>, r[3] as List<ThreadSummary>);
    }();
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (_future == null || _version != s.dataVersion) _load();
    final t = Theme.of(context).textTheme;

    return RefreshIndicator(
      color: context.hc.plum700,
      onRefresh: () async {
        setState(_load);
        await _future;
      },
      child: ListView(padding: EdgeInsets.zero, children: [
        BlobHeader(
          title: tr('Hello, {name}', {'name': s.user?.firstName ?? ''}),
          subtitle: tr('Children who need a follow-up are listed under Flagged.'),
          variant: 1,
        ),
        Padding(
          padding: EdgeInsets.all(Space.s4),
          child: AsyncView<_HomeData>(
            future: _future!,
            onRetry: () => setState(_load),
            builder: (context, d) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(children: [
                  Expanded(
                    child: _Tile(
                      value: d.open.length,
                      label: tr('Flagged to review'),
                      color: d.open.isEmpty ? context.hc.riskLowBg : context.hc.riskMediumBg,
                      onTap: () => Navigator.of(context).push(
                          MaterialPageRoute(builder: (_) => FlaggedScreen())),
                    ),
                  ),
                  SizedBox(width: Space.s3),
                  Expanded(
                    child: _Tile(
                        value: d.reviewedThisWeek,
                        label: tr('Reviewed this week'),
                        color: context.hc.sky100),
                  ),
                  SizedBox(width: Space.s3),
                  Expanded(
                    child: _Tile(
                        value: d.caregivers.length,
                        label: tr('Caregivers linked'),
                        color: context.hc.sun100),
                  ),
                ]),
                SizedBox(height: Space.s3),
                _QuestionsCard(waiting: d.questionsWaiting),
                SizedBox(height: Space.s6),
                Text(tr('Most recent flags'), style: t.titleLarge),
                SizedBox(height: Space.s3),
                if (d.open.isEmpty)
                  EmptyPanel(
                    title: tr('All caught up'),
                    message: tr('No children need a follow-up right now.'),
                    icon: Icons.check_circle_outline_rounded,
                  ),
                for (final a in d.open.take(3)) ...[
                  CaseCard(
                      assessment: a,
                      onTap: () => Navigator.of(context).push(MaterialPageRoute(
                          builder: (_) => CaseReviewScreen(assessment: a)))),
                  SizedBox(height: Space.s2),
                ],
                SizedBox(height: Space.s4),
                FilledButton.icon(
                  style: secondaryButtonStyle(context),
                  onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => LinkCaregiverScreen())),
                  icon: Icon(Icons.person_add_alt_1_outlined),
                  label: Text(tr('Link or enrol a caregiver')),
                ),
              ],
            ),
          ),
        ),
      ]),
    );
  }
}

/// Ask a CHW: opens the Questions inbox, highlighted while a question is waiting.
class _QuestionsCard extends StatelessWidget {
  const _QuestionsCard({required this.waiting});
  final int waiting;

  @override
  Widget build(BuildContext context) {
    final fg = waiting > 0 ? context.hc.plum900 : context.hc.plum900;
    return HatuaCard(
      color: waiting > 0 ? context.hc.sun100 : null,
      onTap: () => Navigator.of(context)
          .push(MaterialPageRoute(builder: (_) => const QuestionsScreen())),
      child: Row(children: [
        Icon(Icons.chat_bubble_outline_rounded, color: fg),
        SizedBox(width: Space.s3),
        Expanded(
          child: Text(
            waiting == 0
                ? tr('Questions from caregivers')
                : waiting == 1
                    ? tr('1 question is waiting for your reply')
                    : tr('{waiting} questions are waiting for your reply', {'waiting': waiting}),
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(color: waiting > 0 ? context.hc.plum900 : null),
          ),
        ),
        Icon(Icons.chevron_right_rounded, color: fg),
      ]),
    );
  }
}

class _Tile extends StatelessWidget {
  const _Tile({required this.value, required this.label, required this.color, this.onTap});
  final int value;
  final String label;
  final Color color;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return HatuaCard(
      color: color,
      onTap: onTap,
      padding: EdgeInsets.all(Space.s3),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('$value', style: t.headlineSmall),
        SizedBox(height: Space.s1),
        Text(label, style: t.bodySmall?.copyWith(color: context.hc.plum900)),
      ]),
    );
  }
}
