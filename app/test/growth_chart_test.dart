import 'package:flutter_test/flutter_test.dart';
import 'package:hatua/widgets/growth_chart.dart';

void main() {
  test('reference weights match the WHO field tables at table ages', () {
    // WHO weight-for-age simplified field tables (percentiles): 3rd, median, 97th.
    void same(String sex, double months, List<double> want) {
      final (p3, p50, p97) = weightReference(sex, months);
      expect(p3, closeTo(want[0], 1e-9), reason: '$sex $months 3rd');
      expect(p50, closeTo(want[1], 1e-9), reason: '$sex $months median');
      expect(p97, closeTo(want[2], 1e-9), reason: '$sex $months 97th');
    }

    same('male', 0, [2.5, 3.3, 4.3]);
    same('male', 12, [7.8, 9.6, 11.8]);
    same('male', 60, [14.3, 18.3, 23.8]);
    same('female', 0, [2.4, 3.2, 4.2]);
    same('female', 24, [9.2, 11.5, 14.6]);
    same('female', 60, [14.0, 18.2, 24.4]);
  });

  test('ages between table rows are interpolated and out-of-range ages are clamped', () {
    final (p3, p50, p97) = weightReference('male', 1.5); // between birth and 3 months
    expect(p3, closeTo(3.8, 0.01));
    expect(p50, closeTo(4.85, 0.01));
    expect(p97, closeTo(6.1, 0.01));
    expect(weightReference('female', 75), weightReference('female', 60));
    expect(weightReference('female', -2), weightReference('female', 0));
  });

  test('age on the day of a measurement', () {
    expect(ageInMonthsOn(DateTime(2026, 1, 1), DateTime(2026, 7, 1)), closeTo(5.95, 0.05));
  });
}
