import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart';
import '../api/models.dart';
import 'google_auth.dart';
import 'pending_check.dart';

/// A first Google sign-in: the account needs a phone number before it can be created.
class NeedsPhone implements Exception {}

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
class Session extends ChangeNotifier {
  Session(this.api) {
    api.onUnauthorised = () {
      if (user != null) signOut();
    };
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
    notifyListeners();
  }

  /// Tries to send every saved check, oldest first. Safe to call often: does nothing
  /// while a send is already running or when nothing is waiting.
  Future<SendReport> sendPending() async {
    if (sendingPending || pending.isEmpty || user == null) return SendReport();
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
        await api.post('/assessments', {'child_id': p.childId, 'responses': p.responses});
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
    sendingPending = false;
    if (sent.isNotEmpty) {
      dataChanged(); // also notifies
    } else {
      notifyListeners();
    }
    return SendReport(sent: sent, rejected: rejected, stillWaiting: keep.length);
  }

  Future<void> restore() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_kToken);
    final userJson = prefs.getString(_kUser);
    welcomed = prefs.getBool(_kWelcomed) ?? false;
    if (token != null && userJson != null) {
      api.token = token;
      user = AppUser.fromJson(jsonDecode(userJson) as Map<String, dynamic>);
    }
    await _loadPending();
    restored = true;
    notifyListeners();
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
      if (e.status == 428) throw NeedsPhone();
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
    await _loadPending();
    notifyListeners();
  }

  Future<void> signOut() async {
    await GoogleAuth.signOut();
    api.token = null;
    user = null;
    pending = []; // still stored for this user; reloaded on their next sign-in
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kToken);
    await prefs.remove(_kUser);
    notifyListeners();
  }
}
