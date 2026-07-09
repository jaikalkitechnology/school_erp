import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../core/auth_cubit.dart';
import '../../theme/brand.dart';
import '../calendar/calendar_page.dart';
import '../messages/messages_page.dart';
import '../notifications/notifications_page.dart';
import '../operations/my_payslips_page.dart';
import '../operations/notice_board_page.dart';
import '../operations/sports_page.dart';
import '../principal/principal_academics_page.dart';
import '../principal/principal_approvals_page.dart';
import '../principal/principal_dashboard_page.dart';
import '../principal/principal_discipline_page.dart';
import '../principal/principal_finance_page.dart';
import '../principal/principal_staff_page.dart';
import '../principal/principal_transport_page.dart';
import '../settings/settings_page.dart';

/// Bottom-nav shell shown when a user logs in as ``principal`` /
/// ``vice_principal``. Five tabs: Today (dashboard), Approvals,
/// Academics, Staff, More. The More tab is a hub for Finance,
/// Discipline, Transport oversight, Communication, Calendar, etc.
class PrincipalShell extends StatefulWidget {
  const PrincipalShell({super.key});

  @override
  State<PrincipalShell> createState() => _PrincipalShellState();
}

class _PrincipalShellState extends State<PrincipalShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    const pages = [
      PrincipalDashboardPage(),
      PrincipalApprovalsPage(),
      PrincipalAcademicsPage(),
      PrincipalStaffPage(),
      _PrincipalMorePage(),
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
              icon: Icon(Icons.dashboard_outlined),
              selectedIcon: Icon(Icons.dashboard),
              label: 'Today',
            ),
            NavigationDestination(
              icon: Icon(Icons.inbox_outlined),
              selectedIcon: Icon(Icons.inbox),
              label: 'Approvals',
            ),
            NavigationDestination(
              icon: Icon(Icons.fact_check_outlined),
              selectedIcon: Icon(Icons.fact_check),
              label: 'Academics',
            ),
            NavigationDestination(
              icon: Icon(Icons.badge_outlined),
              selectedIcon: Icon(Icons.badge),
              label: 'Staff',
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

class _PrincipalMorePage extends StatelessWidget {
  const _PrincipalMorePage();

  Widget _tile(
    BuildContext context, {
    required IconData icon,
    required String title,
    required WidgetBuilder builder,
    String? subtitle,
  }) =>
      ListTile(
        leading: Icon(icon, color: JaikalkiBrand.saffron),
        title: Text(title),
        subtitle: subtitle == null
            ? null
            : Text(subtitle,
                style: const TextStyle(
                  fontSize: 12,
                  color: JaikalkiBrand.textSecondary,
                )),
        trailing: const Icon(Icons.chevron_right,
            color: JaikalkiBrand.textSecondary),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: builder),
        ),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('More')),
      body: ListView(
        children: [
          _tile(
            context,
            icon: Icons.account_balance_wallet_outlined,
            title: 'Finance',
            subtitle: 'Collection by class, defaulters, trend',
            builder: (_) => const PrincipalFinancePage(),
          ),
          _tile(
            context,
            icon: Icons.warning_amber_outlined,
            title: 'Discipline',
            subtitle: 'Recent behaviour concerns',
            builder: (_) => const PrincipalDisciplinePage(),
          ),
          _tile(
            context,
            icon: Icons.directions_bus_outlined,
            title: 'Transport',
            subtitle: "Today's fleet status",
            builder: (_) => const PrincipalTransportPage(),
          ),
          _tile(
            context,
            icon: Icons.chat_bubble_outline,
            title: 'Messages',
            subtitle: 'Threads with teachers and parents',
            builder: (_) => Scaffold(
              appBar: AppBar(title: const Text('Messages')),
              body: const MessagesPage(),
            ),
          ),
          _tile(
            context,
            icon: Icons.calendar_today_outlined,
            title: 'Calendar',
            subtitle: 'Holidays, events, exams',
            builder: (_) => Scaffold(
              appBar: AppBar(title: const Text('Calendar')),
              body: const CalendarPage(),
            ),
          ),
          _tile(
            context,
            icon: Icons.campaign_outlined,
            title: 'Notice board',
            subtitle: 'School announcements + circulars',
            builder: (_) => const NoticeBoardPage(),
          ),
          _tile(
            context,
            icon: Icons.sports_soccer_outlined,
            title: 'Sports & clubs',
            subtitle: 'House leaderboard + events',
            builder: (_) => const SportsPage(),
          ),
          _tile(
            context,
            icon: Icons.receipt_long_outlined,
            title: 'My payslips',
            subtitle: 'Your salary slips',
            builder: (_) => const MyPayslipsPage(),
          ),
          _tile(
            context,
            icon: Icons.notifications_outlined,
            title: 'Notifications',
            builder: (_) => Scaffold(
              appBar: AppBar(title: const Text('Notifications')),
              body: const NotificationsPage(),
            ),
          ),
          _tile(
            context,
            icon: Icons.settings_outlined,
            title: 'Settings',
            builder: (_) => Scaffold(
              appBar: AppBar(title: const Text('Settings')),
              body: const SettingsPage(),
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
