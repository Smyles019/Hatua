import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../state/session.dart';
import '../../theme/colors.dart';
import '../../theme/theme.dart';
import '../../widgets/sprout.dart';
import 'sign_up_screen.dart';

/// Three short welcome pages, shown once on first launch.
class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  final _pages = PageController();
  int _page = 0;

  @override
  void dispose() {
    _pages.dispose();
    super.dispose();
  }

  void _next() => _pages.nextPage(
      duration: const Duration(milliseconds: 320), curve: Curves.easeOutCubic);

  /// Marks the welcome as seen. The sign-in screen replaces this one underneath.
  Future<void> _finish({bool signUp = false}) async {
    final nav = Navigator.of(context);
    await context.read<Session>().finishWelcome();
    if (signUp) nav.push(MaterialPageRoute(builder: (_) => const SignUpScreen()));
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final c = context.hc;
    final last = _page == 2;
    return Scaffold(
      body: SafeArea(
        child: Column(children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(Space.s4, Space.s2, Space.s2, 0),
            child: Row(children: [
              Text('Hatua', style: t.titleLarge?.copyWith(color: c.plum700)),
              const Spacer(),
              if (!last) TextButton(onPressed: _finish, child: const Text('Skip')),
            ]),
          ),
          Expanded(
            child: PageView(
              controller: _pages,
              onPageChanged: (i) => setState(() => _page = i),
              children: [
                _Page(
                  art: _Blob(child: const Sprout(pose: SproutPose.waving, size: 180)),
                  title: 'Welcome to Hatua',
                  body: 'Check how your child is growing, one small step at a time.',
                ),
                _Page(
                  art: _Blob(
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const Sprout(pose: SproutPose.thinking, size: 120),
                      const SizedBox(width: Space.s2),
                      _AnswerCard(),
                    ]),
                  ),
                  title: 'Answer a few simple questions',
                  body: 'Short questions about what your child can do. It takes about 5 minutes.',
                ),
                _Page(
                  art: _Blob(
                    child: Column(mainAxisSize: MainAxisSize.min, children: [
                      const Sprout(pose: SproutPose.cheering, size: 130),
                      _MiniPath(),
                    ]),
                  ),
                  title: "See your child's journey",
                  body: 'Get things to try at home, and a health worker follows up if needed.',
                ),
              ],
            ),
          ),
          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            for (var i = 0; i < 3; i++)
              AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                margin: const EdgeInsets.symmetric(horizontal: 4),
                width: i == _page ? 22 : 8,
                height: 8,
                decoration: BoxDecoration(
                  color: i == _page ? c.plum700 : c.plum200,
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
          ]),
          Padding(
            padding: const EdgeInsets.all(Space.s4),
            child: Column(children: [
              FilledButton(
                onPressed: last ? () => _finish(signUp: true) : _next,
                child: Text(last ? 'Get started' : 'Next'),
              ),
              // Same height on every page so the button does not jump.
              SizedBox(
                height: Space.touch,
                child: last
                    ? TextButton(
                        onPressed: _finish, child: const Text('I already have an account'))
                    : null,
              ),
            ]),
          ),
        ]),
      ),
    );
  }
}

class _Page extends StatelessWidget {
  const _Page({required this.art, required this.title, required this.body});
  final Widget art;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Space.s6),
      child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        art,
        const SizedBox(height: Space.s8),
        Text(title, style: t.headlineSmall, textAlign: TextAlign.center),
        const SizedBox(height: Space.s2),
        Text(body, style: t.bodyLarge, textAlign: TextAlign.center),
      ]),
    );
  }
}

/// Soft round backdrop behind the illustrations.
class _Blob extends StatelessWidget {
  const _Blob({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 280,
      height: 260,
      alignment: Alignment.center,
      decoration: BoxDecoration(color: context.hc.plum100, shape: BoxShape.circle),
      child: child,
    );
  }
}

class _AnswerCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final c = context.hc;
    final t = Theme.of(context).textTheme;
    Widget option(String label, bool on) => Container(
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: on ? c.plum100 : c.surfaceCard,
            borderRadius: BorderRadius.circular(Radii.sm),
            border: Border.all(color: on ? c.plum700 : c.plum200, width: 1.5),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Container(
              width: 12,
              height: 12,
              decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: c.plum700, width: on ? 4 : 1.5)),
            ),
            const SizedBox(width: 6),
            Text(label, style: t.bodySmall?.copyWith(color: c.plum900)),
          ]),
        );
    return Container(
      padding: const EdgeInsets.all(Space.s2),
      decoration: BoxDecoration(
          color: c.surfaceCard, borderRadius: BorderRadius.circular(Radii.md)),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start,
          children: [option('Yes', true), option('No', false), option("Don't know", false)]),
    );
  }
}

class _MiniPath extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final c = context.hc;
    Widget stone(Color fill, {Color? border, IconData? icon}) => Container(
          width: 26,
          height: 26,
          decoration: BoxDecoration(
            color: fill,
            shape: BoxShape.circle,
            border: border == null ? null : Border.all(color: border, width: 2.5),
          ),
          child: icon == null ? null : Icon(icon, size: 15, color: c.onPrimary),
        );
    Widget link() => Container(width: 18, height: 6, color: c.plum200);
    return Row(mainAxisSize: MainAxisSize.min, children: [
      stone(c.plum700, icon: Icons.check_rounded),
      link(),
      stone(c.plum700, icon: Icons.check_rounded),
      link(),
      stone(c.sun500, border: c.plum700),
      link(),
      stone(c.surfaceCard, border: c.plum200),
    ]);
  }
}
