import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import '../../i18n/strings.dart';

/// Link a caregiver who already has an account (by phone), or enrol a new one during a
/// household visit. Both end with the caregiver linked to this CHW.
class LinkCaregiverScreen extends StatefulWidget {
  const LinkCaregiverScreen({super.key});

  @override
  State<LinkCaregiverScreen> createState() => _LinkCaregiverScreenState();
}

class _LinkCaregiverScreenState extends State<LinkCaregiverScreen> {
  bool _enrol = false;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: Text(tr('Link a caregiver'))),
      body: ListView(padding: EdgeInsets.all(Space.s4), children: [
        Row(children: [
          Expanded(
            child: ChoiceOption(
                label: tr('Has an account'),
                selected: !_enrol,
                onTap: () => setState(() => _enrol = false)),
          ),
          SizedBox(width: Space.s2),
          Expanded(
            child: ChoiceOption(
                label: tr('New caregiver'),
                selected: _enrol,
                onTap: () => setState(() => _enrol = true)),
          ),
        ]),
        SizedBox(height: Space.s4),
        Text(
          _enrol
              ? tr('Create an account for the caregiver. Give them the password so they can sign in and change it.')
              : tr('Enter the phone number the caregiver signed up with.'),
          style: t.bodyMedium,
        ),
        SizedBox(height: Space.s4),
        _enrol ? const _EnrolForm() : const _LinkForm(),
      ]),
    );
  }
}

class _LinkForm extends StatefulWidget {
  const _LinkForm();

  @override
  State<_LinkForm> createState() => _LinkFormState();
}

class _LinkFormState extends State<_LinkForm> {
  final _form = GlobalKey<FormState>();
  final _phone = TextEditingController();
  bool _busy = false;
  AppUser? _linked;

  @override
  void dispose() {
    _phone.dispose();
    super.dispose();
  }

  Future<void> _link() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    final s = context.read<Session>();
    try {
      final data = await s.api.post('/chw/caregivers/link', {'phone_number': _phone.text.trim()});
      s.dataChanged();
      if (mounted) setState(() => _linked = AppUser.fromJson(data as Map<String, dynamic>));
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Form(
      key: _form,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        LabeledField(
          label: tr("Caregiver's phone number"),
          controller: _phone,
          hint: '0712 345 678',
          icon: Icons.search_rounded,
          keyboardType: TextInputType.phone,
          textInputAction: TextInputAction.done,
          validator: phoneValidator,
        ),
        SizedBox(height: Space.s4),
        FilledButton(
            onPressed: _busy ? null : _link, child: Text(_busy ? tr('Linking...') : tr('Link to me'))),
        if (_linked != null) ...[
          SizedBox(height: Space.s4),
          HatuaCard(
            color: context.hc.riskLowBg,
            child: Row(children: [
              InitialAvatar(_linked!.fullName, color: context.hc.sky500),
              SizedBox(width: Space.s3),
              Expanded(
                child: Text(tr('{fullName} is now linked to you.', {'fullName': _linked!.fullName}), style: t.bodyMedium),
              ),
            ]),
          ),
        ],
      ]),
    );
  }
}

class _EnrolForm extends StatefulWidget {
  const _EnrolForm();

  @override
  State<_EnrolForm> createState() => _EnrolFormState();
}

class _EnrolFormState extends State<_EnrolForm> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _phone.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _enrol() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    final s = context.read<Session>();
    try {
      await s.api.post('/chw/caregivers', {
        'full_name': _name.text.trim(),
        'email': _email.text.trim(),
        'phone_number': _phone.text.trim(),
        'password': _password.text,
      });
      s.dataChanged();
      if (mounted) {
        showMessage(context, tr('{name} was enrolled and linked to you. They need to open the link we emailed them before they can sign in.', {'name': _name.text.trim()}));
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: _form,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        LabeledField(
            label: tr('Full name'),
            controller: _name,
            icon: Icons.person_outline_rounded,
            validator: (v) => requiredField(v, tr('their name'))),
        SizedBox(height: Space.s3),
        LabeledField(
            label: tr('Email (they sign in with it)'),
            controller: _email,
            hint: 'amina@example.com',
            icon: Icons.mail_outline_rounded,
            keyboardType: TextInputType.emailAddress,
            validator: emailValidator),
        SizedBox(height: Space.s3),
        LabeledField(
            label: tr('Phone number'),
            controller: _phone,
            hint: '0712 345 678',
            icon: Icons.phone_android_rounded,
            keyboardType: TextInputType.phone,
            validator: phoneValidator),
        SizedBox(height: Space.s3),
        LabeledField(
            label: tr('Temporary password'),
            controller: _password,
            hint: tr('At least 6 characters'),
            icon: Icons.lock_outline_rounded,
            textInputAction: TextInputAction.done,
            validator: passwordValidator),
        SizedBox(height: Space.s4),
        FilledButton(
            onPressed: _busy ? null : _enrol,
            child: Text(_busy ? tr('Enrolling...') : tr('Enrol and link'))),
      ]),
    );
  }
}
