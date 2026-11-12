import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/models.dart';
import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/child_avatar.dart';
import '../../widgets/common.dart';
import '../../widgets/sprout.dart';
import '../../i18n/strings.dart';

/// Adds a child under five in four short steps: name, birthday and sex, growth (optional),
/// then an animal avatar. A caregiver adds their own; a CHW passes [caregiverId] for a
/// caregiver linked to them.
class AddChildScreen extends StatefulWidget {
  const AddChildScreen({super.key, this.caregiverId, this.caregiverName});
  final String? caregiverId;
  final String? caregiverName;

  @override
  State<AddChildScreen> createState() => _AddChildScreenState();
}

class _AddChildScreenState extends State<AddChildScreen> {
  static const _steps = 4;
  final _forms = List.generate(_steps, (_) => GlobalKey<FormState>());
  final _name = TextEditingController();
  final _dob = TextEditingController();
  final _location = TextEditingController();
  final _weight = TextEditingController();
  final _height = TextEditingController();
  DateTime? _dobValue;
  String? _sex;
  String _avatar = avatarIds.first;
  Set<String> _careFactors = {};
  int _step = 0;
  bool _busy = false;
  Child? _saved; // set once saved: shows the "profile ready" view
  final _fmt = DateFormat('d MMMM yyyy');

  @override
  void dispose() {
    for (final c in [_name, _dob, _location, _weight, _height]) {
      c.dispose();
    }
    super.dispose();
  }

  String get _childName => _name.text.trim().isEmpty ? tr('your child') : _name.text.trim();

  Future<void> _pickDob() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _dobValue ?? DateTime(now.year - 1, now.month, now.day),
      // Under five only: 0 to 59 months.
      firstDate: DateTime(now.year - 5, now.month, now.day + 1),
      lastDate: now,
      helpText: tr("Child's date of birth"),
    );
    if (picked != null) {
      setState(() {
        _dobValue = picked;
        _dob.text = _fmt.format(picked);
      });
    }
  }

  void _next() {
    if (!_forms[_step].currentState!.validate()) return;
    if (_step == 1 && _sex == null) {
      showMessage(context, tr('Please choose girl or boy.'));
      return;
    }
    if (_step < _steps - 1) {
      setState(() => _step++);
    } else {
      _submit();
    }
  }

  void _back() {
    if (_step > 0) {
      setState(() => _step--);
    } else {
      Navigator.of(context).pop();
    }
  }

  double? _num(TextEditingController c) => double.tryParse(c.text.trim().replaceAll(',', '.'));

  Future<void> _submit() async {
    setState(() => _busy = true);
    final session = context.read<Session>();
    try {
      final data = await session.api.post('/children', {
        if (widget.caregiverId != null) 'caregiver_id': widget.caregiverId,
        'first_name': _name.text.trim(),
        'date_of_birth': DateFormat('yyyy-MM-dd').format(_dobValue!),
        'sex': _sex,
        'location': _location.text.trim(),
        'avatar_id': _avatar,
        'care_factors': _careFactors.toList(),
      });
      var child = Child.fromJson(data as Map<String, dynamic>);
      final w = _num(_weight), h = _num(_height);
      if (w != null || h != null) {
        final entry = GrowthEntry(measuredOn: DateTime.now(), weightKg: w, heightCm: h);
        child = Child.fromJson(await session.api
            .post('/children/${child.childId}/growth', entry.toJson()) as Map<String, dynamic>);
      }
      session.dataChanged();
      if (mounted) setState(() => _saved = child);
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _addAnother() {
    for (final c in [_name, _dob, _location, _weight, _height]) {
      c.clear();
    }
    setState(() {
      _dobValue = null;
      _sex = null;
      _avatar = avatarIds.first;
      _careFactors = {};
      _step = 0;
      _saved = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_saved != null) return _ready(context, _saved!);
    final t = Theme.of(context).textTheme;
    final pages = [_nameStep, _aboutStep, _growthStep, _avatarStep];
    return PopScope(
      canPop: _step == 0,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _back();
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(widget.caregiverName == null
              ? tr('Add a child')
              : tr('Add a child for {caregiverName}', {'caregiverName': widget.caregiverName})),
          leading: IconButton(
              tooltip: tr('Back'), icon: const Icon(Icons.arrow_back_rounded), onPressed: _back),
        ),
        body: SafeArea(
          child: Column(children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(Space.s4, Space.s2, Space.s4, 0),
              child: Column(children: [
                Row(children: [
                  Text(tr('STEP {step} OF {steps}', {'step': _step + 1, 'steps': _steps}), style: t.labelMedium),
                  const Spacer(),
                  Text([tr('Name'), tr('About'), tr('Growth'), tr('Avatar')][_step], style: t.bodySmall),
                ]),
                const SizedBox(height: Space.s2),
                ClipRRect(
                  borderRadius: BorderRadius.circular(999),
                  child: LinearProgressIndicator(
                    value: (_step + 1) / _steps,
                    minHeight: 8,
                    backgroundColor: context.hc.plum100,
                    color: context.hc.plum700,
                  ),
                ),
              ]),
            ),
            Expanded(
              child: Form(
                key: _forms[_step],
                child: ListView(
                  padding: const EdgeInsets.all(Space.s4),
                  children: pages[_step](context),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(Space.s4, 0, Space.s4, Space.s4),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                FilledButton(
                  onPressed: _busy ? null : _next,
                  child: Text(_busy
                      ? tr('Saving...')
                      : _step == _steps - 1
                          ? tr('Save profile')
                          : tr('Next')),
                ),
                if (_step == 2)
                  TextButton(
                    onPressed: () {
                      _weight.clear();
                      _height.clear();
                      _careFactors = {};
                      setState(() => _step++);
                    },
                    child: Text(tr('Skip for now')),
                  ),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _title(BuildContext context, String tag, String title, String body) {
    final t = Theme.of(context).textTheme;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _Pill(tag),
      const SizedBox(height: Space.s2),
      Text(title, style: t.headlineSmall),
      const SizedBox(height: Space.s1),
      Text(body, style: t.bodyMedium?.copyWith(color: context.hc.muted)),
      const SizedBox(height: Space.s4),
    ]);
  }

  List<Widget> _nameStep(BuildContext context) => [
        _title(context, tr('New sprout'), tr("What is your child's name?"),
            tr('We use it to make the questions and results feel personal.')),
        LabeledField(
          label: tr("Child's first name"),
          controller: _name,
          hint: tr('Wanjiru'),
          icon: Icons.child_care_rounded,
          textInputAction: TextInputAction.done,
          validator: (v) => requiredField(v, tr("the child's name")),
        ),
        const SizedBox(height: Space.s4),
        _TipCard(
          title: tr('Did you know?'),
          body: tr('Hearing their own name often helps babies learn to turn and respond when someone calls them.'),
        ),
      ];

  List<Widget> _aboutStep(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return [
      _title(context, tr('About {_childName}', {'_childName': _childName}), tr('Tell us a bit more about {_childName}', {'_childName': _childName}),
          tr('Age decides which questions we ask at each check.')),
      LabeledField(
        label: tr('Date of birth'),
        controller: _dob,
        hint: tr('Choose a date'),
        icon: Icons.calendar_today_rounded,
        readOnly: true,
        onTap: _pickDob,
        validator: (_) => _dobValue == null ? tr('Please choose the date of birth') : null,
      ),
      const SizedBox(height: Space.s4),
      Text(tr('SEX'), style: t.labelMedium),
      const SizedBox(height: Space.s1),
      Row(children: [
        Expanded(
          child: ChoiceOption(
              label: tr('Girl'),
              selected: _sex == 'female',
              onTap: () => setState(() => _sex = 'female')),
        ),
        const SizedBox(width: Space.s3),
        Expanded(
          child: ChoiceOption(
              label: tr('Boy'), selected: _sex == 'male', onTap: () => setState(() => _sex = 'male')),
        ),
      ]),
      const SizedBox(height: Space.s4),
      LabeledField(
        label: tr('Where you live'),
        controller: _location,
        hint: tr('Village, estate or ward'),
        icon: Icons.place_outlined,
        textInputAction: TextInputAction.done,
        validator: (v) => requiredField(v, tr('where you live')),
      ),
    ];
  }

  List<Widget> _growthStep(BuildContext context) {
    String? range(String? v, double lo, double hi, String what) {
      if (v == null || v.trim().isEmpty) return null; // optional
      final n = double.tryParse(v.trim().replaceAll(',', '.'));
      return (n == null || n < lo || n > hi) ? tr('Enter {what} between {lo} and {hi}', {'what': what, 'lo': lo, 'hi': hi}) : null;
    }

    return [
      _title(context, tr('Growth'), "$_childName's weight and height",
          tr('Copy them from the Mother and Child Health booklet after a clinic visit. You can skip this and add them later.')),
      LabeledField(
        label: tr('Weight (kg)'),
        controller: _weight,
        hint: tr('For example 9.4'),
        icon: Icons.monitor_weight_outlined,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        validator: (v) => range(v, 1, 35, tr('a weight')),
      ),
      const SizedBox(height: Space.s3),
      LabeledField(
        label: tr('Height or length (cm)'),
        controller: _height,
        hint: tr('For example 76'),
        icon: Icons.straighten_rounded,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        textInputAction: TextInputAction.done,
        validator: (v) => range(v, 40, 130, tr('a height')),
      ),
      const SizedBox(height: Space.s6),
      // Reasons for special care, as ticked in the Mother and Child Health booklet.
      Text(tr('DOES ANY OF THIS APPLY TO {name}?', {'name': _childName.toUpperCase()}),
          style: Theme.of(context).textTheme.labelMedium),
      const SizedBox(height: Space.s1),
      Text(tr('Tick any that apply. Your health worker sees them; it is fine to leave all blank.'),
          style: Theme.of(context).textTheme.bodySmall),
      const SizedBox(height: Space.s2),
      CareFactorChecks(
          selected: _careFactors,
          onChanged: (f) => setState(() => _careFactors = f)),
      const SizedBox(height: Space.s4),
      _TipCard(
        title: tr('Why we ask'),
        body: tr('Growth and development go together. Regular entries build a growth record you can show at the clinic.'),
      ),
    ];
  }

  List<Widget> _avatarStep(BuildContext context) => [
        _title(context, tr('Almost done'), tr('Pick an animal for {_childName}', {'_childName': _childName}),
            tr('It shows wherever {_childName} appears in the app. We never ask for photos of children.', {'_childName': _childName})),
        Center(child: AnimalAvatar(_avatar, size: 112)),
        const SizedBox(height: Space.s6),
        AvatarPicker(selected: _avatar, onPick: (id) => setState(() => _avatar = id)),
      ];

  Widget _ready(BuildContext context, Child child) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      body: SafeArea(
        child: ListView(padding: const EdgeInsets.all(Space.s4), children: [
          const SizedBox(height: Space.s6),
          Center(child: _Pill(tr('Profile created'))),
          const SizedBox(height: Space.s4),
          HatuaCard(
            padding: const EdgeInsets.all(Space.s6),
            child: Column(children: [
              ChildAvatar(childId: child.childId, avatarId: child.avatarId, size: 112, ring: true),
              const SizedBox(height: Space.s3),
              _Pill(ageLabel(child.ageMonths)),
              const SizedBox(height: Space.s3),
              Text(tr("{firstName}'s profile is ready!", {'firstName': child.firstName}),
                  style: t.headlineSmall, textAlign: TextAlign.center),
              const SizedBox(height: Space.s2),
              Text(
                tr("The questions at each check will match {firstName}'s age.", {'firstName': child.firstName}),
                style: t.bodyMedium?.copyWith(color: context.hc.muted),
                textAlign: TextAlign.center,
              ),
            ]),
          ),
          const SizedBox(height: Space.s4),
          HatuaCard(
            color: context.hc.plum100,
            child: Row(children: [
              const Sprout(pose: SproutPose.cheering, size: 56, bob: false),
              const SizedBox(width: Space.s3),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(tr('Do you have another child to track?'), style: t.titleMedium),
                  const SizedBox(height: Space.s1),
                  Text(tr('Add every child under five to follow them separately.'),
                      style: t.bodySmall),
                ]),
              ),
            ]),
          ),
          const SizedBox(height: Space.s6),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(tr('Continue to home')),
          ),
          const SizedBox(height: Space.s2),
          FilledButton.icon(
            style: secondaryButtonStyle(context),
            onPressed: _addAnother,
            icon: const Icon(Icons.add_rounded),
            label: Text(tr('Add another child')),
          ),
        ]),
      ),
    );
  }
}

/// Small sun-coloured tag above a step title.
class _Pill extends StatelessWidget {
  const _Pill(this.text);
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: Space.s3, vertical: Space.s1),
      decoration: BoxDecoration(
          color: context.hc.sun100, borderRadius: BorderRadius.circular(999)),
      child: Text(text,
          style: Theme.of(context).textTheme.labelMedium?.copyWith(color: context.hc.plum900)),
    );
  }
}

class _TipCard extends StatelessWidget {
  const _TipCard({required this.title, required this.body});
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return HatuaCard(
      color: context.hc.sun100,
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(Icons.lightbulb_outline_rounded, color: context.hc.plum900),
        const SizedBox(width: Space.s3),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: t.labelLarge?.copyWith(color: context.hc.plum900)),
            const SizedBox(height: Space.s1),
            Text(body, style: t.bodySmall?.copyWith(color: context.hc.plum900)),
          ]),
        ),
      ]),
    );
  }
}
