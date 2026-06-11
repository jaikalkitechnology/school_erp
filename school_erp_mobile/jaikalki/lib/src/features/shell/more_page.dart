import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../core/auth_cubit.dart';
import '../../core/settings_cubit.dart';
import '../../theme/brand.dart';
import '../notifications/notifications_page.dart';
import '../settings/settings_page.dart';

/// "More" tab — overflow drawer for less-frequent features. Each row
/// pushes a full-screen page so the bottom nav stays uncluttered.
class MorePage extends StatelessWidget {
  const MorePage({super.key});

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsCubit>().state;
    final s = settings.strings;
    return Scaffold(
      appBar: AppBar(title: Text(s.tabMore)),
      body: ListView(
        children: [
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
  const _Tile({required this.icon, required this.label, required this.onTap});

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: JaikalkiBrand.saffron),
      title: Text(label),
      trailing: const Icon(Icons.chevron_right, color: JaikalkiBrand.textSecondary),
      onTap: onTap,
    );
  }
}
