import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../api/teacher_repository.dart';
import '../../core/auth_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
import '../../widgets/authed_photo.dart';
import '../notifications/notifications_page.dart';
import '../operations/my_payslips_page.dart';
import '../operations/notice_board_page.dart';
import '../operations/sports_page.dart';
import '../settings/settings_page.dart';
import 'chat_list_page.dart';
import 'homework_list_page.dart';
import 'leaves_page.dart';
import 'my_leaves_page.dart';
import 'teacher_calendar_page.dart';

/// More menu for the teacher shell. Above-the-fold: a gradient profile
/// header pulled from /v1/teacher/me. Below: a 2-column grid of the
/// "tasks" surfaces (homework, leaves, chat, calendar) plus a quieter
/// "Account" list for settings / notifications / sign-out.
class TeacherMorePage extends StatefulWidget {
  const TeacherMorePage({super.key});

  @override
  State<TeacherMorePage> createState() => _TeacherMorePageState();
}

class _TeacherMorePageState extends State<TeacherMorePage> {
  late Future<TeacherMe?> _meFuture;

  @override
  void initState() {
    super.initState();
    _meFuture = _safeMe();
  }

  Future<TeacherMe?> _safeMe() async {
    try {
      return await locator<TeacherRepository>().me();
    } catch (_) {
      return null;
    }
  }

  Future<void> _confirmLogout(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Sign out?'),
        content: const Text(
          "You'll need to sign in again to see today's classes and messages.",
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFFD32F2F),
            ),
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Sign out'),
          ),
        ],
      ),
    );
    if (ok == true && context.mounted) {
      await context.read<AuthCubit>().logout();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: JaikalkiBrand.ivory,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
          children: [
            FutureBuilder<TeacherMe?>(
              future: _meFuture,
              builder: (context, snap) {
                final me = snap.data;
                return _ProfileHeader(profile: me?.profile);
              },
            ),
            const SizedBox(height: 20),
            const _SectionLabel(text: 'TASKS'),
            const SizedBox(height: 10),
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              childAspectRatio: 1.05,
              children: [
                _ActionCard(
                  icon: Icons.assignment_turned_in_outlined,
                  label: 'Homework grading',
                  subtitle: 'Submissions, marks, feedback',
                  tint: JaikalkiBrand.saffron,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                        builder: (_) => const HomeworkListPage()),
                  ),
                ),
                _ActionCard(
                  icon: Icons.chat_bubble_outline,
                  label: 'Chat',
                  subtitle: 'Admins & parents',
                  tint: JaikalkiBrand.teal,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const ChatListPage()),
                  ),
                ),
                _ActionCard(
                  icon: Icons.mail_outline,
                  label: 'Leave approvals',
                  subtitle: 'Decide student leave',
                  tint: JaikalkiBrand.indigoDark,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const LeavesPage()),
                  ),
                ),
                _ActionCard(
                  icon: Icons.event_busy_outlined,
                  label: 'My leaves',
                  subtitle: 'Apply & track status',
                  tint: JaikalkiBrand.marigold,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const MyLeavesPage()),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            _WideCard(
              icon: Icons.event_outlined,
              label: 'Calendar',
              subtitle: 'Events, holidays, exams',
              tint: JaikalkiBrand.saffronDark,
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                    builder: (_) => const TeacherCalendarPage()),
              ),
            ),
            const SizedBox(height: 24),
            const _SectionLabel(text: 'ACCOUNT'),
            const SizedBox(height: 8),
            _ListCard(
              children: [
                _ListRow(
                  icon: Icons.campaign_outlined,
                  label: 'Notice board',
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const NoticeBoardPage()),
                  ),
                ),
                const _Separator(),
                _ListRow(
                  icon: Icons.receipt_long_outlined,
                  label: 'My payslips',
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const MyPayslipsPage()),
                  ),
                ),
                const _Separator(),
                _ListRow(
                  icon: Icons.sports_soccer_outlined,
                  label: 'Sports & clubs',
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const SportsPage()),
                  ),
                ),
                const _Separator(),
                _ListRow(
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
                const _Separator(),
                _ListRow(
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
              ],
            ),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: () => _confirmLogout(context),
              icon: const Icon(Icons.logout, color: Color(0xFFD32F2F)),
              label: const Text(
                'Sign out',
                style: TextStyle(
                  color: Color(0xFFD32F2F),
                  fontWeight: FontWeight.w700,
                ),
              ),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                side: const BorderSide(color: Color(0xFFD32F2F)),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Center(
              child: Text(
                'Jaikalki Mobile',
                style: TextStyle(
                  fontSize: 11,
                  color: JaikalkiBrand.textSecondary.withOpacity(0.7),
                  letterSpacing: 1.2,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ProfileHeader extends StatelessWidget {
  const _ProfileHeader({required this.profile});
  final TeacherProfile? profile;

  String _initials(String n) {
    final parts = n.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts[0].isEmpty) return 'J';
    if (parts.length == 1) return parts[0][0].toUpperCase();
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    final name = profile?.fullName ?? 'Teacher';
    final role = profile?.designation ??
        (profile?.isClassTeacher == true ? 'Class teacher' : 'Teacher');
    final school = profile?.schoolName;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [JaikalkiBrand.indigoDark, Color(0xFF3A2A6B)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: JaikalkiBrand.indigoDark.withOpacity(0.18),
            blurRadius: 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.white.withOpacity(0.18),
              border: Border.all(
                  color: Colors.white.withOpacity(0.35), width: 2),
            ),
            clipBehavior: Clip.antiAlias,
            alignment: Alignment.center,
            child: AuthedPhoto(
              path: profile?.photoUrl,
              placeholder: Text(
                _initials(name),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  role,
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.85),
                    fontSize: 12,
                  ),
                ),
                if (school != null && school.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.school_outlined,
                          size: 12, color: JaikalkiBrand.marigoldPale),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          school,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 11,
                            color: JaikalkiBrand.marigoldPale
                                .withOpacity(0.95),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel({required this.text});
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(left: 4),
        child: Text(
          text,
          style: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.4,
            color: JaikalkiBrand.textSecondary,
          ),
        ),
      );
}

class _ActionCard extends StatelessWidget {
  const _ActionCard({
    required this.icon,
    required this.label,
    required this.subtitle,
    required this.tint,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final String subtitle;
  final Color tint;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: JaikalkiBrand.warmWhite,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: JaikalkiBrand.saffronPale),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 40,
                height: 40,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: tint.withOpacity(0.13),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: tint, size: 22),
              ),
              const Spacer(),
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w800,
                  color: JaikalkiBrand.indigoDark,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 11,
                  height: 1.3,
                  color: JaikalkiBrand.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _WideCard extends StatelessWidget {
  const _WideCard({
    required this.icon,
    required this.label,
    required this.subtitle,
    required this.tint,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final String subtitle;
  final Color tint;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: JaikalkiBrand.warmWhite,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: JaikalkiBrand.saffronPale),
          ),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: tint.withOpacity(0.13),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: tint, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(label,
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w800,
                          color: JaikalkiBrand.indigoDark,
                        )),
                    const SizedBox(height: 2),
                    Text(subtitle,
                        style: const TextStyle(
                          fontSize: 12,
                          color: JaikalkiBrand.textSecondary,
                        )),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right,
                  color: JaikalkiBrand.textSecondary),
            ],
          ),
        ),
      ),
    );
  }
}

class _ListCard extends StatelessWidget {
  const _ListCard({required this.children});
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: JaikalkiBrand.warmWhite,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: JaikalkiBrand.saffronPale),
        ),
        child: Column(children: children),
      );
}

class _ListRow extends StatelessWidget {
  const _ListRow({
    required this.icon,
    required this.label,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          child: Row(
            children: [
              Icon(icon, color: JaikalkiBrand.saffron, size: 22),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: JaikalkiBrand.indigoDark,
                  ),
                ),
              ),
              const Icon(Icons.chevron_right,
                  color: JaikalkiBrand.textSecondary, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}

class _Separator extends StatelessWidget {
  const _Separator();
  @override
  Widget build(BuildContext context) =>
      Container(height: 1, color: JaikalkiBrand.saffronPale.withOpacity(0.6));
}
