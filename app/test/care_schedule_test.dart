import 'package:flutter_test/flutter_test.dart';
import 'package:hatua/screens/caregiver/care_schedule.dart';
import 'package:hatua/widgets/domain.dart';

void main() {
  CareItem find(List<CareItem> items, String title) =>
      items.firstWhere((i) => i.title.startsWith(title));

  test('a newborn: 6-week vaccines first, vitamin A at 6 months, deworming at 1 year', () {
    final care = nextCare(DateTime(2026, 11, 1), today: DateTime(2026, 11, 5));
    expect(find(care, 'Vaccines at 6 weeks').due, DateTime(2026, 12, 13));
    expect(find(care, 'Vitamin A').due, DateTime(2027, 5, 1));
    expect(find(care, 'Deworming').due, DateTime(2027, 11, 1));
    expect(find(care, 'Clinic visit').due, DateTime(2026, 12, 1));
    expect(care.first.title, 'Clinic visit'); // soonest first
  });

  test('something due in the last two weeks still shows, as due now', () {
    final today = DateTime(2027, 5, 10);
    final care = nextCare(DateTime(2026, 11, 1), today: today);
    final vitaminA = find(care, 'Vitamin A');
    expect(vitaminA.due, DateTime(2027, 5, 1));
    expect(vitaminA.dueNow(today), isTrue);
    // three weeks later it has moved on to the 12-month dose
    final later = nextCare(DateTime(2026, 11, 1), today: DateTime(2027, 5, 31));
    expect(find(later, 'Vitamin A').due, DateTime(2027, 11, 1));
  });

  test('a two-year-old has no vaccine left on the routine list', () {
    final care = nextCare(DateTime(2024, 11, 1), today: DateTime(2026, 11, 20));
    expect(care.any((i) => i.title.contains('accine')), isFalse);
    expect(find(care, 'Vitamin A').due, DateTime(2027, 5, 1)); // 30 months
    expect(find(care, 'Deworming').due, DateTime(2027, 5, 1));
  });

  test('month ends are handled and nothing shows from the fifth birthday', () {
    final care = nextCare(DateTime(2026, 8, 31), today: DateTime(2026, 9, 1));
    expect(find(care, 'Clinic visit').due, DateTime(2026, 9, 30));
    expect(nextCare(DateTime(2021, 11, 1), today: DateTime(2026, 11, 1)), isEmpty);
  });

  test('movement questions are told apart as big movements or hand skills', () {
    expect(motorKindOfItem('ddigmd068'), 'gross');
    expect(motorKindOfItem('ddifmd013'), 'fine');
    expect(motorKindOfItem('ddicmm037'), isNull); // language
    expect(motorKindOfItem('who_walk_alone'), 'gross');
    expect(motorKindOfItem('ecd22'), 'gross');
    expect(motorKindOfItem('ecd24'), 'fine');
    expect(motorKindOfItem('ecd30'), isNull);
  });
}

// Growth chart reference values are checked in growth_chart_test.dart.
