import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:hatua/api/api_client.dart';
import 'package:hatua/state/pending_check.dart';
import 'package:hatua/state/session.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _user = {
  'user_id': 'u1',
  'full_name': 'Akinyi Otieno',
  'phone_number': '+254712345678',
  'role': 'caregiver',
  'linked_chw_id': null,
  'is_active': true,
};

PendingCheck _check(String id, String name, int minutesAgo) => PendingCheck(
      childId: id,
      childName: name,
      responses: {'ddigmd068': 'yes'},
      savedAt: DateTime.now().subtract(Duration(minutes: minutesAgo)),
    );

/// A signed-in Session whose API answers POST /assessments with [reply].
Future<(Session, List<String>)> _session(
    Future<http.Response> Function(Map<String, dynamic> body) reply) async {
  SharedPreferences.setMockInitialValues({
    'hatua.token': 't',
    'hatua.user': jsonEncode(_user),
  });
  final posted = <String>[];
  final api = ApiClient(client: MockClient((req) async {
    final body = jsonDecode(req.body) as Map<String, dynamic>;
    posted.add(body['child_id'] as String);
    return reply(body);
  }));
  final s = Session(api);
  await s.restore();
  return (s, posted);
}

void main() {
  test('a saved check survives a round trip through JSON', () {
    final c = _check('c1', 'Amani', 0);
    final back = PendingCheck.fromJson(jsonDecode(jsonEncode(c.toJson())) as Map<String, dynamic>);
    expect(back.childId, 'c1');
    expect(back.responses, {'ddigmd068': 'yes'});
    expect(back.savedAt, c.savedAt);
  });

  test('which failures keep a check', () {
    expect(classifySendError(ApiException(0, 'offline')), SendFailure.retryLater);
    expect(classifySendError(ApiException(503, 'down')), SendFailure.retryLater);
    expect(classifySendError(ApiException(401, 'expired')), SendFailure.signedOut);
    expect(classifySendError(ApiException(422, 'questions changed')), SendFailure.rejected);
    expect(classifySendError(ApiException(404, 'no child')), SendFailure.rejected);
    expect(classifySendError(StateError('x')), SendFailure.retryLater);
  });

  test('a newer check for the same child replaces the older one, and is stored', () async {
    final (s, _) = await _session((_) async => http.Response('{}', 201));
    await s.savePending(_check('c1', 'Amani', 10));
    await s.savePending(_check('c1', 'Amani', 0));
    await s.savePending(_check('c2', 'Neema', 5));
    expect(s.pending.map((p) => p.childId), ['c1', 'c2']);

    final again = Session(s.api);
    await again.restore();
    expect(again.pending.length, 2);
  });

  test('sent checks are removed and the data refreshes', () async {
    final (s, posted) = await _session((_) async => http.Response('{}', 201));
    await s.savePending(_check('c2', 'Neema', 1));
    await s.savePending(_check('c1', 'Amani', 10));
    final before = s.dataVersion;
    final r = await s.sendPending();
    expect(posted, ['c1', 'c2']); // oldest first
    expect(r.sent, ['Amani', 'Neema']);
    expect(s.pending, isEmpty);
    expect(s.dataVersion, before + 1);
  });

  test('still offline: everything is kept and nothing else is tried', () async {
    final (s, posted) = await _session((_) async => throw http.ClientException('offline'));
    await s.savePending(_check('c1', 'Amani', 10));
    await s.savePending(_check('c2', 'Neema', 1));
    final r = await s.sendPending();
    expect(posted, ['c1']);
    expect(s.pending.length, 2);
    expect(r.message, contains('Still no connection'));
  });

  test('a check the server refuses is dropped and named', () async {
    final (s, _) = await _session((body) async => body['child_id'] == 'c1'
        ? http.Response(jsonEncode({'detail': {'missing': ['ddigmd070']}}), 422)
        : http.Response('{}', 201));
    await s.savePending(_check('c1', 'Amani', 10));
    await s.savePending(_check('c2', 'Neema', 1));
    final r = await s.sendPending();
    expect(r.rejected, ['Amani']);
    expect(r.sent, ['Neema']);
    expect(s.pending, isEmpty);
    expect(r.message, contains('do the check again'));
  });

  test('signing out hides the checks; signing back in brings them back', () async {
    final (s, _) = await _session((_) async => http.Response('{}', 201));
    await s.savePending(_check('c1', 'Amani', 0));
    await s.signOut();
    expect(s.pending, isEmpty);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getString('hatua.pending.u1'), isNotNull);
  });
}
