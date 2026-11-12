import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import '../../i18n/strings.dart';

/// Asks for the account's email and has a "choose a new password" link sent to it.
/// The new password is chosen on the page the link opens, not in the app.
class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key, this.email = ''});
  final String email;

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _form = GlobalKey<FormState>();
  late final _email = TextEditingController(text: widget.email);
  bool _busy = false;
  String? _sentTo;

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    final email = _email.text.trim().toLowerCase();
    try {
      await context.read<Session>().forgotPassword(email);
      if (mounted) setState(() => _sentTo = email);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      body: ListView(padding: EdgeInsets.zero, children: [
        BlobHeader(
          title: tr('Forgot your password?'),
          subtitle: tr('We will email you a link to choose a new one.'),
          trailing: IconButton(
            tooltip: tr('Back'),
            color: Colors.white,
            icon: const Icon(Icons.arrow_back_rounded),
            onPressed: () => Navigator.of(context).pop(),
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(Space.s4),
          child: _sentTo != null ? _sent(context, t) : _ask(context),
        ),
      ]),
    );
  }

  Widget _ask(BuildContext context) {
    return Form(
      key: _form,
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        const SizedBox(height: Space.s4),
        LabeledField(
          label: tr('Email'),
          controller: _email,
          hint: 'amina@example.com',
          icon: Icons.mail_outline_rounded,
          keyboardType: TextInputType.emailAddress,
          textInputAction: TextInputAction.done,
          validator: emailValidator,
        ),
        const SizedBox(height: Space.s6),
        FilledButton(
          onPressed: _busy ? null : _send,
          child: Text(_busy ? tr('Sending...') : tr('Send the link')),
        ),
      ]),
    );
  }

  Widget _sent(BuildContext context, TextTheme t) {
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      const SizedBox(height: Space.s4),
      HatuaCard(
        color: context.hc.plum100,
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(Icons.mark_email_unread_outlined, color: context.hc.plum900),
          const SizedBox(width: Space.s3),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(tr('If this email has a Hatua account, we sent a link to'), style: t.bodySmall),
              Text(_sentTo!, style: t.titleMedium),
            ]),
          ),
        ]),
      ),
      const SizedBox(height: Space.s4),
      Text(
        tr('Open the email and tap the link to choose a new password. The link works for one hour. Then come back here and sign in.'),
        style: t.bodyMedium,
      ),
      const SizedBox(height: Space.s6),
      FilledButton(
        onPressed: () => Navigator.of(context).pop(),
        child: Text(tr('Back to sign in')),
      ),
      const SizedBox(height: Space.s3),
      TextButton(
        onPressed: _busy ? null : _send,
        child: Text(_busy ? tr('Sending...') : tr('Send the link again')),
      ),
    ]);
  }
}
