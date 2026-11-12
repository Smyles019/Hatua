import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hatua/api/models.dart';
import 'package:hatua/widgets/domain.dart';

void main() {
  test('under-24 questions map to language or movement', () {
    expect(DomainStyle.domainOfItem('ddicmm030'), 'language'); // smiles in response
    expect(DomainStyle.domainOfItem('ddicmd141'), 'language');
    expect(DomainStyle.domainOfItem('ddifmd013'), 'motor'); // tower of 2 cubes
    expect(DomainStyle.domainOfItem('ddigmd068'), 'motor'); // walks alone
    // older items unchanged
    expect(DomainStyle.domainOfItem('who_walk_alone'), 'motor');
    expect(DomainStyle.domainOfItem('ecd30'), 'cognitive');
    expect(DomainStyle.domainOfItem('ecd38'), 'social_emotional');
  });

  test('not_assessed is neither on track nor needs support', () {
    final d = DomainResult.fromJson(
        {'domain': 'cognitive', 'label': 'Thinking and learning', 'status': 'not_assessed'});
    expect(d.notAssessed, isTrue);
    expect(d.needsSupport, isFalse);
  });

  testWidgets('note names the areas not checked, or is null', (tester) async {
    late String? two, none;
    await tester.pumpWidget(MaterialApp(home: Builder(builder: (context) {
      two = notCheckedNote(context, ['cognitive', 'social_emotional']);
      none = notCheckedNote(context, []);
      return const SizedBox();
    })));
    expect(two, contains('Thinking and learning, Social and emotional'));
    expect(two, contains('These are checked from 24 months'));
    expect(none, isNull);
  });
}
