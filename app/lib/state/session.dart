import 'dart:async';
import 'dart:convert';

import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart';
import '../api/models.dart';
import '../i18n/strings.dart';
import 'google_auth.dart';
import 'outbox.dart';
import 'pending_check.dart';
import 'push.dart';

/// A first Google sign-in: the account needs a phone number before it can be created
/// (a new caregiver), or before it can be used (a CHW invited by an administrator).
class NeedsPhone implements Exception {
  NeedsPhone([this.role = 'caregiver']);

  /// 'caregiver' or 'chw', from the server, so the phone step speaks to the right person.
  final String role;
}

/// Email sign-in with the right password, but the email has not been confirmed yet.
class NeedsVerification implements Exception {
  NeedsVerification(this.email);
  final String email;
}

/// Signed-in user and access token. Kept on the device so the caregiver does not have
/// to sign in on every visit; cleared on sign out or when the server rejects the token.
///
/// Note: SharedPreferences is not encrypted. flutter_secure_storage is the hardening
/// step before any real deployment.
class Session extends ChangeNotifier with WidgetsBindingObserver {
  Session(this.api) {
    api.onUnauthorised = () {
      if (user != null) signOut();
    };
    // Back online: send what was saved, and reload the screens with fresh data.
    api.onBackOnline = () {
      unawaited(_sendInBackground());
      dataChanged();
    };
    WidgetsBinding.instance.addObserver(this);
  }

  /// Shows what a send in the background did (wired to the app's snackbar in main.dart).
  void Function(String message)? onSentInBackground;

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) unawaited(_sendInBackground());
  }

  Future<void> _sendInBackground() async {
    final msg = (await sendPending()).message;
    final quietWait = msg == tr('Still no connection. Your saved checks will be sent later.');
    if (msg != null && !quietWait) onSentInBackground?.call(msg);
  }

  // While something is waiting, try again every minute (there is no reliable "signal is
  // back" event on every phone, so a quiet retry is simpler and costs one request).
  Timer? _retry;
  void _scheduleRetry() {
    if (waitingCount == 0 || user == null) {
      _retry?.cancel();
      _retry = null;
    } else {
      _retry ??= Timer.periodic(const Duration(minutes: 1), (_) => _sendInBackground());
    }
  }

  int get waitingCount => pending.length + queued.length;

  // ---- Other changes made offline (messages, growth, outcomes) ----

  List<QueuedChange> queued = [];
  String? get _kQueued => user == null ? null : 'hatua.queue.${user!.userId}';

  Future<void> _loadQueued() async {
    final key = _kQueued;
    final prefs = await SharedPreferences.getInstance();
    final raw = key == null ? null : prefs.getString(key);
    queued = raw == null
        ? []
        : (jsonDecode(raw) as List)
            .map((j) => QueuedChange.fromJson(j as Map<String, dynamic>))
            .toList();
  }

  Future<void> _storeQueued() async {
    final key = _kQueued;
    if (key == null) return;
    final prefs = await SharedPreferences.getInstance();
    if (queued.isEmpty) {
      await prefs.remove(key);
    } else {
      await prefs.setString(key, jsonEncode(queued.map((q) => q.toJson()).toList()));
    }
  }

  Future<dynamic> _sendChange(QueuedChange c) => c.method == 'put'
      ? api.put(c.path, c.body, c.key)
      : api.post(c.path, c.body, c.key);

  /// Sends a change, or keeps it on the phone when there is no connection and throws
  /// [SavedForLater]. Other errors (the server refused it) are thrown as usual.
  Future<dynamic> sendOrQueue(
      {required String kind,
      required String path,
      required Map<String, dynamic> body,
      required String label,
      String method = 'post'}) async {
    final change = QueuedChange(
        key: newChangeKey(), kind: kind, path: path, body: body, label: label,
        savedAt: DateTime.now(), method: method);
    try {
      return await _sendChange(change);
    } catch (e) {
      if (classifySendError(e) != SendFailure.retryLater) rethrow;
      queued = [...queued, change];
      await _storeQueued();
      _scheduleRetry();
      notifyListeners();
      throw SavedForLater();
    }
  }

  final ApiClient api;
  AppUser? user;
  bool restored = false;

  static const _kToken = 'hatua.token';
  static const _kUser = 'hatua.user';
  static const _kWelcomed = 'hatua.welcomed';

  /// Whether the welcome pages have been seen on this phone.
  bool welcomed = true;

  Future<void> finishWelcome() async {
    welcomed = true;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kWelcomed, true);
  }

  bool get signedIn => user != null;

  /// Bumped after anything that changes server data (new child, new check, outcome),
  /// so tabs that watch it reload.
  int dataVersion = 0;
  void dataChanged() {
    dataVersion++;
    notifyListeners();
  }

  // ---- Checks waiting to be sent (#8) ----
  //
  // Stored per user, so a shared phone never sends one caregiver's check from another
  // caregiver's account. Signing out keeps them; they come back on the next sign-in.

  List<PendingCheck> pending = [];
  bool sendingPending = false;

  String? get _kPending => user == null ? null : 'hatua.pending.${user!.userId}';

  Future<void> _loadPending() async {
    final key = _kPending;
    if (key == null) {
      pending = [];
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(key);
    pending = raw == null
        ? []
        : (jsonDecode(raw) as List)
            .map((j) => PendingCheck.fromJson(j as Map<String, dynamic>))
            .toList();
  }

  Future<void> _storePending() async {
    final key = _kPending;
    if (key == null) return;
    final prefs = await SharedPreferences.getInstance();
    if (pending.isEmpty) {
      await prefs.remove(key);
    } else {
      await prefs.setString(key, jsonEncode(pending.map((p) => p.toJson()).toList()));
    }
  }

  /// Keeps a check that could not be sent. Replaces an older one for the same child.
  Future<void> savePending(PendingCheck check) async {
    pending = [...pending.where((p) => p.childId != check.childId), check];
    await _storePending();
    _scheduleRetry();
    notifyListeners();
  }

  /// Tries to send every saved check, then every other saved change, oldest first.
  /// Safe to call often: does nothing while a send is already running or when nothing
  /// is waiting.
  Future<SendReport> sendPending() async {
    if (sendingPending || waitingCount == 0 || user == null) return SendReport();
    sendingPending = true;
    notifyListeners();
    final sent = <String>[], rejected = <String>[];
    final keep = <PendingCheck>[];
    final queue = [...pending]..sort((a, b) => a.savedAt.compareTo(b.savedAt));
    var stop = false;
    for (final p in queue) {
      if (stop) {
        keep.add(p);
        continue;
      }
      try {
        await api.post(
            '/assessments', {'child_id': p.childId, 'responses': p.responses}, p.key);
        sent.add(p.childName);
      } catch (e) {
        switch (classifySendError(e)) {
          case SendFailure.retryLater:
            keep.add(p);
            stop = true; // still offline: no point trying the rest now
          case SendFailure.signedOut:
            keep.add(p);
            stop = true;
          case SendFailure.rejected:
            rejected.add(p.childName);
        }
      }
    }
    pending = keep;
    await _storePending();

    // Then messages, growth entries and outcomes, in the order they were made.
    var changesSent = 0;
    final refused = <String>[];
    final keepChanges = <QueuedChange>[];
    for (final c in queued) {
      if (stop) {
        keepChanges.add(c);
        continue;
      }
      try {
        await _sendChange(c);
        changesSent++;
      } catch (e) {
        if (classifySendError(e) == SendFailure.rejected) {
          refused.add(c.label);
        } else {
          keepChanges.add(c);
          stop = true;
        }
      }
    }
    queued = keepChanges;
    await _storeQueued();

    sendingPending = false;
    _scheduleRetry();
    if (sent.isNotEmpty || changesSent > 0) {
      dataChanged(); // also notifies
    } else {
      notifyListeners();
    }
    return SendReport(
        sent: sent,
        rejected: rejected,
        stillWaiting: keep.length + keepChanges.length,
        changesSent: changesSent,
        changesRefused: refused);
  }

  Future<void> restore() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_kToken);
    final userJson = prefs.getString(_kUser);
    welcomed = prefs.getBool(_kWelcomed) ?? false;
    if (token != null && userJson != null) {
      api.token = token;
      user = AppUser.fromJson(jsonDecode(userJson) as Map<String, dynamic>);
      api.cacheUser = user!.userId;
    }
    await _loadPending();
    await _loadQueued();
    _scheduleRetry();
    restored = true;
    notifyListeners();
    // Already signed in from last time: make sure this phone still gets notifications.
    if (user != null) unawaited(Push.signedIn(api));
  }

  /// Signs in with email and password. If the password is right but the email has not
  /// been confirmed yet, the backend answers 403 and this throws [NeedsVerification].
  Future<void> signIn(String email, String password) async {
    try {
      final data = await api.post('/auth/login', {'email': email, 'password': password});
      await _save(data as Map<String, dynamic>);
    } on ApiException catch (e) {
      final d = e.detail;
      if (e.status == 403 && d is Map && d['needs_verification'] == true) {
        throw NeedsVerification((d['email'] as String?) ?? email);
      }
      rethrow;
    }
  }

  /// Creates the caregiver account and has a confirmation link emailed. There is no
  /// session yet: the person signs in after opening the link. Returns the email as the
  /// backend stored it.
  Future<String> register(String fullName, String email, String phone, String password) async {
    final data = await api.post('/auth/register',
        {'full_name': fullName, 'email': email, 'phone_number': phone, 'password': password});
    return (data as Map<String, dynamic>)['email'] as String;
  }

  Future<void> resendVerification(String email) =>
      api.post('/auth/verify/resend', {'email': email});

  /// Has a "choose a new password" link emailed. The backend gives the same answer
  /// whether or not the email has an account.
  Future<void> forgotPassword(String email) =>
      api.post('/auth/password/forgot', {'email': email});

  /// Signs in with a Google ID token. The first time, the backend needs a phone number
  /// to create the account: it answers 428 and this throws [NeedsPhone].
  Future<void> signInWithGoogle(String idToken, {String? phone}) async {
    try {
      final data = await api.post('/auth/google', {
        'id_token': idToken,
        if (phone != null) 'phone_number': phone,
      });
      await _save(data as Map<String, dynamic>);
    } on ApiException catch (e) {
      if (e.status == 428) {
        final d = e.detail;
        throw NeedsPhone(d is Map && d['role'] == 'chw' ? 'chw' : 'caregiver');
      }
      rethrow;
    }
  }

  Future<void> refreshUser() async {
    final data = await api.get('/auth/me');
    user = AppUser.fromJson(data as Map<String, dynamic>);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kUser, jsonEncode(user!.toJson()));
    notifyListeners();
  }

  Future<void> _save(Map<String, dynamic> session) async {
    api.token = session['access_token'] as String;
    user = AppUser.fromJson(session['user'] as Map<String, dynamic>);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kToken, api.token!);
    await prefs.setString(_kUser, jsonEncode(user!.toJson()));
    api.cacheUser = user!.userId;
    await _loadPending();
    await _loadQueued();
    _scheduleRetry();
    notifyListeners();
    unawaited(Push.signedIn(api)); // this phone now gets this person's notifications
  }

  bool _signingOut = false;

  Future<void> signOut() async {
    // Also reached when the server rejects the token, possibly while the push token is
    // being removed below; one sign-out at a time.
    if (_signingOut) return;
    _signingOut = true;
    try {
      await _signOut();
    } finally {
      _signingOut = false;
    }
  }

  Future<void> _signOut() async {
    await Push.signingOut(api); // first, while the session still works
    await GoogleAuth.signOut();
    api.token = null;
    // The copies kept for reading offline go (a shared phone shows nothing of this
    // person's); what is waiting to be sent stays for their next sign-in.
    final leaving = user?.userId;
    if (leaving != null) await ApiClient.forgetSaved(leaving);
    api.cacheUser = null;
    api.savedDataFrom.value = null;
    user = null;
    pending = []; // still stored for this user; reloaded on their next sign-in
    queued = [];
    _scheduleRetry();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kToken);
    await prefs.remove(_kUser);
    notifyListeners();
  }
}
