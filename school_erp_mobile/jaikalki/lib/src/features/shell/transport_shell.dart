import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth_cubit.dart';
import '../../theme/brand.dart';
import '../driver/driver_page.dart';
import '../driver/driver_profile_page.dart';
import '../driver/driver_routes_page.dart';
import '../driver/driver_stops_map_page.dart';
import '../driver/driver_students_page.dart';
import '../messages/messages_page.dart';
import '../notifications/notifications_page.dart';
import '../settings/settings_page.dart';

/// Bottom-nav shell shown when a user logs in with ``transport_manager``
/// as their role. Strips every parent / teacher surface — no
/// attendance, no fees, no homework.
///
/// Five tabs cover the bus driver ↔ parent coordination loop:
///   1. **Bus**       — today's routes, start trip, GPS pinger, end
///                       trip, boarding scan.
///   2. **Students**  — full roster across every assigned route with
///                       parent + emergency contact, allergies,
///                       address, today's skip flag, call / SMS.
///   3. **Routes**    — every route with stops, tap a stop to open
///                       its lat/lng in Google Maps.
///   4. **Messages**  — 1-on-1 chat threads with parents (existing
///                       MessagesPage; same backend as the parent app).
///   5. **More**      — notifications, settings, sign out.
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
      DriverStudentsPage(),
      DriverRoutesPage(),
      MessagesPage(),
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
              icon: Icon(Icons.groups_outlined),
              selectedIcon: Icon(Icons.groups),
              label: 'Students',
            ),
            NavigationDestination(
              icon: Icon(Icons.alt_route_outlined),
              selectedIcon: Icon(Icons.alt_route),
              label: 'Routes',
            ),
            NavigationDestination(
              icon: Icon(Icons.chat_bubble_outline),
              selectedIcon: Icon(Icons.chat_bubble),
              label: 'Messages',
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
            leading: const Icon(Icons.person_outline,
                color: JaikalkiBrand.saffron),
            title: const Text('My profile'),
            subtitle: const Text(
              'Driver details, license, assigned routes & buses',
              style: TextStyle(
                fontSize: 12,
                color: JaikalkiBrand.textSecondary,
              ),
            ),
            trailing: const Icon(Icons.chevron_right,
                color: JaikalkiBrand.textSecondary),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const DriverProfilePage(),
              ),
            ),
          ),
          ListTile(
            leading: const Icon(Icons.map_outlined,
                color: JaikalkiBrand.saffron),
            title: const Text('Route map'),
            subtitle: const Text(
              'See every stop on each route on a map',
              style: TextStyle(
                fontSize: 12,
                color: JaikalkiBrand.textSecondary,
              ),
            ),
            trailing: const Icon(Icons.chevron_right,
                color: JaikalkiBrand.textSecondary),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const DriverStopsMapPage(),
              ),
            ),
          ),
          const Divider(height: 0),
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
