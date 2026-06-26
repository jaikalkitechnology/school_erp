import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../core/auth_cubit.dart';
import '../../core/children_cubit.dart';
import '../../core/service_locator.dart';
import '../../core/settings_cubit.dart';
import '../../theme/brand.dart';
import '../calendar/calendar_page.dart';
import '../directory/directory_page.dart';
import '../driver/driver_page.dart';
import '../library/library_catalog_page.dart';
import '../messages/messages_page.dart';
import '../notifications/notifications_page.dart';
import '../profile/student_profile_page.dart';
import '../results/result_cards_page.dart';
import '../settings/settings_page.dart';
import '../transport/transport_page.dart';

/// "More" tab — overflow drawer for less-frequent features. Each row
/// pushes a full-screen page so the bottom nav stays uncluttered.
class MorePage extends StatelessWidget {
  const MorePage({super.key});

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsCubit>().state;
    final s = settings.strings;
    final auth = context.watch<AuthCubit>().state;
    final roles = auth is AuthAuthenticated ? auth.user.roles : const <String>[];
    // Anyone with a transport-staff role (or senior school staff) gets
    // the Driver entry point on More so they can run trips from the
    // same Flutter binary as the parent app.
    const _transportStaffRoles = {
      'transport_manager', 'school_admin', 'principal',
      'vice_principal', 'coordinator',
    };
    final showDriver = roles.any(_transportStaffRoles.contains);
    return Scaffold(
      appBar: AppBar(title: Text(s.tabMore)),
      body: RefreshIndicator(
        // The More tab is a static menu — pull-to-refresh just bumps the
        // ChildrenCubit so the next time you tap into Profile / Results /
        // Library you don't see stale child data.
        onRefresh: () async {
          await locator<ChildrenCubit>().load();
        },
        child: ListView(
          children: [
          if (showDriver)
            _Tile(
              icon: Icons.local_taxi_outlined,
              label: 'Driver',
              subtitle: 'Start a trip · live tracking',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const DriverPage()),
              ),
            ),
          _Tile(
            icon: Icons.badge_outlined,
            label: 'Student profile',
            onTap: () => _open(
              context, 'Student profile', const StudentProfilePage(),
            ),
          ),
          _Tile(
            icon: Icons.workspace_premium_outlined,
            label: 'Result cards',
            onTap: () => _open(context, 'Result cards', const ResultCardsPage()),
          ),
          _Tile(
            icon: Icons.event_outlined,
            label: 'Calendar',
            onTap: () => _open(context, 'Calendar', const CalendarPage()),
          ),
          _Tile(
            icon: Icons.directions_bus_outlined,
            label: 'Transport',
            subtitle: 'Bus route, driver, live tracking',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const TransportPage()),
            ),
          ),
          _Tile(
            icon: Icons.menu_book_outlined,
            label: 'Library',
            onTap: () => _open(context, 'Library', const LibraryCatalogPage()),
          ),
          _Tile(
            icon: Icons.contacts_outlined,
            label: 'Contact directory',
            onTap: () => _open(context, 'Teachers', const DirectoryPage()),
          ),
          _Tile(
            icon: Icons.chat_bubble_outline,
            label: 'Messages',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const MessagesPage()),
            ),
          ),
          _Tile(
            icon: Icons.notifications_outlined,
            label: s.tabNotifications,
            onTap: () => _open(context, s.tabNotifications, const NotificationsPage()),
          ),
          _Tile(
            icon: Icons.settings_outlined,
            label: s.tabSettings,
            onTap: () => _open(context, s.tabSettings, const SettingsPage()),
          ),
          const Divider(height: 0),
          ListTile(
            leading: const Icon(Icons.logout, color: Color(0xFFD32F2F)),
            title: const Text('Sign out',
                style: TextStyle(
                  color: Color(0xFFD32F2F),
                  fontWeight: FontWeight.w600,
                )),
            onTap: () => context.read<AuthCubit>().logout(),
          ),
        ],
        ),
      ),
    );
  }

  /// Wraps the pushed page in a Scaffold + AppBar so widgets like
  /// ChoiceChip can find a Material ancestor. The original pages used to
  /// live inside HomeShell's Scaffold and never had their own — moving
  /// them behind the "More" tab via Navigator.push lost that ancestor.
  void _open(BuildContext context, String title, Widget page) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Scaffold(
          appBar: AppBar(title: Text(title)),
          body: page,
        ),
      ),
    );
  }
}

class _Tile extends StatelessWidget {
  const _Tile({
    required this.icon,
    required this.label,
    required this.onTap,
    this.subtitle,
  });

  final IconData icon;
  final String label;
  final String? subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: JaikalkiBrand.saffron),
      title: Text(label),
      subtitle: subtitle == null ? null : Text(subtitle!),
      trailing: const Icon(Icons.chevron_right, color: JaikalkiBrand.textSecondary),
      onTap: onTap,
    );
  }
}
