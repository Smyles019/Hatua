import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../state/google_auth.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/google_button.dart';
import '../../widgets/sprout.dart';

/// Shown once, after the first Google sign-in. The account is created only when the
/// phone number is added: CHWs find and link caregivers by phone.
class AddPhoneScreen extends StatefulWidget {
  const AddPhoneScreen({super.key, required this.google});
  final GoogleIdToken google;

  @override
  State<AddPhoneScreen> createState() => _AddPhoneScreenState();
}

class _AddPhoneScreenState extends State<AddPhoneScreen> {
  final _form = GlobalKey<FormState>();
  final _phone = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _phone.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await context
          .read<Session>()
          .signInWithGoogle(widget.google.idToken, phone: _phone.text.trim());
      if (mounted) Navigator.of(context).popUntil((r) => r.isFirst);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final c = context.hc;
    return Scaffold(
      appBar: AppBar(title: const Text('Add your phone number')),
      body: Form(
        key: _form,
        child: ListView(padding: const EdgeInsets.all(Space.s4), children: [
          const Center(child: Sprout(pose: SproutPose.waving, size: 110)),
          const SizedBox(height: Space.s3),
          Text('One more step', style: t.headlineSmall, textAlign: TextAlign.center),
          const SizedBox(height: Space.s1),
          Text('Add your phone number so your community health worker can link to you.',
              style: t.bodyMedium, textAlign: TextAlign.center),
          const SizedBox(height: Space.s6),
          Text('GOOGLE ACCOUNT', style: t.labelMedium),
          const SizedBox(height: Space.s1),
          HatuaCard(
            child: Row(children: [
              const GoogleLogo(size: 24),
              const SizedBox(width: Space.s3),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(widget.google.name, style: t.titleMedium),
                  Text(widget.google.email, style: t.bodySmall),
                ]),
              ),
              Icon(Icons.check_circle_outline_rounded, color: c.riskLow),
            ]),
          ),
          const SizedBox(height: Space.s4),
          LabeledField(
            label: 'Phone number',
            controller: _phone,
            hint: '0712 345 678',
            icon: Icons.phone_android_rounded,
            keyboardType: TextInputType.phone,
            textInputAction: TextInputAction.done,
            validator: phoneValidator,
          ),
          const SizedBox(height: Space.s6),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: Text(_busy ? 'Creating your account...' : 'Continue'),
          ),
          const SizedBox(height: Space.s3),
          Text(
            'Already have a Hatua account with this number? Go back and sign in with your '
            'phone number and password.',
            style: t.bodySmall,
            textAlign: TextAlign.center,
          ),
        ]),
      ),
    );
  }
}
