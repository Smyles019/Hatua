import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/session.dart';
import '../state/theme_controller.dart';
import '../theme/colors.dart';
import '../theme/theme.dart';
import '../widgets/child_avatar.dart';
import '../widgets/common.dart';
import '../widgets/risk_chip.dart';
import 'caregiver/add_child_screen.dart';
import 'caregiver/caregiver_data.dart';
import 'caregiver/child_profile_screen.dart';
import 'chw/chw_profile_section.dart';
import '../i18n/strings.dart';

/// Profile and settings, shared by all three roles.
class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    final user = session.user;
    final t = Theme.of(context).textTheme;
    if (user == null) return SizedBox.shrink();

    return Scaffold(
      appBar: AppBar(title: Text(tr('Profile'))),
      body: ListView(padding: EdgeInsets.all(Space.s4), children: [
        HatuaCard(
          padding: EdgeInsets.all(Space.s6),
          child: Column(children: [
            InitialAvatar(user.fullName,
                size: 80,
                color: user.role == 'chw' ? context.hc.sky500 : context.hc.blush500),
            SizedBox(height: Space.s3),
            Text(user.fullName, style: t.headlineSmall, textAlign: TextAlign.center),
            SizedBox(height: Space.s1),
            Text(user.email ?? user.phoneNumber, style: t.bodySmall),
          ]),
        ),
        if (user.role == 'chw') ...[
          SizedBox(height: Space.s4),
          const ChwProfileSection(),
        ],
        if (user.role == 'caregiver') ...[
          SizedBox(height: Space.s4),
          const _ChildrenSection(),
          SizedBox(height: Space.s3),
          HatuaCard(
            child: Row(children: [
              Icon(Icons.health_and_safety_outlined, color: context.hc.plum900),
              SizedBox(width: Space.s3),
              Expanded(
                child: Text(
                  user.linkedChwId == null
                      ? tr('You are not linked to a community health worker yet. Ask your CHW to link you using your phone number.')
                      : tr('You are linked to a community health worker. They will see results that need follow-up.'),
                  style: t.bodyMedium,
                ),
              ),
            ]),
          ),
        ],
        SizedBox(height: Space.s3),
        HatuaCard(
          padding: EdgeInsets.zero,
          child: Column(children: [
            // Label on one line, the two choices full width below, so "Kiswahili" never wraps.
            Padding(
              padding: EdgeInsets.fromLTRB(Space.s4, Space.s3, Space.s4, Space.s3),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Row(children: [
                  Icon(Icons.translate_rounded, color: context.hc.plum900),
                  SizedBox(width: Space.s4),
                  Text(tr('Language'), style: t.bodyMedium),
                ]),
                SizedBox(height: Space.s2),
                // Each language is named in itself, so either reader recognises theirs.
                SegmentedButton<String>(
                  showSelectedIcon: false,
                  segments: const [
                    ButtonSegment(value: 'en', label: Text('English')),
                    ButtonSegment(value: 'sw', label: Text('Kiswahili')),
                  ],
                  selected: {context.watch<LanguageController>().language},
                  onSelectionChanged: (s) =>
                      context.read<LanguageController>().choose(s.first, api: session.api),
                ),
              ]),
            ),
            Divider(height: 1, indent: Space.s4, endIndent: Space.s4),
            SwitchListTile(
              minTileHeight: Space.touch + 8,
              secondary: Icon(Icons.dark_mode_outlined, color: context.hc.plum900),
              title: Text(tr('Dark mode'), style: t.bodyMedium),
              value: Theme.of(context).brightness == Brightness.dark,
              onChanged: (_) =>
                  context.read<ThemeController>().toggle(Theme.of(context).brightness),
            ),
            Divider(height: 1, indent: Space.s4, endIndent: Space.s4),
            ListTile(
              minTileHeight: Space.touch + 8,
              leading: Icon(Icons.lock_outline_rounded, color: context.hc.plum900),
              title: Text(tr('Change password'), style: t.bodyMedium),
              trailing: Icon(Icons.chevron_right_rounded, color: context.hc.plum900),
              onTap: () => showDialog(context: context, builder: (_) => const _PasswordDialog()),
            ),
            Divider(height: 1, indent: Space.s4, endIndent: Space.s4),
            ListTile(
              minTileHeight: Space.touch + 8,
              leading: Icon(Icons.logout_rounded, color: context.hc.plum900),
              title: Text(tr('Sign out'), style: t.bodyMedium),
              onTap: () => context.read<Session>().signOut(),
            ),
          ]),
        ),
      ]),
    );
  }
}

/// Caregiver's children with a count of checks, and a button to add another.
class _ChildrenSection extends StatefulWidget {
  const _ChildrenSection();

  @override
  State<_ChildrenSection> createState() => _ChildrenSectionState();
}

class _ChildrenSectionState extends State<_ChildrenSection> {
  Future<List<ChildWithChecks>>? _future;
  int _version = -1;

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (_future == null || _version != s.dataVersion) {
      _version = s.dataVersion;
      _future = loadChildrenWithChecks(s.api);
    }
    final t = Theme.of(context).textTheme;
    return AsyncView<List<ChildWithChecks>>(
      future: _future!,
      onRetry: () => setState(() => _future = null),
      builder: (context, items) {
        final checks = items.fold<int>(0, (n, i) => n + i.checks.length);
        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Row(children: [
            Expanded(child: _Stat(value: '${items.length}', label: tr('Children'))),
            SizedBox(width: Space.s3),
            Expanded(child: _Stat(value: '$checks', label: tr('Checks done'))),
          ]),
          SizedBox(height: Space.s4),
          Text(tr('Children in your care'), style: t.titleLarge),
          SizedBox(height: Space.s3),
          for (final i in items) ...[
            HatuaCard(
              onTap: () => Navigator.of(context).push(MaterialPageRoute(
                  builder: (_) => ChildProfileScreen(childId: i.child.childId))),
              child: Row(children: [
                ChildAvatar(childId: i.child.childId, avatarId: i.child.avatarId),
                SizedBox(width: Space.s3),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(i.child.firstName, style: t.titleMedium),
                    Text(ageLabel(i.child.ageMonths), style: t.bodySmall),
                    // Under the name, not beside it, so a long label (Swahili) never
                    // squeezes the name.
                    if (i.latest != null) ...[
                      SizedBox(height: Space.s1),
                      RiskChip.risk(i.latest!.riskLevel),
                    ],
                  ]),
                ),
                Icon(Icons.chevron_right_rounded, color: context.hc.plum900),
              ]),
            ),
            SizedBox(height: Space.s2),
          ],
          FilledButton.icon(
            style: secondaryButtonStyle(context),
            onPressed: () => Navigator.of(context)
                .push(MaterialPageRoute(builder: (_) => const AddChildScreen())),
            icon: Icon(Icons.add_rounded),
            label: Text(tr('Add another child')),
          ),
        ]);
      },
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.value, required this.label});
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return HatuaCard(
      color: context.hc.plum100,
      child: Column(children: [
        Text(value, style: t.headlineSmall),
        Text(label, style: t.bodySmall),
      ]),
    );
  }
}

class _PasswordDialog extends StatefulWidget {
  const _PasswordDialog();

  @override
  State<_PasswordDialog> createState() => _PasswordDialogState();
}

class _PasswordDialogState extends State<_PasswordDialog> {
  final _form = GlobalKey<FormState>();
  final _current = TextEditingController();
  final _new = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _current.dispose();
    _new.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await context
          .read<Session>()
          .api
          .put('/auth/password', {'current_password': _current.text, 'new_password': _new.text});
      if (mounted) {
        Navigator.of(context).pop();
        showMessage(context, tr('Your password was changed.'));
      }
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(tr('Change password')),
      content: Form(
        key: _form,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          LabeledField(
              label: tr('Current password'),
              controller: _current,
              obscure: true,
              validator: (v) => requiredField(v, tr('your current password'))),
          SizedBox(height: Space.s3),
          LabeledField(
              label: tr('New password'),
              controller: _new,
              obscure: true,
              textInputAction: TextInputAction.done,
              validator: passwordValidator),
        ]),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text(tr('Cancel'))),
        TextButton(onPressed: _busy ? null : _save, child: Text(tr('Save'))),
      ],
    );
  }
}
