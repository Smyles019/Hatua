/// English or Swahili for the app's words.
///
/// The Swahili lines live in i18n/sw.json at the repository root, the one file the
/// website and the backend read too, keyed by the English text. The app carries a copy
/// (assets/i18n/sw.json, refreshed with i18n/tools/sync_app.py) so it works offline from
/// the first screen. Anything missing shows in English.
///
/// The questions and results come from the server already in the account's language, so
/// the choice is kept on the phone and on the account.
library;

import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:intl/date_symbol_data_local.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart';

const _prefKey = 'hatua.lang';
Map<String, String> _sw = const {};
String _lang = 'en';

/// The language in use: "en" or "sw".
String get currentLanguage => _lang;

/// Dates (DateFormat) follow the language: "22 Okt 2026" in Swahili.
void _applyLocale() => Intl.defaultLocale = _lang == 'sw' ? 'sw' : 'en_GB';

/// [text] in the chosen language, with {name}-style gaps filled from [params].
String tr(String text, [Map<String, Object?>? params]) {
  var out = _lang == 'sw' ? (_sw[text] ?? text) : text;
  if (params != null) {
    out = out.replaceAllMapped(RegExp(r'\{(\w+)\}'),
        (m) => params.containsKey(m[1]) ? '${params[m[1]]}' : m[0]!);
  }
  return out;
}

/// Holds the choice and rebuilds the app when it changes.
class LanguageController extends ChangeNotifier {
  /// True once the person picked a language on this phone (it then wins over the account).
  bool _chosenHere = false;

  String get language => _lang;

  /// Loads the Swahili lines and the saved choice. Call before the first screen.
  Future<void> restore() async {
    try {
      final sections = jsonDecode(await rootBundle.loadString('assets/i18n/sw.json')) as Map;
      final words = <String, String>{};
      sections.forEach((key, value) {
        if (!(key as String).startsWith('_') && value is Map) {
          value.forEach((en, sw) {
            if (sw is String && sw.isNotEmpty) words[en as String] = sw;
          });
        }
      });
      _sw = words;
    } catch (e) {
      debugPrint('Swahili lines not loaded: $e');
    }
    await initializeDateFormatting('sw');
    await initializeDateFormatting('en_GB');
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(_prefKey);
    _chosenHere = saved != null;
    _lang = saved == 'sw' ? 'sw' : 'en';
    _applyLocale();
    notifyListeners();
  }

  /// The person picked a language. Saved here, and on the account when signed in.
  Future<void> choose(String lang, {ApiClient? api}) async {
    _lang = lang == 'sw' ? 'sw' : 'en';
    _chosenHere = true;
    _applyLocale();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefKey, _lang);
    notifyListeners();
    if (api != null) {
      try {
        await api.patch('/auth/me', {'language': _lang});
      } catch (_) {
        // Kept on this phone; the account catches up next time.
      }
    }
  }

  /// After signing in: a choice made on this phone goes onto the account; otherwise the
  /// phone follows the account (for example, Swahili picked on the website).
  Future<void> syncWith(String accountLanguage, ApiClient api) async {
    if (accountLanguage == _lang) return;
    if (_chosenHere) {
      try {
        await api.patch('/auth/me', {'language': _lang});
      } catch (_) {}
    } else {
      _lang = accountLanguage == 'sw' ? 'sw' : 'en';
      _applyLocale();
      notifyListeners();
    }
  }
}
