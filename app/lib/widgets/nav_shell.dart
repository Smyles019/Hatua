import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/theme.dart';

class NavTab {
  NavTab(this.label, this.icon, this.builder);
  final String label;
  final IconData icon;
  final WidgetBuilder builder;
}

/// Lilac bottom bar where the selected tab's icon rises into a plum circle that sits in a
/// notch cut out of the bar, and slides to whichever tab is tapped.
/// An optional centre action (a flat plum pill) sits in the middle slot; it opens a screen
/// rather than selecting a tab, so the circle never moves onto it.
/// Every slot has a text label: icons alone are not reliable for low-literacy users.
class NavShell extends StatefulWidget {
  const NavShell({
    super.key,
    required this.tabs,
    this.centreLabel,
    this.centreIcon,
    this.onCentre,
    this.centreBadge,
  }) : assert((centreLabel == null) == (onCentre == null) &&
            (centreIcon == null) == (onCentre == null));

  final List<NavTab> tabs;
  final String? centreLabel;
  final IconData? centreIcon;
  final void Function(BuildContext context)? onCentre;
  final int? centreBadge;

  @override
  State<NavShell> createState() => NavShellState();
}

class NavShellState extends State<NavShell> {
  int index = 0;

  void select(int i) => setState(() => index = i);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: index,
        children: [for (final t in widget.tabs) Builder(builder: t.builder)],
      ),
      bottomNavigationBar: _Bar(
        tabs: widget.tabs,
        index: index,
        onSelect: select,
        centreLabel: widget.centreLabel,
        centreIcon: widget.centreIcon,
        centreBadge: widget.centreBadge,
        onCentre: widget.onCentre == null ? null : () => widget.onCentre!(context),
      ),
    );
  }
}

// Geometry, in logical pixels.
const _lift = 24.0; // how far the circle rises above the bar's top edge
const _barHeight = 68.0;
const _circle = 52.0;
const _circleCentreY = _lift + 4; // circle centre, measured from the top of the widget
const _notchRadius = _circle / 2 + 6; // circle plus the gap that shows the page behind

class _Bar extends StatelessWidget {
  const _Bar({
    required this.tabs,
    required this.index,
    required this.onSelect,
    this.centreLabel,
    this.centreIcon,
    this.onCentre,
    this.centreBadge,
  });

  final List<NavTab> tabs;
  final int index;
  final ValueChanged<int> onSelect;
  final String? centreLabel;
  final IconData? centreIcon;
  final VoidCallback? onCentre;
  final int? centreBadge;

  bool get _hasCentre => onCentre != null;
  int get _slots => tabs.length + (_hasCentre ? 1 : 0);

  /// Slot position of tab [i]: tabs after the middle shift right past the centre action.
  int _slotOf(int i) => _hasCentre && i >= tabs.length ~/ 2 ? i + 1 : i;

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.of(context).padding.bottom;
    return SizedBox(
      height: _lift + _barHeight + bottom,
      child: LayoutBuilder(builder: (context, constraints) {
        final slotWidth = constraints.maxWidth / _slots;
        final targetX = (_slotOf(index) + 0.5) * slotWidth;
        return TweenAnimationBuilder<double>(
          tween: Tween(end: targetX),
          duration: Duration(milliseconds: 380),
          curve: Curves.easeOutCubic,
          builder: (context, x, _) => Stack(clipBehavior: Clip.none, children: [
            Positioned.fill(
                child: CustomPaint(
                    painter: _NotchedBarPainter(x, context.hc.plum100,
                        Theme.of(context).brightness == Brightness.dark
                            ? const Color(0x00000000)
                            : const Color(0x337B3F70)))),
            Positioned(
              top: _lift,
              left: 0,
              right: 0,
              bottom: bottom,
              child: Material(
                type: MaterialType.transparency,
                child: Row(children: [
                  for (var s = 0; s < _slots; s++)
                    Expanded(child: _slot(context, s)),
                ]),
              ),
            ),
            Positioned(
              left: x - _circle / 2,
              top: _circleCentreY - _circle / 2,
              child: IgnorePointer(child: _activeCircle(context)),
            ),
          ]),
        );
      }),
    );
  }

  Widget _slot(BuildContext context, int slot) {
    if (_hasCentre && slot == tabs.length ~/ 2) return _centreAction(context);
    final i = _hasCentre && slot > tabs.length ~/ 2 ? slot - 1 : slot;
    final active = i == index;
    final color = active ? context.hc.plum700 : context.hc.muted;
    return Semantics(
      selected: active,
      button: true,
      label: tabs[i].label,
      excludeSemantics: true,
      child: InkWell(
        onTap: () => onSelect(i),
        child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
          // The active icon is drawn in the raised circle instead.
          AnimatedOpacity(
            opacity: active ? 0 : 1,
            duration: Duration(milliseconds: 200),
            child: Icon(tabs[i].icon, color: color),
          ),
          SizedBox(height: 4),
          _label(context, tabs[i].label, color, active),
          SizedBox(height: 10),
        ]),
      ),
    );
  }

  Widget _label(BuildContext context, String text, Color color, bool bold) => Text(
        text,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
            color: color,
            letterSpacing: 0,
            fontSize: 12,
            fontWeight: bold ? FontWeight.w800 : null),
      );

  Widget _activeCircle(BuildContext context) {
    return Container(
      width: _circle,
      height: _circle,
      decoration: BoxDecoration(
        color: context.hc.plum700,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(color: context.hc.shadow, blurRadius: 10, offset: const Offset(0, 4))
        ],
      ),
      child: AnimatedSwitcher(
        duration: Duration(milliseconds: 250),
        transitionBuilder: (child, animation) =>
            ScaleTransition(scale: animation, child: child),
        child: Icon(tabs[index].icon,
            key: ValueKey(index), color: context.hc.onPrimary, size: 26),
      ),
    );
  }

  Widget _centreAction(BuildContext context) {
    return Semantics(
      button: true,
      label: centreLabel,
      excludeSemantics: true,
      child: InkWell(
        onTap: onCentre,
        child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
          Stack(clipBehavior: Clip.none, children: [
            Container(
              width: 52,
              height: 32,
              decoration: BoxDecoration(
                color: context.hc.plum700,
                borderRadius: BorderRadius.circular(999),
              ),
              child: Icon(centreIcon, color: context.hc.onPrimary, size: 22),
            ),
            if ((centreBadge ?? 0) > 0)
              Positioned(
                right: -10,
                top: -8,
                child: Container(
                  padding: EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                  decoration: BoxDecoration(
                    color: context.hc.riskHigh,
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: context.hc.plum100, width: 2),
                  ),
                  child: Text('$centreBadge',
                      style: TextStyle(
                          color: context.hc.plum900,
                          fontWeight: FontWeight.w700,
                          fontSize: 12)),
                ),
              ),
          ]),
          SizedBox(height: 2),
          _label(context, centreLabel!, context.hc.plum900, false),
          SizedBox(height: 10),
        ]),
      ),
    );
  }
}

/// The bar's lilac shape with a round notch cut out around the active circle.
class _NotchedBarPainter extends CustomPainter {
  _NotchedBarPainter(this.notchX, this.fill, this.shadow);

  final double notchX;
  final Color fill;
  final Color shadow;

  @override
  void paint(Canvas canvas, Size size) {
    const corner = Radius.circular(Radii.xl);
    final bar = Path()
      ..addRRect(RRect.fromRectAndCorners(
        Rect.fromLTWH(0, _lift, size.width, size.height - _lift),
        topLeft: corner,
        topRight: corner,
      ));
    final notch = Path()
      ..addOval(Rect.fromCircle(
          center: Offset(math.max(0, notchX), _circleCentreY), radius: _notchRadius));
    final shape = Path.combine(PathOperation.difference, bar, notch);
    if (shadow.a > 0) canvas.drawShadow(shape, shadow, 6, false);
    canvas.drawPath(shape, Paint()..color = fill);
  }

  @override
  bool shouldRepaint(_NotchedBarPainter old) =>
      old.notchX != notchX || old.fill != fill || old.shadow != shadow;
}
