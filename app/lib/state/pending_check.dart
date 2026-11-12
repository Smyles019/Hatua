import '../api/api_client.dart';
import '../i18n/strings.dart';

/// A finished check that could not be sent (#8): kept on the phone and retried later.
/// One per child; a newer check for the same child replaces the older one.
class PendingCheck {
  PendingCheck({
    required this.childId,
    required this.childName,
    required this.responses,
    required this.savedAt,
  });

  final String childId;
  final String childName;
  final Map<String, String> responses; // item -> answer value, as sent to POST /assessments
  final DateTime savedAt;

  Map<String, dynamic> toJson() => {
        'child_id': childId,
        'child_name': childName,
        'responses': responses,
        'saved_at': savedAt.toIso8601String(),
      };

  factory PendingCheck.fromJson(Map<String, dynamic> j) => PendingCheck(
        childId: j['child_id'] as String,
        childName: j['child_name'] as String,
        responses: (j['responses'] as Map).map((k, v) => MapEntry('$k', '$v')),
        savedAt: DateTime.parse(j['saved_at'] as String),
      );
}

/// What to do with a check after a failed send.
enum SendFailure {
  /// No connection, timeout or server error: keep it and try again later.
  retryLater,

  /// Signed out (401): stop trying for now, keep the check.
  signedOut,

  /// The server refused the check itself (for example the child moved into a new
  /// month and the questions changed, or the child was removed): drop it and ask the
  /// caregiver to do the check again.
  rejected,
}

SendFailure classifySendError(Object e) {
  if (e is! ApiException) return SendFailure.retryLater;
  if (e.status == 0 || e.status >= 500) return SendFailure.retryLater;
  if (e.status == 401) return SendFailure.signedOut;
  return SendFailure.rejected;
}

/// Outcome of trying to send every pending check.
class SendReport {
  SendReport({this.sent = const [], this.rejected = const [], this.stillWaiting = 0});
  final List<String> sent; // child names
  final List<String> rejected; // child names, need a new check
  final int stillWaiting;

  /// Plain-language summary for a snackbar, or null if nothing happened.
  String? get message {
    final parts = <String>[];
    if (sent.isNotEmpty) parts.add(tr('Sent the saved check for {names}.', {'names': sent.join(', ')}));
    if (rejected.isNotEmpty) {
      parts.add('The saved check for ${rejected.join(', ')} could not be used. '
          'Please do the check again.');
    }
    if (parts.isEmpty && stillWaiting > 0) {
      return tr('Still no connection. Your saved checks will be sent later.');
    }
    return parts.isEmpty ? null : parts.join(' ');
  }
}
