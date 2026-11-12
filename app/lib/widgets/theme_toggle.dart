import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../i18n/strings.dart';
import '../state/session.dart';
import '../state/theme_controller.dart';

/// Sun or moon button that flips between light and dark mode.
class ThemeToggleButton extends StatelessWidget {
  const ThemeToggleButton({super.key, this.color});

  final Color? color;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return IconButton(
      tooltip: dark ? tr('Switch to light mode') : tr('Switch to dark mode'),
      color: color,
      iconSize: 28,
      icon: Icon(dark ? Icons.light_mode_rounded : Icons.dark_mode_rounded),
      onPressed: () => context.read<ThemeController>().toggle(Theme.of(context).brightness),
    );
  }
}

/// Switches between English and Swahili. Its label is in the other language ("Kiswahili"
/// while in English), so someone who reads only that language can find it.
class LanguageToggleButton extends StatelessWidget {
  const LanguageToggleButton({super.key, this.color});

  final Color? color;

  @override
  Widget build(BuildContext context) {
    final other = context.watch<LanguageController>().language == 'sw' ? 'en' : 'sw';
    final session = context.read<Session>();
    return TextButton.icon(
      style: TextButton.styleFrom(foregroundColor: color),
      icon: const Icon(Icons.translate_rounded),
      label: Text(other == 'sw' ? 'Kiswahili' : 'English'),
      onPressed: () => context
          .read<LanguageController>()
          .choose(other, api: session.user == null ? null : session.api),
    );
  }
}
