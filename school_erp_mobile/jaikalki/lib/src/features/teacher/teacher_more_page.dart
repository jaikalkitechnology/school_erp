import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../core/auth_cubit.dart';
import '../../theme/brand.dart';
import '../notifications/notifications_page.dart';
import '../settings/settings_page.dart';

/// More menu for the teacher shell — homework grading, leave approvals,
/// settings, sign-out. Each row pushes a new full-screen page (with its
/// own Scaffold so ChoiceChip / Material descendants stay happy).
class TeacherMorePage extends StatelessWidget {
  const TeacherMorePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('More')),
      body: ListView(
        children: [
          _Tile(
            icon: Icons.assignment_outlined,
            label: 'Homework grading',
            subtitle: 'Coming soon',
            onTap: () {},
          ),
          _Tile(
            icon: Icons.mail_outline,
            label: 'Leave approvals',
            subtitle: 'Coming soon',
            onTap: () {},
          ),
          _Tile(
            icon: Icons.notifications_outlined,
            label: 'Notifications',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => Scaffold(
                  appBar: AppBar(title: const Text('Notifications')),
                  body: const NotificationsPage(),
                ),
              ),
            ),
          ),
          _Tile(
            icon: Icons.settings_outlined,
            label: 'Settings',
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
      trailing: const Icon(Icons.chevron_right,
          color: JaikalkiBrand.textSecondary),
      onTap: onTap,
    );
  }
}
