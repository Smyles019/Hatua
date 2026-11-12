import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/child_avatar.dart';
import '../../widgets/common.dart';
import '../../widgets/risk_chip.dart';
import 'case_review_screen.dart';
import 'chw_data.dart';
import '../../i18n/strings.dart';

/// Open cases routed to this CHW, newest first, filterable by level.
class FlaggedScreen extends StatefulWidget {
  const FlaggedScreen({super.key});

  @override
  State<FlaggedScreen> createState() => _FlaggedScreenState();
}

enum _Filter { all, high, medium, unusual }

class _FlaggedScreenState extends State<FlaggedScreen> {
  Future<List<Assessment>>? _future;
  int _version = -1;
  _Filter _filter = _Filter.all;

  void _load() {
    final s = context.read<Session>();
    _version = s.dataVersion;
    _future = loadCases(s.api);
  }

  bool _keep(Assessment a) => switch (_filter) {
        _Filter.all => true,
        _Filter.high => a.riskLevel == 'high',
        _Filter.medium => a.riskLevel == 'medium',
        _Filter.unusual => a.anomalyFlag,
      };

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (_future == null || _version != s.dataVersion) _load();
    return Scaffold(
      appBar: AppBar(title: Text(tr('Flagged children'))),
      body: RefreshIndicator(
        color: context.hc.plum700,
        onRefresh: () async {
          setState(_load);
          await _future;
        },
        child: ListView(padding: EdgeInsets.all(Space.s4), children: [
          Wrap(spacing: Space.s2, runSpacing: Space.s2, children: [
            _chip(tr('All'), _Filter.all),
            _chip(tr('High'), _Filter.high),
            _chip(tr('Medium'), _Filter.medium),
            _chip(tr('Unusual answers'), _Filter.unusual),
          ]),
          SizedBox(height: Space.s4),
          AsyncView<List<Assessment>>(
            future: _future!,
            onRetry: () => setState(_load),
            builder: (context, cases) {
              final shown = cases.where(_keep).toList();
              if (shown.isEmpty) {
                return EmptyPanel(
                  title: tr('All caught up'),
                  message: tr('No children in this list need a follow-up right now.'),
                  icon: Icons.check_circle_outline_rounded,
                );
              }
              return Column(children: [
                for (final a in shown) ...[
                  CaseCard(
                    assessment: a,
                    onTap: () => Navigator.of(context).push(MaterialPageRoute(
                        builder: (_) => CaseReviewScreen(assessment: a))),
                  ),
                  SizedBox(height: Space.s2),
                ],
              ]);
            },
          ),
        ]),
      ),
    );
  }

  Widget _chip(String label, _Filter f) {
    final on = _filter == f;
    return ChoiceChip(
      label: Text(label),
      selected: on,
      showCheckmark: false,
      selectedColor: context.hc.plum700,
      backgroundColor: context.hc.plum100,
      labelStyle: Theme.of(context)
          .textTheme
          .labelLarge
          ?.copyWith(color: on ? context.hc.onPrimary : context.hc.plum900),
      shape: StadiumBorder(side: BorderSide(color: context.hc.plum200)),
      onSelected: (_) => setState(() => _filter = f),
    );
  }
}

/// One routed case in a CHW list.
class CaseCard extends StatelessWidget {
  const CaseCard({super.key, required this.assessment, this.onTap});
  final Assessment assessment;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final a = assessment;
    return HatuaCard(
      onTap: onTap,
      child: Row(children: [
        ChildAvatar(childId: a.childId, avatarId: a.childAvatarId),
        SizedBox(width: Space.s3),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${a.childName} · ${ageLabel(a.ageMonths)}', style: t.titleMedium),
            if (a.caregiverName != null) Text(tr('Caregiver: {caregiverName}', {'caregiverName': a.caregiverName}), style: t.bodySmall),
            Text(tr('Checked {when}', {'when': DateFormat('d MMM yyyy').format(a.submittedAt)}),
                style: t.bodySmall),
            SizedBox(height: Space.s2),
            Wrap(spacing: Space.s2, runSpacing: Space.s2, children: [
              if (a.riskLevel != 'low') RiskChip.risk(a.riskLevel, audience: Audience.chw),
              if (a.anomalyFlag) RiskChip.anomaly(),
            ]),
          ]),
        ),
        Icon(Icons.chevron_right_rounded, color: context.hc.plum900),
      ]),
    );
  }
}
