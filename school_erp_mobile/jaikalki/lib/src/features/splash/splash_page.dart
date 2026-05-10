import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth_cubit.dart';
import '../../core/service_locator.dart';
import '../../core/settings_cubit.dart';
import '../../theme/brand.dart';

class SplashPage extends StatefulWidget {
  const SplashPage({super.key});

  @override
  State<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends State<SplashPage> {
  @override
  void initState() {
    super.initState();
    _route();
  }

  Future<void> _route() async {
    await Future<void>.delayed(const Duration(milliseconds: 350));
    if (!mounted) return;
    final settings = locator<SettingsCubit>().state;
    if (!settings.onboarded) {
      context.go('/onboarding');
      return;
    }
    final auth = locator<AuthCubit>().state;
    context.go(auth is AuthAuthenticated ? '/home' : '/login');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: JaikalkiBrand.saffron,
      body: BlocBuilder<SettingsCubit, SettingsState>(
        builder: (context, state) {
          final t = Theme.of(context).textTheme;
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  height: 96,
                  width: 96,
                  decoration: const BoxDecoration(
                    color: JaikalkiBrand.warmWhite,
                    shape: BoxShape.circle,
                  ),
                  alignment: Alignment.center,
                  child: const Text(
                    'J',
                    style: TextStyle(
                      color: JaikalkiBrand.saffronDark,
                      fontSize: 56,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                Text(
                  'Jaikalki',
                  style: t.displayMedium?.copyWith(
                    color: JaikalkiBrand.warmWhite,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  state.strings.appTagline,
                  style: t.bodyMedium?.copyWith(color: JaikalkiBrand.marigoldPale),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
