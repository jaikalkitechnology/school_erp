import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth_cubit.dart';
import '../../theme/brand.dart';
import '../driver/driver_page.dart';
import '../notifications/notifications_page.dart';
import '../settings/settings_page.dart';

/// Bottom-nav shell shown when a user logs in with ``transport_manager``
/// as their role. Strips every parent / teacher surface — no
/// attendance, no fees, no homework. Just the bus screen and an
/// account drawer.
///
/// Two tabs:
///   1. **Bus** — DriverPage (today's routes, start trip, GPS pinger,
///      end trip).
///   2. **More** — notifications, settings, sign out.
class TransportShell extends StatefulWidget {
  const TransportShell({super.key});

  @override
  State<TransportShell> createState() => _TransportShellState();
}

class _TransportShellState extends State<TransportShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    const pages = [
      DriverPage(),
      _TransportMorePage(),
    ];
    return BlocListener<AuthCubit, AuthState>(
      listenWhen: (prev, curr) =>
          curr is AuthInitial && prev is AuthAuthenticated,
      listener: (context, state) {
        if (state is AuthInitial) context.go('/login');
      },
      child: Scaffold(
        body: IndexedStack(index: _index, children: pages),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (i) => setState(() => _index = i),
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.directions_bus_outlined),
              selectedIcon: Icon(Icons.directions_bus_filled),
              label: 'Bus',
            ),
            NavigationDestination(
              icon: Icon(Icons.more_horiz_outlined),
              selectedIcon: Icon(Icons.more_horiz),
              label: 'More',
            ),
          ],
        ),
      ),
    );
  }
}

/// Stripped-down "More" tab — just the account essentials. The
/// transport_manager has no children to switch between, no calendar
/// to peek at, no result cards. So we keep this lean.
class _TransportMorePage extends StatelessWidget {
  const _TransportMorePage();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('More')),
      body: ListView(
        children: [
          ListTile(
            leading: const Icon(Icons.notifications_outlined,
                color: JaikalkiBrand.saffron),
            title: const Text('Notifications'),
            trailing: const Icon(Icons.chevron_right,
                color: JaikalkiBrand.textSecondary),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => Scaffold(
                  appBar: AppBar(title: const Text('Notifications')),
                  body: const NotificationsPage(),
                ),
              ),
            ),
          ),
          ListTile(
            leading: const Icon(Icons.settings_outlined,
                color: JaikalkiBrand.saffron),
            title: const Text('Settings'),
            trailing: const Icon(Icons.chevron_right,
                color: JaikalkiBrand.textSecondary),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => Scaffold(
                  appBar: AppBar(title: const Text('Settings')),
                  body: const SettingsPage(),
                ),
              ),
            ),
          ),
          const Divider(height: 0),
          ListTile(
            leading: const Icon(Icons.logout, color: Color(0xFFD32F2F)),
            title: const Text(
              'Sign out',
              style: TextStyle(
                color: Color(0xFFD32F2F),
                fontWeight: FontWeight.w600,
              ),
            ),
            onTap: () => context.read<AuthCubit>().logout(),
          ),
        ],
      ),
    );
  }
}
