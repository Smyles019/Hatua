import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/session.dart';
import '../theme/colors.dart';
import '../theme/theme.dart';

/// On a wide screen (a laptop browser) the caregiver and CHW screens keep their phone
/// layout in a centred column, so cards and buttons never stretch across the window.
/// Admin screens get a wider column for tables. On a phone this does nothing.
class WebFrame extends StatelessWidget {
  const WebFrame({super.key, required this.child});
  final Widget child;

  static const phoneWidth = 480.0;
  static const adminWidth = 1200.0;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final admin = context.select<Session, bool>((s) => s.user?.role == 'admin');
    final max = admin ? adminWidth : phoneWidth;
    if (width <= max + Space.s8) return child;

    return ColoredBox(
      color: context.hc.plum100,
      child: Center(
        child: Container(
          width: max,
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            color: context.hc.surfacePage,
            boxShadow: cardShadowOf(context),
          ),
          // Children read the column's width, not the window's.
          child: MediaQuery(
            data:
                MediaQuery.of(context).copyWith(size: Size(max, MediaQuery.sizeOf(context).height)),
            child: child,
          ),
        ),
      ),
    );
  }
}
