import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth_cubit.dart';
import '../../theme/brand.dart';

/// For logins whose work is only on a website — the platform super admin,
/// and front-office roles (receptionist, visitor desk, area supervisor)
/// whose dashboard is the school admin website: says where to go instead
/// of showing app screens that aren't meant for them.
class WebOnlyPage extends StatelessWidget {
  const WebOnlyPage({super.key, required this.roleName, required this.websiteName});

  /// eg. "Receptionist".
  final String roleName;

  /// eg. "school admin" / "Super Admin".
  final String websiteName;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return BlocListener<AuthCubit, AuthState>(
      listenWhen: (a, b) => b is AuthInitial && a is AuthAuthenticated,
      listener: (context, state) {
        if (state is AuthInitial) context.go('/login');
      },
      child: Scaffold(
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Icon(Icons.desktop_windows_outlined, size: 56, color: JaikalkiBrand.saffron),
                const SizedBox(height: 20),
                Text('Use the $websiteName website', style: t.headlineSmall, textAlign: TextAlign.center),
                const SizedBox(height: 12),
                Text(
                  'Your work as $roleName is on the $websiteName website. Sign in there on a computer.',
                  style: t.bodyLarge,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 32),
                OutlinedButton.icon(
                  icon: const Icon(Icons.logout),
                  label: const Text('Sign out'),
                  onPressed: () => context.read<AuthCubit>().logout(),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
