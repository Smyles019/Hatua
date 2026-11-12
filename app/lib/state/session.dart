import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../api/api_client.dart';
import '../api/models.dart';
import 'google_auth.dart';

/// A first Google sign-in: the account needs a phone number before it can be created.
class NeedsPhone implements Exception {}

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

  Future<void> restore() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_kToken);
    final userJson = prefs.getString(_kUser);
    welcomed = prefs.getBool(_kWelcomed) ?? false;
    if (token != null && userJson != null) {
      api.token = token;
      user = AppUser.fromJson(jsonDecode(userJson) as Map<String, dynamic>);
    }
    restored = true;
    notifyListeners();
  }

  Future<void> signIn(String phone, String password) async {
    final data = await api.post('/auth/login', {'phone_number': phone, 'password': password});
    await _save(data as Map<String, dynamic>);
  }

  Future<void> register(String fullName, String phone, String password) async {
    final data = await api.post('/auth/register',
        {'full_name': fullName, 'phone_number': phone, 'password': password});
    await _save(data as Map<String, dynamic>);
  }

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
    notifyListeners();
  }

  Future<void> signOut() async {
    await GoogleAuth.signOut();
    api.token = null;
    user = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kToken);
    await prefs.remove(_kUser);
    notifyListeners();
  }
}
