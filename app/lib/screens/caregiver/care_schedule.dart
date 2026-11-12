/// What is coming up at the clinic for a child, worked out from the date of birth.
///
/// The schedule is the routine one printed in the MOH Mother and Child Health Handbook
/// (2020): clinic visit every month, vitamin A every six months from 6 months, deworming
/// every six months from 1 year, and the childhood vaccines. The app does not know what
/// the child has already received, so these are reminders of when each is due, not a
/// record. The clinic booklet stays the record.
library;

import '../../i18n/strings.dart';

class CareItem {
  CareItem(this.title, this.detail, this.due);
  final String title;
  final String detail;
  final DateTime due;

  /// Due today or in the last two weeks.
  bool dueNow(DateTime today) => !due.isAfter(today);
}

DateTime _addMonths(DateTime d, int months) {
  final total = d.year * 12 + d.month - 1 + months;
  final y = total ~/ 12, m = total % 12 + 1;
  final lastDay = DateTime(y, m + 1, 0).day;
  return DateTime(y, m, d.day > lastDay ? lastDay : d.day);
}

/// (age in days, name) for vaccines given at an age in weeks.
const _vaccinesByWeek = [
  (42, 'Vaccines at 6 weeks'),
  (70, 'Vaccines at 10 weeks'),
  (98, 'Vaccines at 14 weeks'),
];

/// (age in months, name) for vaccines given at an age in months.
const _vaccinesByMonth = [
  (9, 'Measles-rubella vaccine, first dose'),
  (18, 'Measles-rubella vaccine, second dose'),
];

// The vaccine names above are English keys, put into the chosen language where shown.
String _age(int months) => months < 12
    ? tr('at {n} months', {'n': months})
    : months == 12
        ? tr('at 1 year')
        : months % 12 == 0
            ? tr('at {n} years', {'n': months ~/ 12})
            : tr('at {n}½ years', {'n': months ~/ 12});

/// The next vitamin A dose, deworming dose, vaccine and monthly clinic visit, soonest
/// first. Something due in the last two weeks is kept and reads as due now. Nothing is
/// returned once the child is five.
List<CareItem> nextCare(DateTime dateOfBirth, {DateTime? today}) {
  final now = today ?? DateTime.now();
  final day = DateTime(now.year, now.month, now.day);
  final dob = DateTime(dateOfBirth.year, dateOfBirth.month, dateOfBirth.day);
  final fifth = _addMonths(dob, 60);
  if (!day.isBefore(fifth)) return [];
  final from = day.subtract(const Duration(days: 14));
  final items = <CareItem>[];

  // Vitamin A: 6, 12, ... 54 months, then 59 months.
  for (final m in [6, 12, 18, 24, 30, 36, 42, 48, 54, 59]) {
    final due = _addMonths(dob, m);
    if (!due.isBefore(from)) {
      items.add(CareItem(tr('Vitamin A'), tr('Given at the clinic {age}', {'age': _age(m)}), due));
      break;
    }
  }
  // Deworming: 12, 18, ... 54 months, then 59 months.
  for (final m in [12, 18, 24, 30, 36, 42, 48, 54, 59]) {
    final due = _addMonths(dob, m);
    if (!due.isBefore(from)) {
      items.add(CareItem(tr('Deworming'), tr('Given at the clinic {age}', {'age': _age(m)}), due));
      break;
    }
  }
  // Vaccines.
  final vaccines = [
    for (final (days, name) in _vaccinesByWeek) (dob.add(Duration(days: days)), name),
    for (final (months, name) in _vaccinesByMonth) (_addMonths(dob, months), name),
  ];
  for (final (due, name) in vaccines) {
    if (!due.isBefore(from)) {
      items.add(CareItem(tr(name), tr('Take the clinic booklet with you'), due));
      break;
    }
  }
  // Monthly clinic visit for weighing: the next month-birthday.
  for (var m = 1; m < 60; m++) {
    final due = _addMonths(dob, m);
    if (!due.isBefore(day)) {
      items.add(CareItem(tr('Clinic visit'), tr('Monthly weighing and growth check'), due));
      break;
    }
  }
  items.sort((a, b) => a.due.compareTo(b.due));
  return items;
}
