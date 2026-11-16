import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'api/api_client.dart';
import 'screens/admin/admin_shell.dart';
import 'screens/auth/sign_in_screen.dart';
import 'screens/auth/splash_screen.dart';
import 'screens/auth/welcome_screen.dart';
import 'screens/caregiver/caregiver_shell.dart';
import 'screens/chw/chw_shell.dart';
import 'screens/notification_routes.dart';
import 'state/push.dart';
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
  await Push.init(); // before the session, which registers the phone once signed in
  final session = Session(ApiClient())..restore();
  _wireNotifications(session);
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

final _navigator = GlobalKey<NavigatorState>();
final _messenger = GlobalKey<ScaffoldMessengerState>();

/// Push notifications: a tap opens the screen it is about; one that arrives while the
/// app is open shows as a banner and refreshes the lists.
void _wireNotifications(Session session) {
  void open(Map<String, dynamic> data) {
    final nav = _navigator.currentState;
    if (nav != null && session.user != null) openFromNotification(nav, session, data);
  }

  Push.taps.stream.listen(open);
  // The notification that opened the app from closed: once signed in and on screen.
  void launchTap() {
    if (!session.restored || session.user == null) return;
    final tap = Push.takeLaunchTap();
    if (tap != null) WidgetsBinding.instance.addPostFrameCallback((_) => open(tap));
  }

  session.addListener(launchTap);
  Push.arrived.stream.listen((m) {
    session.dataChanged();
    final n = m.notification;
    if (n == null) return;
    _messenger.currentState?.showSnackBar(SnackBar(
      content: Text([n.title, n.body].whereType<String>().join('\n')),
      duration: const Duration(seconds: 6),
      action: SnackBarAction(label: tr('Open'), onPressed: () => open(m.data)),
    ));
  });
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
      navigatorKey: _navigator,
      scaffoldMessengerKey: _messenger,
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
