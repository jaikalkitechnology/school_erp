import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth_cubit.dart';
import '../../core/service_locator.dart';
import '../../core/settings_cubit.dart';
import '../dashboard/dashboard_page.dart';
import '../notifications/notifications_page.dart';
import '../settings/settings_page.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<SettingsCubit, SettingsState>(
      builder: (context, settings) {
        final s = settings.strings;
        final pages = const [
          DashboardPage(),
          NotificationsPage(),
          SettingsPage(),
        ];
        return BlocListener<AuthCubit, AuthState>(
          listenWhen: (prev, curr) => curr is AuthInitial && prev is AuthAuthenticated,
          listener: (context, state) {
            if (state is AuthInitial) context.go('/login');
          },
          child: Scaffold(
            appBar: _index == 0
                ? null
                : AppBar(
                    title: Text(_index == 1 ? s.tabNotifications : s.tabSettings),
                  ),
            body: IndexedStack(index: _index, children: pages),
            bottomNavigationBar: NavigationBar(
              selectedIndex: _index,
              onDestinationSelected: (i) => setState(() => _index = i),
              destinations: [
                NavigationDestination(
                  icon: const Icon(Icons.home_outlined),
                  selectedIcon: const Icon(Icons.home_rounded),
                  label: s.tabHome,
                ),
                NavigationDestination(
                  icon: const Icon(Icons.notifications_outlined),
                  selectedIcon: const Icon(Icons.notifications_rounded),
                  label: s.tabNotifications,
                ),
                NavigationDestination(
                  icon: const Icon(Icons.settings_outlined),
                  selectedIcon: const Icon(Icons.settings_rounded),
                  label: s.tabSettings,
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
