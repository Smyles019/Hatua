import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/theme_controller.dart';

/// Sun or moon button that flips between light and dark mode.
class ThemeToggleButton extends StatelessWidget {
  const ThemeToggleButton({super.key, this.color});

  final Color? color;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return IconButton(
      tooltip: dark ? 'Switch to light mode' : 'Switch to dark mode',
      color: color,
      iconSize: 28,
      icon: Icon(dark ? Icons.light_mode_rounded : Icons.dark_mode_rounded),
      onPressed: () => context.read<ThemeController>().toggle(Theme.of(context).brightness),
    );
  }
}
