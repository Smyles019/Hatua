import '../../api/api_client.dart';
import '../../api/models.dart';

/// A child with their checks, newest first.
class ChildWithChecks {
  ChildWithChecks(this.child, this.checks);
  final Child child;
  final List<Assessment> checks;

  Assessment? get latest => checks.isEmpty ? null : checks.first;
}

Future<List<Child>> loadChildren(ApiClient api) async {
  final data = await api.get('/children') as List;
  return data.map((c) => Child.fromJson(c as Map<String, dynamic>)).toList();
}

Future<List<Assessment>> loadChecks(ApiClient api, String childId) async {
  final data = await api.get('/children/$childId/assessments') as List;
  return data.map((a) => Assessment.fromJson(a as Map<String, dynamic>)).toList();
}

Future<List<ChildWithChecks>> loadChildrenWithChecks(ApiClient api) async {
  final children = await loadChildren(api);
  final checks = await Future.wait(children.map((c) => loadChecks(api, c.childId)));
  return [for (var i = 0; i < children.length; i++) ChildWithChecks(children[i], checks[i])];
}

/// Rough guide for the next check, from the age bands the backend uses: CREDI-style
/// 6-month bands under 3 years, then one check in the 36 to 59 month window.
/// Shown as guidance only; nothing is scheduled or enforced.
DateTime? nextCheckDue(Child child, Assessment? latest) {
  if (latest == null) return DateTime.now();
  if (child.ageMonths >= 36) {
    return latest.ageMonths >= 36 ? null : DateTime.now();
  }
  return latest.submittedAt.add(const Duration(days: 182));
}
