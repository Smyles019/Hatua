import 'dart:math';

/// A random key for a change made offline. The server saves a change once per key, so
/// sending it again after a lost answer is safe (app.core.idempotency on the backend).
String newChangeKey() {
  final r = Random.secure();
  return List.generate(16, (_) => r.nextInt(256).toRadixString(16).padLeft(2, '0')).join();
}

/// A change made without signal (a chat message, a weight and height, a CHW outcome),
/// kept on the phone and sent when it is back online. Checks have their own queue
/// (PendingCheck) because the home screen shows them by child.
class QueuedChange {
  QueuedChange({
    required this.key,
    required this.kind,
    required this.path,
    required this.body,
    required this.label,
    required this.savedAt,
  });

  final String key;

  /// 'message', 'growth' or 'outcome': used to show it in the right place meanwhile.
  final String kind;
  final String path;
  final Map<String, dynamic> body;

  /// What it is, for the "could not be sent" message, e.g. "message to your health worker".
  final String label;
  final DateTime savedAt;

  Map<String, dynamic> toJson() => {
        'key': key,
        'kind': kind,
        'path': path,
        'body': body,
        'label': label,
        'saved_at': savedAt.toIso8601String(),
      };

  factory QueuedChange.fromJson(Map<String, dynamic> j) => QueuedChange(
        key: j['key'] as String,
        kind: j['kind'] as String,
        path: j['path'] as String,
        body: Map<String, dynamic>.from(j['body'] as Map),
        label: j['label'] as String,
        savedAt: DateTime.parse(j['saved_at'] as String),
      );
}

/// The change was kept on the phone instead of being sent (no connection).
class SavedForLater implements Exception {}
