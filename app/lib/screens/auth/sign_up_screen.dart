import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/api_client.dart';
import '../../state/google_auth.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/google_button.dart';
import 'add_phone_screen.dart';
import 'check_email_screen.dart';
import '../../i18n/strings.dart';

/// Self-registration. The backend always creates a caregiver account here.
class SignUpScreen extends StatefulWidget {
  const SignUpScreen({super.key});

  @override
  State<SignUpScreen> createState() => _SignUpScreenState();
}

class _SignUpScreenState extends State<SignUpScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _busy = false;
  bool _google = false;

  @override
  void dispose() {
    for (final c in [_name, _email, _phone, _password, _confirm]) {
      c.dispose();
    }
    super.dispose();
  }

  /// Creates the account, then shows "Check your email": there is no session until the
  /// emailed link has been opened.
  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      final email = await context.read<Session>().register(
          _name.text.trim(), _email.text.trim(), _phone.text.trim(), _password.text);
      if (mounted) {
        await Navigator.of(context)
            .pushReplacement(MaterialPageRoute(builder: (_) => CheckEmailScreen(email: email)));
      }
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Same Google flow as sign in: a new Google account adds a phone number once.
  Future<void> _withGoogle() async {
    setState(() => _google = true);
    final session = context.read<Session>();
    try {
      final google = await GoogleAuth.pickAccount();
      try {
        await session.signInWithGoogle(google.idToken);
        if (mounted) Navigator.of(context).popUntil((r) => r.isFirst);
      } on NeedsPhone {
        if (mounted) {
          await Navigator.of(context)
              .push(MaterialPageRoute(builder: (_) => AddPhoneScreen(google: google)));
        }
      }
    } on GoogleSignInCancelled {
      // The person closed the picker: nothing to say.
    } catch (e) {
      if (mounted) {
        showError(context,
            e is ApiException ? e : ApiException(0, e.toString().replaceFirst('Exception: ', '')));
      }
    } finally {
      if (mounted) setState(() => _google = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: ListView(padding: EdgeInsets.zero, children: [
        BlobHeader(
          title: tr('Create your account'),
          subtitle: tr('For parents and caregivers.'),
          trailing: IconButton(
            tooltip: tr('Back'),
            color: Colors.white,
            icon: const Icon(Icons.arrow_back_rounded),
            onPressed: () => Navigator.of(context).pop(),
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(Space.s4),
          child: Form(
            key: _form,
            child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              if (!kIsWeb) ...[
                GoogleButton(onPressed: _busy ? null : _withGoogle, busy: _google),
                const SizedBox(height: Space.s4),
                Row(children: [
                  const Expanded(child: Divider()),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: Space.s3),
                    child: Text(tr('OR SIGN UP WITH YOUR EMAIL'),
                        style: Theme.of(context).textTheme.labelMedium),
                  ),
                  const Expanded(child: Divider()),
                ]),
              ],
              const SizedBox(height: Space.s4),
              LabeledField(
                label: tr('Full name'),
                controller: _name,
                hint: tr('Amina Wanjiku'),
                icon: Icons.person_outline_rounded,
                validator: (v) => requiredField(v, tr('your name')),
              ),
              const SizedBox(height: Space.s3),
              LabeledField(
                label: tr('Email'),
                controller: _email,
                hint: 'amina@example.com',
                icon: Icons.mail_outline_rounded,
                keyboardType: TextInputType.emailAddress,
                validator: emailValidator,
              ),
              const SizedBox(height: Space.s3),
              LabeledField(
                label: tr('Phone number'),
                controller: _phone,
                hint: '0712 345 678',
                icon: Icons.phone_android_rounded,
                keyboardType: TextInputType.phone,
                validator: phoneValidator,
              ),
              const SizedBox(height: Space.s3),
              LabeledField(
                label: tr('Create a password'),
                controller: _password,
                hint: tr('At least 6 characters'),
                icon: Icons.lock_outline_rounded,
                obscure: true,
                validator: passwordValidator,
              ),
              const SizedBox(height: Space.s3),
              LabeledField(
                label: tr('Confirm password'),
                controller: _confirm,
                icon: Icons.lock_outline_rounded,
                obscure: true,
                textInputAction: TextInputAction.done,
                validator: (v) => v != _password.text ? tr('The passwords do not match') : null,
              ),
              const SizedBox(height: Space.s4),
              HatuaCard(
                color: context.hc.plum100,
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Icon(Icons.lock_outline_rounded, color: context.hc.plum900),
                  const SizedBox(width: Space.s3),
                  Expanded(
                    child: Text(
                      tr("Your children's checks are private. Only you and the community health worker linked to you can see them."),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                ]),
              ),
              const SizedBox(height: Space.s6),
              FilledButton(
                onPressed: _busy ? null : _submit,
                child: Text(_busy ? tr('Creating account...') : tr('Create account')),
              ),
              const SizedBox(height: Space.s3),
              TextButton(
                onPressed: _busy ? null : () => Navigator.of(context).pop(),
                child: Text(tr('Already have an account? Sign in')),
              ),
            ]),
          ),
        ),
      ]),
    );
  }
}
