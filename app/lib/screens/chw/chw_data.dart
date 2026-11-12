import '../../api/api_client.dart';
import '../../api/models.dart';
import '../../i18n/strings.dart';

/// Routed cases (medium or high risk, or an anomaly flag) for caregivers linked to
/// this CHW. Open cases only unless [includeReviewed].
Future<List<Assessment>> loadCases(ApiClient api, {bool includeReviewed = false}) async {
  final data = await api.get('/chw/cases', {'include_reviewed': '$includeReviewed'}) as List;
  return data.map((a) => Assessment.fromJson(a as Map<String, dynamic>)).toList();
}

Future<List<LinkedCaregiver>> loadCaregivers(ApiClient api) async {
  final data = await api.get('/chw/caregivers') as List;
  return data.map((c) => LinkedCaregiver.fromJson(c as Map<String, dynamic>)).toList();
}

/// Ask a CHW inbox: threads of caregivers linked to this CHW, unanswered first.
Future<List<ThreadSummary>> loadThreads(ApiClient api) async {
  final data = await api.get('/messages/threads') as List;
  return data.map((t) => ThreadSummary.fromJson(t as Map<String, dynamic>)).toList();
}

Map<String, String> get outcomeLabels => {
      'refer_to_facility': tr('Refer to facility'),
      'reviewed_not_concerning': tr('Reviewed, not concerning'),
      'unreachable': tr('Could not reach caregiver'),
    };
