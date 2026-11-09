import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Light or dark mode, chosen by the person and kept on this phone.
/// Follows the phone's setting until they pick one.
class ThemeController extends ChangeNotifier {
  static const _kMode = 'hatua.themeMode';

  ThemeMode mode = ThemeMode.system;

  Future<void> restore() async {
    final prefs = await SharedPreferences.getInstance();
    mode = switch (prefs.getString(_kMode)) {
      'light' => ThemeMode.light,
      'dark' => ThemeMode.dark,
      _ => ThemeMode.system,
    };
    notifyListeners();
  }

  /// Switches to the opposite of what is on screen now.
  Future<void> toggle(Brightness current) async {
    mode = current == Brightness.dark ? ThemeMode.light : ThemeMode.dark;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kMode, mode == ThemeMode.dark ? 'dark' : 'light');
  }
}
