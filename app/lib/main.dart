import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'api/api_client.dart';
import 'screens/admin/admin_shell.dart';
import 'screens/auth/sign_in_screen.dart';
import 'screens/auth/splash_screen.dart';
import 'screens/auth/welcome_screen.dart';
import 'screens/caregiver/caregiver_shell.dart';
import 'screens/chw/chw_shell.dart';
import 'state/session.dart';
import 'state/theme_controller.dart';
import 'theme/theme.dart';
import 'widgets/web_frame.dart';
import 'i18n/strings.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // The language first, so the first screen is already in it.
  final language = LanguageController();
  await language.restore();
  final session = Session(ApiClient())..restore();
  final theme = ThemeController()..restore();
  // Once someone is signed in, line the phone and the account up on one language.
  String? synced;
  session.addListener(() {
    final user = session.user;
    if (user != null && user.userId != synced) {
      synced = user.userId;
      language.syncWith(user.language, session.api);
    } else if (user == null) {
      synced = null;
    }
  });
  runApp(MultiProvider(providers: [
    ChangeNotifierProvider.value(value: language),
    ChangeNotifierProvider.value(value: session),
    ChangeNotifierProvider.value(value: theme),
  ], child: const HatuaApp()));
}

class HatuaApp extends StatelessWidget {
  const HatuaApp({super.key});

  @override
  Widget build(BuildContext context) {
    // A new key when the language changes rebuilds every screen in the new language
    // (the app opens again at its first screen).
    final lang = context.watch<LanguageController>().language;
    return MaterialApp(
      key: ValueKey(lang),
      title: 'Hatua',
      debugShowCheckedModeBanner: false,
      theme: buildHatuaTheme(Brightness.light),
      darkTheme: buildHatuaTheme(Brightness.dark),
      themeMode: context.watch<ThemeController>().mode,
      builder: (context, child) => WebFrame(child: child ?? const SizedBox.shrink()),
      home: const _Root(),
    );
  }
}

/// Picks the first screen from the session: splash while restoring, sign in when signed
/// out, otherwise the home for the user's role.
class _Root extends StatelessWidget {
  const _Root();

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    if (!session.restored) return SplashScreen();
    final user = session.user;
    if (user == null) return session.welcomed ? const SignInScreen() : const WelcomeScreen();
    return switch (user.role) {
      'chw' => const ChwShell(),
      'admin' => AdminShell(),
      _ => const CaregiverShell(),
    };
  }
}
