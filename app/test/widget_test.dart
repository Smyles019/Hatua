import 'package:flutter_test/flutter_test.dart';
import 'package:hatua/widgets/common.dart';

void main() {
  test('ageLabel reads naturally', () {
    expect(ageLabel(1), '1 month');
    expect(ageLabel(18), '18 months');
    expect(ageLabel(24), '2 years');
    expect(ageLabel(37), '3 years 1 month');
  });

  test('phoneValidator accepts the formats the backend accepts', () {
    for (final ok in ['0712345678', '0712 345 678', '+254712345678', '254112345678']) {
      expect(phoneValidator(ok), isNull, reason: ok);
    }
    for (final bad in ['', '12345', '0812345678', '+255712345678']) {
      expect(phoneValidator(bad), isNotNull, reason: bad);
    }
  });

  test('passwordValidator needs 6 characters', () {
    expect(passwordValidator('12345'), isNotNull);
    expect(passwordValidator('123456'), isNull);
  });
}
