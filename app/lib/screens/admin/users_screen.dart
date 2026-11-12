import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import 'admin_shell.dart';

const _roleLabels = {'caregiver': 'Caregiver', 'chw': 'CHW', 'admin': 'Admin'};

/// Accounts: list, filter, add, deactivate or reactivate, move a caregiver to a CHW.
/// Accounts are never deleted (the backend keeps reviewers on recorded outcomes).
class UsersScreen extends StatefulWidget {
  const UsersScreen({super.key});

  @override
  State<UsersScreen> createState() => _UsersScreenState();
}

class _UsersScreenState extends State<UsersScreen> {
  Future<List<AppUser>>? _future;
  int _version = -1;
  String? _role;
  String _query = '';

  void _load() {
    final s = context.read<Session>();
    _version = s.dataVersion;
    _future = s.api.get('/admin/users').then((d) =>
        (d as List).map((u) => AppUser.fromJson(u as Map<String, dynamic>)).toList());
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<Session>();
    if (_future == null || _version != s.dataVersion) _load();
    return Scaffold(
      appBar: adminAppBar(context, 'Manage users'),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: context.hc.plum700,
        foregroundColor: context.hc.onPrimary,
        onPressed: () => showDialog(context: context, builder: (_) => const _AddUserDialog()),
        icon: Icon(Icons.person_add_alt_1_outlined),
        label: Text('Add user'),
      ),
      body: RefreshIndicator(
        color: context.hc.plum700,
        onRefresh: () async {
          setState(_load);
          await _future;
        },
        child: ListView(padding: EdgeInsets.fromLTRB(Space.s4, Space.s4, Space.s4, 96),
            children: [
          TextField(
            decoration: InputDecoration(
                hintText: 'Search by name or phone', prefixIcon: Icon(Icons.search_rounded)),
            onChanged: (v) => setState(() => _query = v.trim().toLowerCase()),
          ),
          SizedBox(height: Space.s3),
          Wrap(spacing: Space.s2, runSpacing: Space.s2, children: [
            _chip('All', null),
            _chip('Caregivers', 'caregiver'),
            _chip('CHWs', 'chw'),
            _chip('Admins', 'admin'),
          ]),
          SizedBox(height: Space.s4),
          AsyncView<List<AppUser>>(
            future: _future!,
            onRetry: () => setState(_load),
            builder: (context, users) {
              final chws = {for (final u in users.where((u) => u.role == 'chw')) u.userId: u};
              final shown = users.where((u) {
                if (_role != null && u.role != _role) return false;
                if (_query.isEmpty) return true;
                return u.fullName.toLowerCase().contains(_query) ||
                    u.phoneNumber.contains(_query.replaceAll(' ', ''));
              }).toList();
              if (shown.isEmpty) {
                return EmptyPanel(title: 'No users found', message: 'Try another search.');
              }
              return Column(children: [
                for (final u in shown) ...[
                  _UserRow(user: u, chws: chws),
                  SizedBox(height: Space.s2),
                ],
              ]);
            },
          ),
        ]),
      ),
    );
  }

  Widget _chip(String label, String? role) {
    final on = _role == role;
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
      onSelected: (_) => setState(() => _role = role),
    );
  }
}

class _UserRow extends StatelessWidget {
  const _UserRow({required this.user, required this.chws});
  final AppUser user;
  final Map<String, AppUser> chws;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final chw = user.linkedChwId == null ? null : chws[user.linkedChwId];
    return HatuaCard(
      child: Row(children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Flexible(child: Text(user.fullName, style: t.titleMedium)),
              SizedBox(width: Space.s2),
              Container(
                padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                    color: context.hc.plum100, borderRadius: BorderRadius.circular(Radii.sm)),
                child: Text(_roleLabels[user.role] ?? user.role,
                    style: t.labelMedium?.copyWith(color: context.hc.plum900)),
              ),
            ]),
            Text(user.phoneNumber, style: t.bodySmall),
            if (user.role == 'caregiver')
              Text(chw == null ? 'No CHW linked' : 'CHW: ${chw.fullName}', style: t.bodySmall),
            if (!user.isActive)
              Text('Deactivated', style: t.labelLarge?.copyWith(fontSize: 14)),
          ]),
        ),
        PopupMenuButton<String>(
          tooltip: 'More actions',
          onSelected: (v) => _act(context, v),
          itemBuilder: (_) => [
            PopupMenuItem(
                value: 'toggle', child: Text(user.isActive ? 'Deactivate' : 'Reactivate')),
            if (user.role == 'caregiver')
              PopupMenuItem(value: 'chw', child: Text('Change CHW')),
          ],
        ),
      ]),
    );
  }

  Future<void> _act(BuildContext context, String action) async {
    final s = context.read<Session>();
    try {
      if (action == 'toggle') {
        await s.api.patch('/admin/users/${user.userId}', {'is_active': !user.isActive});
      } else {
        final active = chws.values.where((c) => c.isActive).toList();
        final picked = await showDialog<String>(
          context: context,
          builder: (ctx) => SimpleDialog(
            title: Text('CHW for ${user.fullName}'),
            children: [
              for (final c in active)
                SimpleDialogOption(
                  onPressed: () => Navigator.pop(ctx, c.userId),
                  child: Text(c.fullName),
                ),
              SimpleDialogOption(
                onPressed: () => Navigator.pop(ctx, ''),
                child: Text('Remove link'),
              ),
            ],
          ),
        );
        if (picked == null) return;
        await s.api.put('/admin/users/${user.userId}/chw',
            {'chw_id': picked.isEmpty ? null : picked});
      }
      s.dataChanged();
    } catch (e) {
      if (context.mounted) showError(context, e);
    }
  }
}

class _AddUserDialog extends StatefulWidget {
  const _AddUserDialog();

  @override
  State<_AddUserDialog> createState() => _AddUserDialogState();
}

class _AddUserDialogState extends State<_AddUserDialog> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  String _role = 'chw';
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    final s = context.read<Session>();
    try {
      await s.api.post('/admin/users', {
        'full_name': _name.text.trim(),
        'phone_number': _phone.text.trim(),
        'password': _password.text,
        'role': _role,
      });
      s.dataChanged();
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Add user'),
      content: SingleChildScrollView(
        child: Form(
          key: _form,
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            LabeledField(
                label: 'Full name',
                controller: _name,
                validator: (v) => requiredField(v, 'a name')),
            SizedBox(height: Space.s3),
            LabeledField(
                label: 'Phone number',
                controller: _phone,
                keyboardType: TextInputType.phone,
                validator: phoneValidator),
            SizedBox(height: Space.s3),
            LabeledField(
                label: 'Temporary password',
                controller: _password,
                validator: passwordValidator),
            SizedBox(height: Space.s3),
            for (final r in _roleLabels.entries) ...[
              ChoiceOption(
                  label: r.value,
                  selected: _role == r.key,
                  onTap: () => setState(() => _role = r.key)),
              SizedBox(height: Space.s2),
            ],
          ]),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text('Cancel')),
        TextButton(onPressed: _busy ? null : _save, child: Text('Add')),
      ],
    );
  }
}
