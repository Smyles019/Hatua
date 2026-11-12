import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/child_avatar.dart';
import '../../widgets/common.dart';
import '../caregiver/add_child_screen.dart';
import '../caregiver/child_profile_screen.dart';
import 'chw_data.dart';
import 'link_caregiver_screen.dart';
import '../../i18n/strings.dart';

/// Caregivers linked to this CHW, with their children.
class CaregiversTab extends StatefulWidget {
  const CaregiversTab({super.key});

  @override
  State<CaregiversTab> createState() => _CaregiversTabState();
}

class _CaregiversTabState extends State<CaregiversTab> {
  Future<List<LinkedCaregiver>>? _future;
  int _version = -1;

  void _load() {
    final s = context.read<Session>();
    _version = s.dataVersion;
    _future = loadCaregivers(s.api);
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (_future == null || _version != s.dataVersion) _load();
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: Text(tr('Caregivers'))),
      body: RefreshIndicator(
        color: context.hc.plum700,
        onRefresh: () async {
          setState(_load);
          await _future;
        },
        child: ListView(padding: EdgeInsets.all(Space.s4), children: [
          FilledButton.icon(
            style: secondaryButtonStyle(context),
            onPressed: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => LinkCaregiverScreen())),
            icon: Icon(Icons.person_add_alt_1_outlined),
            label: Text(tr('Link or enrol a caregiver')),
          ),
          SizedBox(height: Space.s4),
          AsyncView<List<LinkedCaregiver>>(
            future: _future!,
            onRetry: () => setState(_load),
            builder: (context, list) => Column(children: [
              if (list.isEmpty)
                EmptyPanel(
                  title: tr('No caregivers linked yet'),
                  message: tr('Link caregivers by phone number to see their children here.'),
                  icon: Icons.people_outline_rounded,
                ),
              for (final c in list) ...[
                HatuaCard(
                  onTap: () => _openCaregiver(context, c),
                  child: Row(children: [
                    InitialAvatar(c.user.fullName, color: context.hc.sky500),
                    SizedBox(width: Space.s3),
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(c.user.fullName, style: t.titleMedium),
                        Text(c.user.phoneNumber, style: t.bodySmall),
                        Text(
                          '${c.children} child${c.children == 1 ? '' : 'ren'}'
                          '${c.openCases > 0 ? ' · ${c.openCases} to review' : ''}',
                          style: t.bodySmall?.copyWith(color: context.hc.plum900),
                        ),
                      ]),
                    ),
                    Icon(Icons.chevron_right_rounded, color: context.hc.plum900),
                  ]),
                ),
                SizedBox(height: Space.s2),
              ],
            ]),
          ),
        ]),
      ),
    );
  }

  Future<void> _openCaregiver(BuildContext context, LinkedCaregiver c) async {
    final api = context.read<Session>().api;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: EdgeInsets.all(Space.s4),
          child: FutureBuilder<List<Child>>(
            future: api
                .get('/children', {'caregiver_id': c.user.userId})
                .then((d) => (d as List)
                    .map((x) => Child.fromJson(x as Map<String, dynamic>))
                    .toList()),
            builder: (ctx, snap) {
              final t = Theme.of(ctx).textTheme;
              return Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(c.user.fullName, style: t.titleLarge),
                  SizedBox(height: Space.s3),
                  if (snap.connectionState != ConnectionState.done)
                    Center(child: CircularProgressIndicator(color: context.hc.plum700))
                  else if (snap.hasError)
                    Text('${snap.error}', style: t.bodyMedium)
                  else ...[
                    if (snap.data!.isEmpty) Text(tr('No children added yet.'), style: t.bodyMedium),
                    for (final ch in snap.data!)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: ChildAvatar(childId: ch.childId, avatarId: ch.avatarId, size: 36),
                        title: Text(ch.firstName, style: t.titleMedium),
                        subtitle: Text(ageLabel(ch.ageMonths), style: t.bodySmall),
                        trailing: Icon(Icons.chevron_right_rounded),
                        onTap: () {
                          Navigator.of(ctx).pop();
                          Navigator.of(context).push(MaterialPageRoute(
                              builder: (_) => ChildProfileScreen(childId: ch.childId)));
                        },
                      ),
                  ],
                  SizedBox(height: Space.s3),
                  FilledButton(
                    onPressed: () {
                      Navigator.of(ctx).pop();
                      Navigator.of(context).push(MaterialPageRoute(
                          builder: (_) => AddChildScreen(
                              caregiverId: c.user.userId, caregiverName: c.user.fullName)));
                    },
                    child: Text(tr('Add a child for this caregiver')),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}
