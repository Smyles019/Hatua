import 'package:flutter/material.dart';

import '../state/session.dart';
import 'caregiver/child_profile_screen.dart';
import 'chw/flagged_screen.dart';
import 'messages/thread_screen.dart';

/// Opens the screen a tapped notification is about. The data comes from the backend
/// (app/services/notify.py): type, id, and for some types child_id or name. A
/// notification meant for another role (an old one, after someone else signed in on
/// this phone) opens nothing.
void openFromNotification(NavigatorState nav, Session session, Map<String, dynamic> data) {
  final role = session.user?.role;
  final id = data['id']?.toString();
  Widget? screen;
  switch (data['type']) {
    case 'case' when role == 'chw':
      screen = const FlaggedScreen();
    case 'thread' when role == 'chw' && id != null:
      screen = ThreadScreen(caregiverId: id, caregiverName: data['name']?.toString() ?? '');
    case 'ask' when role == 'caregiver':
      screen = const ThreadScreen();
    case 'result' when role == 'caregiver':
      final child = data['child_id']?.toString();
      if (child != null) screen = ChildProfileScreen(childId: child);
    case 'child' when role == 'caregiver' && id != null:
      screen = ChildProfileScreen(childId: id);
  }
  if (screen != null) {
    nav.push(MaterialPageRoute(builder: (_) => screen!));
  }
}
