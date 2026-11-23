import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import '../api/api_client.dart';

/// Push notifications through Firebase Cloud Messaging, on Android only.
///
/// The backend sends them (backend/app/services/notify.py). This side registers the
/// phone after sign-in, takes it off the account on sign-out (so a shared phone never
/// shows someone else's notifications), and passes taps on to the app, which opens the
/// matching screen. Without android/app/google-services.json, Firebase does not start
/// and the rest of the app works as before, just without notifications.
class Push {
  Push._();

  static bool _ready = false;
  static String? _token;
  static StreamSubscription<String>? _refresh;
  static Map<String, dynamic>? _launch;

  /// The data of a tapped notification (type, id, ...), while the app is running.
  static final taps = StreamController<Map<String, dynamic>>.broadcast();

  /// A notification that arrived while the app was open (Android does not show those).
  static final arrived = StreamController<RemoteMessage>.broadcast();

  static Future<void> init() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return;
    try {
      await Firebase.initializeApp();
    } catch (e) {
      debugPrint('push: Firebase is not set up, notifications are off ($e)');
      return;
    }
    _ready = true;
    FirebaseMessaging.onMessage.listen(arrived.add);
    FirebaseMessaging.onMessageOpenedApp.listen((m) => taps.add(m.data));
    final opened = await FirebaseMessaging.instance.getInitialMessage();
    if (opened != null) _launch = opened.data;
  }

  /// The notification that opened the app from closed, if any. Given out once.
  static Map<String, dynamic>? takeLaunchTap() {
    final tap = _launch;
    _launch = null;
    return tap;
  }

  /// After sign-in: ask to show notifications (Android 13 and later ask the person)
  /// and give the phone's token to the account.
  ///
  /// getToken and onTokenRefresh are deprecated in firebase_messaging 17 in favour of
  /// Firebase Installation IDs (register / onRegistered). That switch is optional and
  /// would change what the backend sends to, so Hatua keeps FCM registration tokens.
  // ignore_for_file: deprecated_member_use
  static Future<void> signedIn(ApiClient api) async {
    if (!_ready) return;
    try {
      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission();
      _token = await messaging.getToken();
      if (_token != null) await api.put('/auth/me/push-token', {'token': _token});
      await _refresh?.cancel();
      _refresh = messaging.onTokenRefresh.listen((t) async {
        _token = t;
        try {
          await api.put('/auth/me/push-token', {'token': t});
        } catch (_) {/* tried again at the next sign-in */}
      });
    } catch (e) {
      debugPrint('push: could not register this phone ($e)');
    }
  }

  /// Before sign-out, while the session still works: take the phone off the account.
  static Future<void> signingOut(ApiClient api) async {
    if (!_ready) return;
    await _refresh?.cancel();
    _refresh = null;
    final token = _token;
    _token = null;
    if (token == null || api.token == null) return;
    try {
      await api.delete('/auth/me/push-token', {'token': token});
    } catch (_) {
      // Offline or the session ran out: the next account to sign in on this phone
      // takes the token over anyway (see the backend).
    }
  }
}
