import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth_cubit.dart';
import '../../theme/brand.dart';

/// For logins whose work is only on a website (the platform super admin):
/// says where to go instead of showing school screens that would all fail.
class WebOnlyPage extends StatelessWidget {
  const WebOnlyPage({super.key, required this.roleName});

  final String roleName;

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
                Text('Use the $roleName website', style: t.headlineSmall, textAlign: TextAlign.center),
                const SizedBox(height: 12),
                Text(
                  'The $roleName tools are on the web. Sign in to the $roleName website on a computer.',
                  style: t.bodyLarge,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                Text(
                  'This app is for school staff, parents and students.',
                  style: t.bodyMedium,
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
