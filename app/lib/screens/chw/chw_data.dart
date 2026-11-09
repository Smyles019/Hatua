import '../../api/api_client.dart';
import '../../api/models.dart';

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

const outcomeLabels = {
  'refer_to_facility': 'Refer to facility',
  'reviewed_not_concerning': 'Reviewed, not concerning',
  'unreachable': 'Could not reach caregiver',
};
