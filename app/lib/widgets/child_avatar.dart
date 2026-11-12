import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../theme/colors.dart';
import '../theme/theme.dart';

/// The animal avatars in assets/avatars. A child gets one instead of a photo, so the
/// app never stores pictures of children.
const avatarIds = [
  'lion', 'elephant', 'giraffe', 'zebra', 'hippo', 'monkey', 'cheetah', 'rhino',
];

const avatarNames = {
  'lion': 'Lion', 'elephant': 'Elephant', 'giraffe': 'Giraffe', 'zebra': 'Zebra',
  'hippo': 'Hippo', 'monkey': 'Monkey', 'cheetah': 'Cheetah', 'rhino': 'Rhino',
};

/// Default avatar when none was picked: stable for a child, so it never changes.
String defaultAvatar(String childId) =>
    avatarIds[childId.codeUnits.fold<int>(0, (a, b) => a + b) % avatarIds.length];

class AnimalAvatar extends StatelessWidget {
  const AnimalAvatar(this.avatarId, {super.key, this.size = 44, this.ring = false});
  final String avatarId;
  final double size;
  final bool ring;

  @override
  Widget build(BuildContext context) {
    // Round everywhere a child appears (home chips, lists, profile, picker).
    final img = ClipOval(
      child: SvgPicture.asset('assets/avatars/$avatarId.svg',
          width: size, height: size, excludeFromSemantics: true),
    );
    if (!ring) return img;
    return Container(
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: context.hc.plum700, width: 2.5),
      ),
      child: img,
    );
  }
}

/// A child's chosen animal (from the API), or their default one.
class ChildAvatar extends StatelessWidget {
  const ChildAvatar(
      {super.key, required this.childId, this.avatarId, this.size = 44, this.ring = false});
  final String childId;
  final String? avatarId;
  final double size;
  final bool ring;

  @override
  Widget build(BuildContext context) {
    final id = avatarIds.contains(avatarId) ? avatarId! : defaultAvatar(childId);
    return AnimalAvatar(id, size: size, ring: ring);
  }
}

/// Grid of animals to choose from.
class AvatarPicker extends StatelessWidget {
  const AvatarPicker({super.key, required this.selected, required this.onPick});
  final String? selected;
  final ValueChanged<String> onPick;

  @override
  Widget build(BuildContext context) {
    // Pictures only: the animal names are not shown, but stay as screen-reader labels.
    return GridView.count(
      crossAxisCount: 4,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: Space.s3,
      crossAxisSpacing: Space.s3,
      children: [
        for (final id in avatarIds)
          Semantics(
            button: true,
            selected: selected == id,
            label: avatarNames[id],
            child: InkWell(
              customBorder: const CircleBorder(),
              onTap: () => onPick(id),
              child: Center(
                child: Stack(clipBehavior: Clip.none, children: [
                  AnimalAvatar(id, size: 64, ring: selected == id),
                  if (selected == id)
                    Positioned(
                      right: -4,
                      top: -4,
                      child: Container(
                        width: 22,
                        height: 22,
                        decoration: BoxDecoration(
                            color: context.hc.plum700, shape: BoxShape.circle),
                        child: Icon(Icons.check_rounded, size: 16, color: context.hc.onPrimary),
                      ),
                    ),
                ]),
              ),
            ),
          ),
      ],
    );
  }
}
