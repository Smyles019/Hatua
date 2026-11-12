import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
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

  Future<dynamic> get(String path, [Map<String, String?>? query]) =>
      _send(() => _http.get(_uri(path, query), headers: _headers));

  Future<dynamic> post(String path, [Object? body]) =>
      _send(() => _http.post(_uri(path), headers: _headers, body: jsonEncode(body ?? {})));

  Future<dynamic> put(String path, [Object? body]) =>
      _send(() => _http.put(_uri(path), headers: _headers, body: jsonEncode(body ?? {})));

  Future<dynamic> patch(String path, [Object? body]) =>
      _send(() => _http.patch(_uri(path), headers: _headers, body: jsonEncode(body ?? {})));

  Future<dynamic> _send(Future<http.Response> Function() call) async {
    http.Response res;
    try {
      res = await call().timeout(_timeout);
    } on TimeoutException {
      throw ApiException(0, tr('The connection is slow. Please try again.'));
    } on http.ClientException {
      // Also covers socket errors on Android and failed fetches on the web.
      throw ApiException(0, tr('No connection. Check your data or Wi-Fi and try again.'));
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
