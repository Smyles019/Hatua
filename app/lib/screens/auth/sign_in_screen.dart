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
import 'sign_up_screen.dart';

class SignInScreen extends StatefulWidget {
  const SignInScreen({super.key});

  @override
  State<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends State<SignInScreen> {
  final _form = GlobalKey<FormState>();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  bool _google = false;

  @override
  void dispose() {
    _phone.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await context.read<Session>().signIn(_phone.text.trim(), _password.text);
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
              child: ThemeToggleButton(color: context.hc.onHeader),
            ),
          ),
        ),
      ]),
    );
  }

  Widget _body(BuildContext context) {
    return ListView(padding: EdgeInsets.zero, children: [
      BlobHeader(title: 'Welcome back', subtitle: 'Sign in to continue.', variant: 1),
      Padding(
        padding: const EdgeInsets.all(Space.s4),
        child: Form(
          key: _form,
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const SizedBox(height: Space.s4),
            LabeledField(
              label: 'Phone number',
              controller: _phone,
              hint: '0712 345 678',
              icon: Icons.phone_android_rounded,
              keyboardType: TextInputType.phone,
              validator: phoneValidator,
            ),
            const SizedBox(height: Space.s3),
            LabeledField(
              label: 'Password',
              controller: _password,
              icon: Icons.lock_outline_rounded,
              obscure: true,
              textInputAction: TextInputAction.done,
              validator: (v) => requiredField(v, 'your password'),
            ),
            const SizedBox(height: Space.s6),
            FilledButton(
              onPressed: _busy || _google ? null : _submit,
              child: Text(_busy ? 'Signing in...' : 'Sign in'),
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
              child: const Text('New here? Create an account'),
            ),
            const SizedBox(height: Space.s4),
            Text(
              'Health workers and administrators: use the account your administrator '
              'gave you.',
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ]),
        ),
      ),
    ]);
  }
}
