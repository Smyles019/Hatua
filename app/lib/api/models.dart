/// Plain data classes for the Hatua API responses (backend/app/schemas).
library;

DateTime? _date(dynamic v) => v == null ? null : DateTime.parse(v as String).toLocal();

class AppUser {
  AppUser({
    required this.userId,
    required this.fullName,
    required this.phoneNumber,
    required this.role,
    required this.linkedChwId,
    required this.isActive,
    this.email,
  });

  /// Set for accounts that sign in with Google.
  final String? email;
  final String userId;
  final String fullName;
  final String phoneNumber;
  final String role; // caregiver | chw | admin
  final String? linkedChwId;
  final bool isActive;

  String get firstName => fullName.trim().split(RegExp(r'\s+')).first;

  factory AppUser.fromJson(Map<String, dynamic> j) => AppUser(
        userId: j['user_id'] as String,
        fullName: j['full_name'] as String,
        phoneNumber: j['phone_number'] as String,
        role: j['role'] as String,
        linkedChwId: j['linked_chw_id'] as String?,
        isActive: j['is_active'] as bool? ?? true,
        email: j['email'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'user_id': userId,
        'full_name': fullName,
        'phone_number': phoneNumber,
        'role': role,
        'linked_chw_id': linkedChwId,
        'is_active': isActive,
        'email': email,
      };
}

/// One weight and height entry (backend: children.growth).
class GrowthEntry {
  GrowthEntry({required this.measuredOn, this.weightKg, this.heightCm});
  final DateTime measuredOn;
  final double? weightKg;
  final double? heightCm;

  Map<String, dynamic> toJson() => {
        'measured_on': measuredOn.toIso8601String().substring(0, 10),
        'weight_kg': weightKg,
        'height_cm': heightCm,
      };

  factory GrowthEntry.fromJson(Map<String, dynamic> j) => GrowthEntry(
        measuredOn: DateTime.parse(j['measured_on'] as String),
        weightKg: (j['weight_kg'] as num?)?.toDouble(),
        heightCm: (j['height_cm'] as num?)?.toDouble(),
      );
}

class Child {
  Child({
    required this.childId,
    required this.caregiverId,
    required this.firstName,
    required this.dateOfBirth,
    required this.sex,
    required this.location,
    required this.ageMonths,
    this.avatarId,
    this.growth = const [],
  });

  final String childId;
  final String caregiverId;
  final String firstName;
  final DateTime dateOfBirth;
  final String sex; // male | female
  final String location;
  final int ageMonths;

  /// Animal avatar (assets/avatars); null until one is picked.
  final String? avatarId;

  /// Weight and height entries, oldest first.
  final List<GrowthEntry> growth;

  factory Child.fromJson(Map<String, dynamic> j) => Child(
        childId: j['child_id'] as String,
        caregiverId: j['caregiver_id'] as String,
        firstName: j['first_name'] as String,
        dateOfBirth: DateTime.parse(j['date_of_birth'] as String),
        sex: j['sex'] as String,
        location: j['location'] as String,
        ageMonths: j['age_months'] as int,
        avatarId: j['avatar_id'] as String?,
        growth: ((j['growth'] as List?) ?? [])
            .map((g) => GrowthEntry.fromJson(g as Map<String, dynamic>))
            .toList(),
      );
}

class AnswerOption {
  AnswerOption(this.value, this.label);
  final String value;
  final String label;
}

class Question {
  Question({required this.item, required this.text, required this.options});
  final String item;
  final String text;
  final List<AnswerOption> options;

  factory Question.fromJson(Map<String, dynamic> j) => Question(
        item: j['item'] as String,
        text: j['text'] as String,
        options: (j['options'] as List)
            .map((o) => AnswerOption(o['value'] as String, o['label'] as String))
            .toList(),
      );
}

class Questionnaire {
  Questionnaire({
    required this.childId,
    required this.ageMonths,
    required this.ageBand,
    required this.method,
    required this.questions,
  });

  final String childId;
  final int ageMonths;
  final String ageBand;
  final String method; // model | milestone_check
  final List<Question> questions;

  factory Questionnaire.fromJson(Map<String, dynamic> j) => Questionnaire(
        childId: j['child_id'] as String,
        ageMonths: j['age_months'] as int,
        ageBand: j['age_band'] as String,
        method: j['method'] as String,
        questions: (j['questions'] as List)
            .map((q) => Question.fromJson(q as Map<String, dynamic>))
            .toList(),
      );
}

class DomainResult {
  DomainResult({required this.domain, required this.label, required this.status});
  final String domain; // motor | language | cognitive | social_emotional
  final String label;
  final String status; // on_track | needs_support

  bool get needsSupport => status == 'needs_support';

  factory DomainResult.fromJson(Map<String, dynamic> j) => DomainResult(
        domain: j['domain'] as String,
        label: j['label'] as String,
        status: j['status'] as String,
      );
}

class Reason {
  Reason({required this.item, required this.domain, required this.question});
  final String item;
  final String domain;
  final String question; // short wording, e.g. "jumping with both feet"

  factory Reason.fromJson(Map<String, dynamic> j) => Reason(
        item: j['item'] as String,
        domain: j['domain'] as String,
        question: (j['question'] ?? j['item']) as String,
      );
}

class Assessment {
  Assessment({
    required this.predictionId,
    required this.childId,
    required this.childName,
    this.childAvatarId,
    required this.ageMonths,
    required this.method,
    required this.riskLevel,
    required this.anomalyFlag,
    required this.sentToChw,
    required this.domains,
    required this.topReasons,
    required this.chwOutcome,
    required this.caregiverMessage,
    required this.reviewedAt,
    required this.submittedAt,
    this.caregiverName,
    this.caregiverPhone,
    this.location,
    this.answers = const {},
  });

  final String predictionId;
  final String childId;
  final String childName;
  final String? childAvatarId;
  final int ageMonths;
  final String method;
  final String riskLevel; // low | medium | high
  final bool anomalyFlag;
  final bool sentToChw;
  final List<DomainResult> domains;
  final List<Reason> topReasons;
  final String? chwOutcome;
  final String? caregiverMessage;
  final DateTime? reviewedAt;
  final DateTime submittedAt;

  // Present only on CHW case rows.
  final String? caregiverName;
  final String? caregiverPhone;
  final String? location;
  final Map<String, String> answers;

  factory Assessment.fromJson(Map<String, dynamic> j) {
    final cg = j['caregiver'] as Map<String, dynamic>?;
    final answers = (j['answers'] as Map?)?.map((k, v) => MapEntry('$k', '$v')) ?? {};
    return Assessment(
      predictionId: j['prediction_id'] as String,
      childId: j['child_id'] as String,
      childName: j['child_name'] as String,
      childAvatarId: j['child_avatar_id'] as String?,
      ageMonths: j['age_months'] as int,
      method: j['method'] as String,
      riskLevel: j['risk_level'] as String,
      anomalyFlag: j['anomaly_flag'] as bool? ?? false,
      sentToChw: j['sent_to_chw'] as bool? ?? false,
      domains: (j['domains'] as List)
          .map((d) => DomainResult.fromJson(d as Map<String, dynamic>))
          .toList(),
      topReasons: (j['top_reasons'] as List)
          .map((r) => Reason.fromJson(r as Map<String, dynamic>))
          .toList(),
      chwOutcome: j['chw_outcome'] as String?,
      caregiverMessage: j['caregiver_message'] as String?,
      reviewedAt: _date(j['reviewed_at']),
      submittedAt: _date(j['submitted_at'])!,
      caregiverName: cg?['full_name'] as String?,
      caregiverPhone: cg?['phone_number'] as String?,
      location: j['location'] as String?,
      answers: answers,
    );
  }
}

class HistoryPoint {
  HistoryPoint(this.submittedAt, this.ageMonths, this.riskLevel);
  final DateTime submittedAt;
  final int ageMonths;
  final String riskLevel;
}

class Milestones {
  Milestones({required this.domains, required this.history});
  final List<DomainResult> domains;
  final List<HistoryPoint> history;

  String? get latestRisk => history.isEmpty ? null : history.last.riskLevel;

  factory Milestones.fromJson(Map<String, dynamic> j) => Milestones(
        domains: (j['domains'] as List)
            .map((d) => DomainResult.fromJson(d as Map<String, dynamic>))
            .toList(),
        history: (j['history'] as List)
            .map((h) => HistoryPoint(_date(h['submitted_at'])!, h['age_months'] as int,
                h['risk_level'] as String))
            .toList(),
      );
}

class LinkedCaregiver {
  LinkedCaregiver({required this.user, required this.children, required this.openCases});
  final AppUser user;
  final int children;
  final int openCases;

  factory LinkedCaregiver.fromJson(Map<String, dynamic> j) => LinkedCaregiver(
        user: AppUser.fromJson(j),
        children: j['children'] as int? ?? 0,
        openCases: j['open_cases'] as int? ?? 0,
      );
}

class UsageSummary {
  UsageSummary(this.raw);
  final Map<String, dynamic> raw;

  Map<String, int> _ints(String key) =>
      (raw[key] as Map).map((k, v) => MapEntry('$k', (v as num).toInt()));

  Map<String, int> get users => _ints('users');
  Map<String, int> get byRisk => _ints('by_risk_level');
  Map<String, int> get outcomes => _ints('outcomes');
  int get children => raw['children'] as int;
  int get assessments => raw['assessments'] as int;
  int get flagged => raw['flagged_for_chw'] as int;
  int get anomalies => raw['anomaly_flags'] as int;
  int get awaiting => raw['awaiting_review'] as int;
}
