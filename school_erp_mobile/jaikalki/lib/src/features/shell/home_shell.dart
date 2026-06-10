import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth_cubit.dart';
import '../../core/settings_cubit.dart';
import '../attendance/attendance_page.dart';
import '../dashboard/dashboard_page.dart';
import '../fees/fees_page.dart';
import '../homework/homework_page.dart';
import 'more_page.dart';

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
        // IndexedStack keeps every tab alive so child-switcher + scroll
        // state survives jumps. Notifications + Settings live behind the
        // "More" tab to keep the bottom nav at 5 max.
        const pages = [
          DashboardPage(),
          AttendancePage(),
          FeesPage(),
          HomeworkPage(),
          MorePage(),
        ];
        return BlocListener<AuthCubit, AuthState>(
          listenWhen: (prev, curr) => curr is AuthInitial && prev is AuthAuthenticated,
          listener: (context, state) {
            if (state is AuthInitial) context.go('/login');
          },
          child: Scaffold(
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
                  icon: const Icon(Icons.event_available_outlined),
                  selectedIcon: const Icon(Icons.event_available_rounded),
                  label: s.tabAttendance,
                ),
                NavigationDestination(
                  icon: const Icon(Icons.payments_outlined),
                  selectedIcon: const Icon(Icons.payments_rounded),
                  label: s.tabFees,
                ),
                NavigationDestination(
                  icon: const Icon(Icons.menu_book_outlined),
                  selectedIcon: const Icon(Icons.menu_book_rounded),
                  label: s.tabHomework,
                ),
                NavigationDestination(
                  icon: const Icon(Icons.more_horiz_outlined),
                  selectedIcon: const Icon(Icons.more_horiz_rounded),
                  label: s.tabMore,
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
