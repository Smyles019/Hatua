import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../widgets/sprout.dart';

/// Full-bleed plum splash with bleeding circles, shown while the session restores.
class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      backgroundColor: context.hc.header,
      body: Stack(children: [
        Positioned(top: -80, right: -60, child: _disc(220, context.hc.sun500)),
        Positioned(top: 40, left: -70, child: _disc(150, context.hc.plum500)),
        Positioned(bottom: -90, left: -40, child: _disc(240, context.hc.blush500)),
        Positioned(bottom: -40, right: -50, child: _disc(170, context.hc.sun500)),
        Center(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            const Sprout(pose: SproutPose.waving, size: 140),
            SizedBox(height: 8),
            Text('Hatua',
                style: t.displaySmall?.copyWith(color: context.hc.onHeader, fontSize: 48)),
            SizedBox(height: 8),
            Text('Growing well, step by step',
                style: t.bodyMedium?.copyWith(color: context.hc.onHeader)),
          ]),
        ),
      ]),
    );
  }

  Widget _disc(double size, Color color) => Container(
      width: size, height: size, decoration: BoxDecoration(color: color, shape: BoxShape.circle));
}
