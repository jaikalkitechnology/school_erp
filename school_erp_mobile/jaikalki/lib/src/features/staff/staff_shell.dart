import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../api/operations_repository.dart';
import '../../api/teacher_repository.dart';
import '../../core/auth_cubit.dart';
import '../../core/service_locator.dart';
import '../../models/user_role.dart';
import '../../theme/brand.dart';
import '../messages/messages_page.dart';
import '../notifications/notifications_page.dart';
import '../operations/my_payslips_page.dart';
import '../operations/notice_board_page.dart';
import '../operations/sports_page.dart';
import '../settings/settings_page.dart';
import '../teacher/my_leaves_page.dart';
import '../teacher/teacher_calendar_page.dart';

/// Shell for non-teaching staff (accountant, librarian, hostel warden,
/// office staff, receptionist, visitor desk, supervisor, ...). Their
/// day-to-day work tools live on the admin website; in the app they get
/// the self-service every staff member needs: notices, messages, leave,
/// calendar and payslips.
class StaffShell extends StatefulWidget {
  const StaffShell({super.key});

  @override
  State<StaffShell> createState() => _StaffShellState();
}

class _StaffShellState extends State<StaffShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final pages = [
      StaffHomePage(onOpenLeave: () => setState(() => _index = 2)),
      const MessagesPage(),
      const MyLeavesPage(staffApi: true),
      const _StaffMorePage(),
    ];
    return BlocListener<AuthCubit, AuthState>(
      listenWhen: (a, b) => b is AuthInitial && a is AuthAuthenticated,
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
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home_rounded),
              label: 'Home',
            ),
            NavigationDestination(
              icon: Icon(Icons.chat_bubble_outline),
              selectedIcon: Icon(Icons.chat_bubble),
              label: 'Messages',
            ),
            NavigationDestination(
              icon: Icon(Icons.beach_access_outlined),
              selectedIcon: Icon(Icons.beach_access),
              label: 'Leave',
            ),
            NavigationDestination(
              icon: Icon(Icons.menu),
              label: 'More',
            ),
          ],
        ),
      ),
    );
  }
}

/// Greeting, what's coming up, the latest notices and my leave status.
class StaffHomePage extends StatefulWidget {
  const StaffHomePage({super.key, required this.onOpenLeave});

  final VoidCallback onOpenLeave;

  @override
  State<StaffHomePage> createState() => _StaffHomePageState();
}

class _StaffHomePageState extends State<StaffHomePage> {
  late Future<List<_Upcoming>> _upcoming;
  late Future<List<NoticeItem>> _notices;
  late Future<List<StaffLeaveRow>> _leaves;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final t = locator<TeacherRepository>();
    _upcoming = _loadUpcoming(t);
    _notices = locator<OperationsRepository>().notices();
    _leaves = t.myLeaves(staff: true);
  }

  Future<void> _refresh() async {
    setState(_load);
    await Future.wait([_upcoming, _notices, _leaves]);
  }

  /// Next few holidays + events, soonest first.
  static Future<List<_Upcoming>> _loadUpcoming(TeacherRepository t) async {
    final today = DateTime.now();
    final day = DateTime(today.year, today.month, today.day);
    final (holidays, events) = await (t.holidays(staff: true), t.events(staff: true)).wait;
    final items = <_Upcoming>[
      for (final h in holidays)
        if (DateTime.tryParse(h.date) case final d? when !d.isBefore(day))
          _Upcoming(d, h.name, 'Holiday', Icons.beach_access_outlined),
      for (final e in events)
        if (DateTime.tryParse(e.startsAt) case final d? when !d.isBefore(day))
          _Upcoming(d, e.title, 'Event', Icons.event_outlined),
    ]..sort((a, b) => a.date.compareTo(b.date));
    return items.take(4).toList();
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final auth = context.watch<AuthCubit>().state;
    final user = auth is AuthAuthenticated ? auth.user : null;
    final firstName = (user?.fullName ?? '').split(' ').first;
    final hour = DateTime.now().hour;
    final greeting = hour < 12
        ? 'Good morning'
        : hour < 17
            ? 'Good afternoon'
            : 'Good evening';

    return Scaffold(
      appBar: AppBar(title: Text(user?.schoolName ?? 'Home')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            Text('$greeting${firstName.isEmpty ? '' : ', $firstName'}', style: t.headlineSmall),
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final r in user?.roles ?? const <String>[])
                  Chip(
                    label: Text(roleLabelFor(r)),
                    visualDensity: VisualDensity.compact,
                    backgroundColor: JaikalkiBrand.saffronPale,
                    side: BorderSide.none,
                  ),
              ],
            ),
            const SizedBox(height: 16),
            _Section(
              title: 'COMING UP',
              child: FutureBuilder<List<_Upcoming>>(
                future: _upcoming,
                builder: (context, snap) {
                  if (snap.connectionState != ConnectionState.done) return const _Loading();
                  final items = snap.data ?? const <_Upcoming>[];
                  if (items.isEmpty) return const _Empty('No holidays or events coming up.');
                  return Column(
                    children: [
                      for (final u in items)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: Icon(u.icon, color: JaikalkiBrand.saffron),
                          title: Text(u.title),
                          subtitle: Text('${u.kind} · ${_date(u.date)}'),
                        ),
                    ],
                  );
                },
              ),
              onMore: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const TeacherCalendarPage(staffApi: true)),
              ),
            ),
            _Section(
              title: 'NOTICE BOARD',
              child: FutureBuilder<List<NoticeItem>>(
                future: _notices,
                builder: (context, snap) {
                  if (snap.connectionState != ConnectionState.done) return const _Loading();
                  final items = (snap.data ?? const <NoticeItem>[]).take(3).toList();
                  if (items.isEmpty) return const _Empty('No notices right now.');
                  return Column(
                    children: [
                      for (final n in items)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: Icon(
                            n.isPinned ? Icons.push_pin : Icons.campaign_outlined,
                            color: JaikalkiBrand.saffron,
                          ),
                          title: Text(n.title),
                          subtitle: Text(n.body, maxLines: 2, overflow: TextOverflow.ellipsis),
                        ),
                    ],
                  );
                },
              ),
              onMore: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const NoticeBoardPage()),
              ),
            ),
            _Section(
              title: 'MY LEAVE',
              child: FutureBuilder<List<StaffLeaveRow>>(
                future: _leaves,
                builder: (context, snap) {
                  if (snap.connectionState != ConnectionState.done) return const _Loading();
                  final rows = snap.data ?? const <StaffLeaveRow>[];
                  if (rows.isEmpty) return const _Empty('No leave applied yet.');
                  final latest = rows.first;
                  return ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(_leaveIcon(latest.status), color: _leaveColor(latest.status)),
                    title: Text('${_ymd(latest.startDate)} → ${_ymd(latest.endDate)}'),
                    subtitle: Text('${_cap(latest.kind)} · ${_cap(latest.status)}'),
                  );
                },
              ),
              onMore: widget.onOpenLeave,
              moreLabel: 'Apply / view',
            ),
          ],
        ),
      ),
    );
  }

  static String _date(DateTime d) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return '${d.day} ${months[d.month - 1]} ${d.year}';
  }

  /// "2026-10-31" → "31 Oct 2026" (left as-is if it isn't a date).
  static String _ymd(String s) {
    final d = DateTime.tryParse(s);
    return d == null ? s : _date(d);
  }

  static String _cap(String s) => s.isEmpty ? s : '${s[0].toUpperCase()}${s.substring(1)}';

  static IconData _leaveIcon(String status) => switch (status) {
        'approved' => Icons.check_circle_outline,
        'rejected' => Icons.cancel_outlined,
        _ => Icons.hourglass_empty,
      };

  static Color _leaveColor(String status) => switch (status) {
        'approved' => const Color(0xFF0F766E),
        'rejected' => const Color(0xFFD32F2F),
        _ => JaikalkiBrand.saffronDark,
      };
}

class _Upcoming {
  const _Upcoming(this.date, this.title, this.kind, this.icon);
  final DateTime date;
  final String title;
  final String kind;
  final IconData icon;
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.child, required this.onMore, this.moreLabel = 'See all'});

  final String title;
  final Widget child;
  final VoidCallback onMore;
  final String moreLabel;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.fromLTRB(14, 8, 8, 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(title, style: t.labelSmall?.copyWith(color: JaikalkiBrand.saffronDark))),
              TextButton(onPressed: onMore, child: Text(moreLabel)),
            ],
          ),
          child,
        ],
      ),
    );
  }
}

class _Loading extends StatelessWidget {
  const _Loading();

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.all(12),
        child: Center(child: SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))),
      );
}

class _Empty extends StatelessWidget {
  const _Empty(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Text(text, style: Theme.of(context).textTheme.bodyMedium),
      );
}

class _StaffMorePage extends StatelessWidget {
  const _StaffMorePage();

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
            : Text(subtitle, style: const TextStyle(fontSize: 12, color: JaikalkiBrand.textSecondary)),
        trailing: const Icon(Icons.chevron_right, color: JaikalkiBrand.textSecondary),
        onTap: () => Navigator.of(context).push(MaterialPageRoute(builder: builder)),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('More')),
      body: ListView(
        children: [
          _tile(
            context,
            icon: Icons.campaign_outlined,
            title: 'Notice board',
            subtitle: 'School announcements + circulars',
            builder: (_) => const NoticeBoardPage(),
          ),
          _tile(
            context,
            icon: Icons.calendar_today_outlined,
            title: 'Calendar',
            subtitle: 'Holidays and events',
            builder: (_) => const TeacherCalendarPage(staffApi: true),
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
            icon: Icons.sports_soccer_outlined,
            title: 'Sports & clubs',
            subtitle: 'House leaderboard + events',
            builder: (_) => const SportsPage(),
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
              style: TextStyle(color: Color(0xFFD32F2F), fontWeight: FontWeight.w600),
            ),
            onTap: () => context.read<AuthCubit>().logout(),
          ),
        ],
      ),
    );
  }
}
