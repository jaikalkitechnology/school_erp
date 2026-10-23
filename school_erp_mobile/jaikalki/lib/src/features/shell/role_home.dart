import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../core/auth_cubit.dart';
import '../../core/push_service.dart';
import '../../core/service_locator.dart';
import '../../core/settings_cubit.dart';
import '../coordinator/coordinator_shell.dart';
import '../notifications/notifications_page.dart';
import '../staff/staff_shell.dart';
import '../student/student_shell.dart';
import '../teacher/teacher_shell.dart';
import 'home_shell.dart';
import 'principal_shell.dart';
import 'transport_shell.dart';

/// Picks the right shell based on the logged-in user's primary role.
///
///   * Parent                       → HomeShell (dashboard, attendance,
///                                     fees, homework, more).
///   * coordinator                  → CoordinatorShell.
///   * class_teacher / subject_teacher → TeacherShell.
///   * transport_manager            → TransportShell — a stripped-down
///                                     2-tab shell with just the Bus
///                                     screen + a More tab. No
///                                     attendance / fees / homework.
///   * transport_manager / bus_staff → TransportShell.
///   * Other staff (accountant, librarian, hostel warden, office staff,
///     receptionist, visitor desk, supervisor, school admin, ...)
///                                  → StaffShell.
///   * Anyone else                  → HomeShell fallback.
class RoleHome extends StatelessWidget {
  const RoleHome({super.key});

  static const _principalRoles = <String>{
    'principal',
    'vice_principal',
    'hod',
    'management',
  };

  static const _teacherRoles = <String>{
    'teacher',
    'class_teacher',
    'subject_teacher',
    'coordinator',
  };

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<AuthCubit, AuthState>(
      builder: (context, state) {
        if (state is! AuthAuthenticated) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        return _OpenNotificationsOnTap(child: _shellFor(state.user.roles.toSet()));
      },
    );
  }

  Widget _shellFor(Set<String> roles) {
    // Parent role wins over any other (parents who also happen to be
    // staff get the parent shell — staff workflows live on the admin
    // web).
    if (roles.contains('parent')) return const HomeShell();
    // Transport-only operators get a dedicated, stripped shell.
    // Checked BEFORE teacher / fallback so a user holding only
    // transport_manager doesn't accidentally fall into the parent
    // shell with empty data.
    if (roles.contains('transport_manager') || roles.contains('bus_staff')) {
      return const TransportShell();
    }
    // Principal / vice_principal get their own dashboard shell —
    // checked BEFORE the teacher shell so a principal who also
    // happens to teach a section still lands on the leadership UI.
    if (roles.any(_principalRoles.contains)) {
      return const PrincipalShell();
    }
    // Coordinators oversee the whole school's day (cover, attendance)
    // and get the teacher tools under More.
    if (roles.contains('coordinator')) return const CoordinatorShell();
    if (roles.any(_teacherRoles.contains)) return const TeacherShell();
    // Students get their own self-service shell (own attendance,
    // homework, results, profile) — never the parent shell, which is
    // built around a child-switcher and "your child" framing.
    if (roles.contains('student')) return const StudentShell();
    // Any other staff role: self-service staff screens instead of the
    // parent screens (which only make sense with linked children).
    if (roles.isNotEmpty) return const StaffShell();
    return const HomeShell();
  }
}

/// Opens the Notifications page when the user taps a push notification —
/// whether the app was open, in the background, or launched by the tap
/// (PushService.openRequests is bumped before this screen exists then,
/// so a request newer than the last one handled is acted on at start).
class _OpenNotificationsOnTap extends StatefulWidget {
  const _OpenNotificationsOnTap({required this.child});

  final Widget child;

  @override
  State<_OpenNotificationsOnTap> createState() => _OpenNotificationsOnTapState();
}

class _OpenNotificationsOnTapState extends State<_OpenNotificationsOnTap> {
  static int _handled = 0;
  final _requests = PushService.instance.openRequests;

  @override
  void initState() {
    super.initState();
    _requests.addListener(_onRequest);
    WidgetsBinding.instance.addPostFrameCallback((_) => _onRequest());
  }

  @override
  void dispose() {
    _requests.removeListener(_onRequest);
    super.dispose();
  }

  void _onRequest() {
    if (!mounted || _requests.value <= _handled) return;
    _handled = _requests.value;
    final title = locator<SettingsCubit>().state.strings.tabNotifications;
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Scaffold(
          appBar: AppBar(title: Text(title)),
          body: const NotificationsPage(),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
