import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/child_avatar.dart';
import '../../widgets/common.dart';
import 'add_child_screen.dart';
import 'caregiver_data.dart';
import 'child_profile_screen.dart';

class ChildrenTab extends StatefulWidget {
  const ChildrenTab({super.key});

  @override
  State<ChildrenTab> createState() => _ChildrenTabState();
}

class _ChildrenTabState extends State<ChildrenTab> {
  Future<List<Child>>? _future;
  int _version = -1;

  void _load() {
    final s = context.read<Session>();
    _version = s.dataVersion;
    _future = loadChildren(s.api);
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (_future == null || _version != s.dataVersion) _load();
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: Text('Children')),
      body: RefreshIndicator(
        color: context.hc.plum700,
        onRefresh: () async {
          setState(_load);
          await _future;
        },
        child: ListView(padding: EdgeInsets.all(Space.s4), children: [
          AsyncView<List<Child>>(
            future: _future!,
            onRetry: () => setState(_load),
            builder: (context, children) => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (children.isEmpty)
                  EmptyPanel(
                      title: 'No children yet',
                      message: 'Add a child under five to start checking.',
                      icon: Icons.child_care_rounded),
                for (final c in children) ...[
                  HatuaCard(
                    onTap: () => Navigator.of(context).push(MaterialPageRoute(
                        builder: (_) => ChildProfileScreen(childId: c.childId))),
                    child: Row(children: [
                      ChildAvatar(childId: c.childId, avatarId: c.avatarId),
                      SizedBox(width: Space.s3),
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(c.firstName, style: t.titleMedium),
                          Text('${ageLabel(c.ageMonths)} · ${c.location}', style: t.bodySmall),
                        ]),
                      ),
                      Icon(Icons.chevron_right_rounded, color: context.hc.plum900),
                    ]),
                  ),
                  SizedBox(height: Space.s3),
                ],
                SizedBox(height: Space.s3),
                FilledButton.icon(
                  style: secondaryButtonStyle(context),
                  onPressed: () => Navigator.of(context)
                      .push(MaterialPageRoute(builder: (_) => AddChildScreen())),
                  icon: Icon(Icons.add_rounded),
                  label: Text('Add a child'),
                ),
              ],
            ),
          ),
        ]),
      ),
    );
  }
}
