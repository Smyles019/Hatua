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
import '../../widgets/theme_toggle.dart';
import 'add_phone_screen.dart';
import 'check_email_screen.dart';
import 'forgot_password_screen.dart';
import 'sign_up_screen.dart';
import '../../i18n/strings.dart';

class SignInScreen extends StatefulWidget {
  const SignInScreen({super.key});

  @override
  State<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends State<SignInScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  bool _google = false;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await context.read<Session>().signIn(_email.text.trim(), _password.text);
    } on NeedsVerification catch (e) {
      // Right password, but the emailed confirmation link has not been opened yet.
      if (mounted) {
        await Navigator.of(context)
            .push(MaterialPageRoute(builder: (_) => CheckEmailScreen(email: e.email)));
      }
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Google's account picker, then the backend. A first-time Google account goes to the
  /// one-time "Add your phone number" step.
  Future<void> _withGoogle() async {
    setState(() => _google = true);
    final session = context.read<Session>();
    try {
      final google = await GoogleAuth.pickAccount();
      try {
        await session.signInWithGoogle(google.idToken);
      } on NeedsPhone {
        if (mounted) {
          await Navigator.of(context)
              .push(MaterialPageRoute(builder: (_) => AddPhoneScreen(google: google)));
        }
      }
    } on GoogleSignInCancelled {
      // The person closed the picker: nothing to say.
    } catch (e) {
      if (mounted) showError(context, e is ApiException ? e : _plain(e));
    } finally {
      if (mounted) setState(() => _google = false);
    }
  }

  static ApiException _plain(Object e) =>
      ApiException(0, e.toString().replaceFirst('Exception: ', ''));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(children: [
        _body(context),
        SafeArea(
          child: Align(
            alignment: Alignment.topRight,
            child: Padding(
              padding: const EdgeInsets.all(Space.s2),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                LanguageToggleButton(color: context.hc.onHeader),
                ThemeToggleButton(color: context.hc.onHeader),
              ]),
            ),
          ),
        ),
      ]),
    );
  }

  Widget _body(BuildContext context) {
    return ListView(padding: EdgeInsets.zero, children: [
      BlobHeader(title: tr('Welcome back'), subtitle: tr('Sign in to continue.'), variant: 1),
      Padding(
        padding: const EdgeInsets.all(Space.s4),
        child: Form(
          key: _form,
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const SizedBox(height: Space.s4),
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
              label: tr('Password'),
              controller: _password,
              icon: Icons.lock_outline_rounded,
              obscure: true,
              textInputAction: TextInputAction.done,
              validator: (v) => requiredField(v, tr('your password')),
            ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: _busy
                    ? null
                    : () => Navigator.of(context).push(MaterialPageRoute(
                        builder: (_) => ForgotPasswordScreen(email: _email.text.trim()))),
                child: Text(tr('Forgot password?')),
              ),
            ),
            const SizedBox(height: Space.s3),
            FilledButton(
              onPressed: _busy || _google ? null : _submit,
              child: Text(_busy ? tr('Signing in...') : tr('Sign in')),
            ),
            // Google sign-in is phone-only for now: the web needs Google's own button.
            if (!kIsWeb) ...[
              const SizedBox(height: Space.s4),
              Row(children: [
                Expanded(child: Divider(color: context.hc.plum200)),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: Space.s3),
                  child: Text('or', style: Theme.of(context).textTheme.bodySmall),
                ),
                Expanded(child: Divider(color: context.hc.plum200)),
              ]),
              const SizedBox(height: Space.s4),
              GoogleButton(onPressed: _busy ? null : _withGoogle, busy: _google),
            ],
            const SizedBox(height: Space.s3),
            TextButton(
              onPressed: _busy
                  ? null
                  : () => Navigator.of(context)
                      .push(MaterialPageRoute(builder: (_) => const SignUpScreen())),
              child: Text(tr('New here? Create an account')),
            ),
          ]),
        ),
      ),
    ]);
  }
}
