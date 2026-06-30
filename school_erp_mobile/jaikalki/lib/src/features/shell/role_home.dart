import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../core/auth_cubit.dart';
import '../teacher/teacher_shell.dart';
import 'home_shell.dart';
import 'principal_shell.dart';
import 'transport_shell.dart';

/// Picks the right shell based on the logged-in user's primary role.
///
///   * Parent                       → HomeShell (dashboard, attendance,
///                                     fees, homework, more).
///   * Teacher-shaped roles
///     (class_teacher / subject_teacher / coordinator / vice_principal /
///     principal)                   → TeacherShell.
///   * transport_manager            → TransportShell — a stripped-down
///                                     2-tab shell with just the Bus
///                                     screen + a More tab. No
///                                     attendance / fees / homework.
///   * Anyone else (eg. accountant) → HomeShell fallback.
class RoleHome extends StatelessWidget {
  const RoleHome({super.key});

  // Senior leadership roles all land on the same Principal dashboard
  // shell. `management` is the trust / society tier; `hod` is the
  // department head — both want the school-wide rollup view rather
  // than the per-class teacher UI.
  static const _principalRoles = <String>{
    'management',
    'principal',
    'vice_principal',
    'hod',
  };

  static const _teacherRoles = <String>{
    'class_teacher',
    'subject_teacher',
    'coordinator',
    'teacher', // generic Teacher code from the Phase 27 org chart
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
        final roles = state.user.roles.toSet();
        // Parent role wins over any other (parents who also happen to be
        // staff get the parent shell — staff workflows live on the admin
        // web).
        if (roles.contains('parent')) return const HomeShell();
        // Transport-only operators get a dedicated, stripped shell.
        // Checked BEFORE teacher / fallback so a user holding only
        // transport_manager doesn't accidentally fall into the parent
        // shell with empty data.
        if (roles.contains('transport_manager')) {
          return const TransportShell();
        }
        // Principal / vice_principal get their own dashboard shell —
        // checked BEFORE the teacher shell so a principal who also
        // happens to teach a section still lands on the leadership UI.
        if (roles.any(_principalRoles.contains)) {
          return const PrincipalShell();
        }
        if (roles.any(_teacherRoles.contains)) return const TeacherShell();
        return const HomeShell();
      },
    );
  }
}
