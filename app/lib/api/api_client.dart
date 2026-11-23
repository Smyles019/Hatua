import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show ValueNotifier, kIsWeb;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../i18n/strings.dart';

/// Base URL of the FastAPI backend. The Android emulator reaches the host machine at
/// 10.0.2.2; the web version on the same machine uses localhost. Override for a real
/// phone or a deployed backend:
///   flutter run --dart-define=API_URL=http://192.168.1.20:8000
const _apiUrlOverride = String.fromEnvironment('API_URL');
final apiBaseUrl = _apiUrlOverride.isNotEmpty
    ? _apiUrlOverride
    : kIsWeb
        ? 'http://localhost:8000'
        : 'http://10.0.2.2:8000';

/// An error the user can read. [status] is the HTTP status (0 = no connection).
class ApiException implements Exception {
  ApiException(this.status, this.message, [this.detail]);
  final int status;
  final String message;

  /// The raw "detail" from the API, for errors that carry data (e.g. Google sign-in's
  /// 428 with the name and email to show on the "Add your phone number" step).
  final dynamic detail;

  bool get unauthorised => status == 401;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({http.Client? client}) : _http = client ?? http.Client();

  final http.Client _http;
  String? token;

  /// Called when the server rejects the token, so the app can sign out.
  void Function()? onUnauthorised;

  // Slow networks are expected; give each request room but not forever.
  static const _timeout = Duration(seconds: 20);

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Uri _uri(String path, [Map<String, String?>? query]) {
    final q = <String, String>{};
    query?.forEach((k, v) {
      if (v != null) q[k] = v;
    });
    return Uri.parse('$apiBaseUrl$path').replace(queryParameters: q.isEmpty ? null : q);
  }

  // ---- Offline reading ----
  //
  // Every answer to a GET is kept on the phone, per signed-in account (cacheUser). With
  // no connection, get() returns the kept copy instead of failing, and [savedDataFrom]
  // says how old the oldest copy on screen is, for the "offline" banner. The first
  // request that reaches the server clears it again and calls [onBackOnline].

  /// The signed-in account whose copies are used; null keeps nothing.
  String? cacheUser;

  /// Null while online; when showing kept copies, the time the oldest was saved.
  final savedDataFrom = ValueNotifier<DateTime?>(null);

  /// Called when a request succeeds after one failed for lack of a connection.
  void Function()? onBackOnline;
  bool _unreachable = false;

  static const _cachePrefix = 'hatua.cache.';

  String? _cacheKey(Uri uri) {
    if (cacheUser == null || uri.path.startsWith('/auth/')) return null;
    return '$_cachePrefix$cacheUser.${uri.path}?${uri.query}';
  }

  Future<dynamic> get(String path, [Map<String, String?>? query]) async {
    final uri = _uri(path, query);
    final key = _cacheKey(uri);
    try {
      final data = await _send(() => _http.get(uri, headers: _headers));
      if (key != null) {
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(
            key, jsonEncode({'at': DateTime.now().toIso8601String(), 'data': data}));
      }
      return data;
    } on ApiException catch (e) {
      if (e.status != 0 || key == null) rethrow;
      final prefs = await SharedPreferences.getInstance();
      final raw = prefs.getString(key);
      if (raw == null) rethrow;
      final saved = jsonDecode(raw) as Map<String, dynamic>;
      final at = DateTime.parse(saved['at'] as String);
      final shown = savedDataFrom.value;
      if (shown == null || at.isBefore(shown)) savedDataFrom.value = at;
      return saved['data'];
    }
  }

  /// Removes every kept copy for [user] (on sign out, so a shared phone shows nothing).
  static Future<void> forgetSaved(String user) async {
    final prefs = await SharedPreferences.getInstance();
    for (final k in prefs.getKeys().where((k) => k.startsWith('$_cachePrefix$user.'))) {
      await prefs.remove(k);
    }
  }

  /// Sends a change. [idempotencyKey] is for changes queued while offline: the server
  /// saves the change once even if it arrives twice.
  Future<dynamic> post(String path, [Object? body, String? idempotencyKey]) => _send(() =>
      _http.post(_uri(path),
          headers: {..._headers, if (idempotencyKey != null) 'Idempotency-Key': idempotencyKey},
          body: jsonEncode(body ?? {})));

  Future<dynamic> put(String path, [Object? body, String? idempotencyKey]) => _send(() =>
      _http.put(_uri(path),
          headers: {..._headers, if (idempotencyKey != null) 'Idempotency-Key': idempotencyKey},
          body: jsonEncode(body ?? {})));

  Future<dynamic> patch(String path, [Object? body]) =>
      _send(() => _http.patch(_uri(path), headers: _headers, body: jsonEncode(body ?? {})));

  Future<dynamic> delete(String path, [Map<String, String?>? query]) =>
      _send(() => _http.delete(_uri(path, query), headers: _headers));

  Future<dynamic> _send(Future<http.Response> Function() call) async {
    http.Response res;
    try {
      res = await call().timeout(_timeout);
    } on TimeoutException {
      _unreachable = true;
      throw ApiException(0, tr('The connection is slow. Please try again.'));
    } on http.ClientException {
      // Also covers socket errors on Android and failed fetches on the web.
      _unreachable = true;
      throw ApiException(0, tr('No connection. Check your data or Wi-Fi and try again.'));
    }
    if (_unreachable || savedDataFrom.value != null) {
      _unreachable = false;
      savedDataFrom.value = null;
      onBackOnline?.call();
    }

    final text = utf8.decode(res.bodyBytes);
    final data = text.isEmpty ? null : _tryJson(text);
    if (res.statusCode >= 200 && res.statusCode < 300) return data;

    if (res.statusCode == 401) onUnauthorised?.call();
    throw ApiException(
        res.statusCode, _message(res.statusCode, data), data is Map ? data['detail'] : null);
  }

  static dynamic _tryJson(String s) {
    try {
      return jsonDecode(s);
    } catch (_) {
      return s;
    }
  }

  /// FastAPI errors come as {"detail": "..."} or {"detail": [{"msg": ...}]}.
  static String _message(int status, dynamic data) {
    final detail = data is Map ? data['detail'] : null;
    if (detail is String) return _sentence(detail);
    if (detail is List && detail.isNotEmpty && detail.first is Map) {
      final msg = (detail.first as Map)['msg']?.toString() ?? '';
      return _sentence(msg.replaceFirst('Value error, ', ''));
    }
    if (status == 503) return tr('The service is not ready yet. Please try again later.');
    if (status >= 500) return tr('Something went wrong on our side. Please try again.');
    return tr('Something went wrong. Please try again.');
  }

  static String _sentence(String s) {
    if (s.isEmpty) return tr('Something went wrong. Please try again.');
    final t = s[0].toUpperCase() + s.substring(1);
    return t.endsWith('.') ? t : '$t.';
  }
}
