import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/common.dart';
import '../../i18n/strings.dart';

/// Shown after sign-up, and when someone signs in before confirming their email.
/// The account exists but cannot be used until the emailed link has been opened.
class CheckEmailScreen extends StatefulWidget {
  const CheckEmailScreen({super.key, required this.email});
  final String email;

  @override
  State<CheckEmailScreen> createState() => _CheckEmailScreenState();
}

class _CheckEmailScreenState extends State<CheckEmailScreen> {
  bool _busy = false;

  Future<void> _resend() async {
    setState(() => _busy = true);
    try {
      await context.read<Session>().resendVerification(widget.email);
      if (mounted) showMessage(context, tr('We sent the email again.'));
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
        BlobHeader(title: tr('Check your email'), subtitle: tr('One more step.'), variant: 1),
        Padding(
          padding: const EdgeInsets.all(Space.s4),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            const SizedBox(height: Space.s4),
            HatuaCard(
              color: context.hc.plum100,
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Icon(Icons.mark_email_unread_outlined, color: context.hc.plum900),
                const SizedBox(width: Space.s3),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(tr('We sent a link to'), style: t.bodySmall),
                    Text(widget.email, style: t.titleMedium),
                  ]),
                ),
              ]),
            ),
            const SizedBox(height: Space.s4),
            Text(
              tr('Open the email and tap the link to confirm your address. Then come back here and sign in.'),
              style: t.bodyMedium,
            ),
            const SizedBox(height: Space.s2),
            Text(tr('If you cannot find it, look in your spam folder.'), style: t.bodySmall),
            const SizedBox(height: Space.s6),
            FilledButton(
              onPressed: () => Navigator.of(context).popUntil((r) => r.isFirst),
              child: Text(tr('I have confirmed, sign in')),
            ),
            const SizedBox(height: Space.s3),
            TextButton(
              onPressed: _busy ? null : _resend,
              child: Text(_busy ? tr('Sending...') : tr('Send the email again')),
            ),
          ]),
        ),
      ]),
    );
  }
}
