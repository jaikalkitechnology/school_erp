import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../core/auth_cubit.dart';
import '../teacher/teacher_shell.dart';
import 'home_shell.dart';

/// Picks the right shell based on the logged-in user's primary role.
///
/// Parent → HomeShell (the existing parent app surface).
/// Teacher-shaped roles (class_teacher / subject_teacher / coordinator /
/// vice_principal / principal) → TeacherShell.
///
/// Anyone else (eg. accountant who only ever uses the admin web) sees
/// the HomeShell too as a safe fallback — it'll just have empty data.
class RoleHome extends StatelessWidget {
  const RoleHome({super.key});

  static const _teacherRoles = <String>{
    'class_teacher',
    'subject_teacher',
    'coordinator',
    'vice_principal',
    'principal',
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
        final isTeacher = roles.any(_teacherRoles.contains);
        // Parent role wins if present (parents who also happen to be
        // staff would get the parent shell — the staff features are on
        // the admin web).
        if (roles.contains('parent')) return const HomeShell();
        if (isTeacher) return const TeacherShell();
        return const HomeShell();
      },
    );
  }
}
