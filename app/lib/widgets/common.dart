import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../theme/colors.dart';
import '../theme/theme.dart';
import 'sprout.dart';

/// Plum header with a rounded bottom edge and circles bleeding off the edges.
/// Used only on entry screens (splash, sign in, sign up, home dashboards).
class BlobHeader extends StatelessWidget {
  const BlobHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.height = 220,
    this.variant = 0,
    this.trailing,
  });

  final String title;
  final String? subtitle;
  final double height;
  final int variant; // changes the circle arrangement between screens
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final top = MediaQuery.of(context).padding.top;
    final circles = variant.isEven
        ? [
            _Circle(140, right: -40, top: -50, color: context.hc.sun500),
            _Circle(110, left: -45, top: -35, color: context.hc.plum500),
            _Circle(70, right: 60, bottom: -30, color: context.hc.blush500),
          ]
        : [
            _Circle(120, right: -30, bottom: -50, color: context.hc.sun500),
            _Circle(110, left: -45, top: -35, color: context.hc.blush500),
          ];
    return Container(
      height: height + top,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: context.hc.header,
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(Radii.xl)),
      ),
      child: Stack(children: [
        ...circles,
        if (trailing != null) Positioned(top: top + 8, right: 8, child: trailing!),
        Positioned(
          left: Space.s4,
          right: Space.s4,
          bottom: Space.s6,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title,
                style: t.displaySmall?.copyWith(color: context.hc.onHeader),
                maxLines: 2),
            if (subtitle != null) ...[
              SizedBox(height: Space.s1),
              Text(subtitle!, style: t.bodyMedium?.copyWith(color: context.hc.onHeader)),
            ],
          ]),
        ),
      ]),
    );
  }
}

class _Circle extends StatelessWidget {
  const _Circle(this.size, {this.left, this.right, this.top, this.bottom, required this.color});
  final double size;
  final double? left, right, top, bottom;
  final Color color;

  @override
  Widget build(BuildContext context) => Positioned(
        left: left,
        right: right,
        top: top,
        bottom: bottom,
        child: Container(
            width: size,
            height: size,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
      );
}

/// White card with the Hatua radius and shadow.
class HatuaCard extends StatelessWidget {
  const HatuaCard({super.key, required this.child, this.color, this.onTap, this.padding});
  final Widget child;
  final Color? color;
  final VoidCallback? onTap;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    final radius = BorderRadius.circular(Radii.lg);
    return Container(
      decoration: BoxDecoration(
          color: color ?? context.hc.surfaceCard, borderRadius: radius, boxShadow: cardShadowOf(context)),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: radius,
          onTap: onTap,
          child: Padding(padding: padding ?? EdgeInsets.all(Space.s4), child: child),
        ),
      ),
    );
  }
}

/// Text field with its label always visible above it (never a placeholder label).
class LabeledField extends StatelessWidget {
  const LabeledField({
    super.key,
    required this.label,
    required this.controller,
    this.hint,
    this.icon,
    this.keyboardType,
    this.obscure = false,
    this.validator,
    this.textInputAction = TextInputAction.next,
    this.readOnly = false,
    this.onTap,
  });

  final String label;
  final TextEditingController controller;
  final String? hint;
  final IconData? icon;
  final TextInputType? keyboardType;
  final bool obscure;
  final String? Function(String?)? validator;
  final TextInputAction textInputAction;
  final bool readOnly;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(label.toUpperCase(), style: Theme.of(context).textTheme.labelMedium),
      SizedBox(height: Space.s1),
      TextFormField(
        controller: controller,
        keyboardType: keyboardType,
        obscureText: obscure,
        validator: validator,
        textInputAction: textInputAction,
        readOnly: readOnly,
        onTap: onTap,
        style: Theme.of(context).textTheme.bodyMedium,
        decoration: InputDecoration(
          hintText: hint,
          prefixIcon: icon == null ? null : Icon(icon),
        ),
      ),
    ]);
  }
}

/// Large selectable choice, used for answers, sex and CHW outcomes.
class ChoiceOption extends StatelessWidget {
  const ChoiceOption({
    super.key,
    required this.label,
    required this.selected,
    required this.onTap,
    this.subtitle,
  });

  final String label;
  final String? subtitle;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Semantics(
      selected: selected,
      button: true,
      child: Material(
        color: selected ? context.hc.plum100 : context.hc.surfaceCard,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(Radii.md),
          side: BorderSide(
              color: selected ? context.hc.plum700 : context.hc.plum200, width: 2),
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(Radii.md),
          onTap: onTap,
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: 56),
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: Space.s4, vertical: Space.s3),
              child: Row(children: [
                Container(
                  width: 22,
                  height: 22,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: context.hc.plum700, width: selected ? 7 : 2),
                  ),
                ),
                SizedBox(width: Space.s3),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(label, style: t.labelLarge),
                    if (subtitle != null) Text(subtitle!, style: t.bodySmall),
                  ]),
                ),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}

/// Loads [future] and shows a spinner, a readable error with a retry button, or [builder].
class AsyncView<T> extends StatelessWidget {
  const AsyncView({super.key, required this.future, required this.builder, this.onRetry});
  final Future<T> future;
  final Widget Function(BuildContext, T) builder;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<T>(
      future: future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return Center(
              child: Padding(
                  padding: EdgeInsets.all(Space.s8),
                  child: CircularProgressIndicator(color: context.hc.plum700)));
        }
        if (snap.hasError) {
          return ErrorPanel(message: '${snap.error}', onRetry: onRetry);
        }
        return builder(context, snap.data as T);
      },
    );
  }
}

class ErrorPanel extends StatelessWidget {
  const ErrorPanel({super.key, required this.message, this.onRetry});
  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(Space.s6),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.cloud_off_rounded, size: 40, color: context.hc.plum900),
          SizedBox(height: Space.s3),
          Text(message,
              textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyMedium),
          if (onRetry != null) ...[
            SizedBox(height: Space.s4),
            OutlinedButton(onPressed: onRetry, child: Text('Try again')),
          ],
        ]),
      ),
    );
  }
}

class EmptyPanel extends StatelessWidget {
  const EmptyPanel({super.key, required this.title, required this.message, this.icon});
  final String title;
  final String message;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Padding(
      padding: EdgeInsets.all(Space.s6),
      child: Column(children: [
        // Sprout resting stands in for an icon on every empty state.
        const Sprout(pose: SproutPose.resting, size: 96),
        SizedBox(height: Space.s3),
        Text(title, style: t.titleMedium, textAlign: TextAlign.center),
        SizedBox(height: Space.s1),
        Text(message, style: t.bodyMedium, textAlign: TextAlign.center),
      ]),
    );
  }
}

/// Round initial avatar for a child or user.
class InitialAvatar extends StatelessWidget {
  const InitialAvatar(this.name, {super.key, this.size = 44, this.color});
  final String name;
  final double size;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: color ?? context.hc.sun500, shape: BoxShape.circle),
      child: Text(name.isEmpty ? '?' : name[0].toUpperCase(),
          style: Theme.of(context).textTheme.titleLarge?.copyWith(color: context.hc.onBright)),
    );
  }
}

/// Shows an API error (or any error) as a snackbar.
void showError(BuildContext context, Object error) {
  final msg = error is ApiException ? error.message : 'Something went wrong. Please try again.';
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(msg)));
}

void showMessage(BuildContext context, String msg) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(msg)));
}

/// Plain-language age: "8 months", "2 years 3 months".
String ageLabel(int months) {
  if (months < 24) return '$months month${months == 1 ? '' : 's'}';
  final y = months ~/ 12, m = months % 12;
  return m == 0 ? '$y years' : '$y years $m month${m == 1 ? '' : 's'}';
}

String? requiredField(String? v, String what) =>
    (v == null || v.trim().isEmpty) ? 'Please enter $what' : null;

/// Accepts the same formats as the backend (07.., 01.., 2547.., +2547..).
String? phoneValidator(String? v) {
  final d = (v ?? '').replaceAll(RegExp(r'[\s-]'), '');
  return RegExp(r'^(?:\+?254|0)[17]\d{8}$').hasMatch(d)
      ? null
      : 'Enter a Kenyan mobile number, for example 0712 345 678';
}

String? passwordValidator(String? v) =>
    (v == null || v.length < 6) ? 'Use at least 6 characters' : null;
