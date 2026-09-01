import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../api/parent_repository.dart'
    show
        AttendanceRow,
        ChildDashboard,
        HomeworkItem,
        ResultCardRow,
        StudentProfile,
        SubjectAttendanceReport,
        TimetableView;
import '../../api/student_repository.dart';
import '../../core/auth_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
import '../library/library_catalog_page.dart';
import '../notifications/notifications_page.dart';
import '../operations/notice_board_page.dart';
import '../settings/settings_page.dart';

/// Dedicated shell for the `student` role. Unlike the parent HomeShell it
/// has no child-switcher — every screen shows the logged-in student's own
/// data, resolved server-side from their user id.
class StudentShell extends StatefulWidget {
  const StudentShell({super.key});

  @override
  State<StudentShell> createState() => _StudentShellState();
}

class _StudentShellState extends State<StudentShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    const pages = [
      _StudentHomePage(),
      _StudentAttendancePage(),
      _StudentHomeworkPage(),
      _StudentMorePage(),
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
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home_rounded),
              label: 'Home',
            ),
            NavigationDestination(
              icon: Icon(Icons.event_available_outlined),
              selectedIcon: Icon(Icons.event_available_rounded),
              label: 'Attendance',
            ),
            NavigationDestination(
              icon: Icon(Icons.menu_book_outlined),
              selectedIcon: Icon(Icons.menu_book_rounded),
              label: 'Homework',
            ),
            NavigationDestination(
              icon: Icon(Icons.more_horiz_outlined),
              selectedIcon: Icon(Icons.more_horiz_rounded),
              label: 'More',
            ),
          ],
        ),
      ),
    );
  }
}

// ---- Home / dashboard ------------------------------------------------------

class _StudentHomePage extends StatefulWidget {
  const _StudentHomePage();

  @override
  State<_StudentHomePage> createState() => _StudentHomePageState();
}

class _StudentHomePageState extends State<_StudentHomePage> {
  late Future<ChildDashboard?> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<StudentRepository>().dashboard();
  }

  Future<void> _refresh() async {
    setState(() => _future = locator<StudentRepository>().dashboard());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My dashboard')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<ChildDashboard?>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            final d = snap.data;
            if (d == null) {
              return ListView(children: const [
                SizedBox(height: 80),
                Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'Could not load your dashboard.\n'
                    'Make sure your student account is linked to a student '
                    'record — ask the school office.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: JaikalkiBrand.textSecondary),
                  ),
                ),
              ]);
            }
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              children: [
                Text(
                  d.fullName,
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                    color: JaikalkiBrand.indigoDark,
                  ),
                ),
                Text(
                  [
                    d.admissionNumber,
                    if (d.classLabel != null) d.classLabel!,
                  ].join(' · '),
                  style: const TextStyle(color: JaikalkiBrand.textSecondary),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                      child: _StatCard(
                        label: "Today",
                        value: (d.todayAttendance ?? '—')
                            .replaceAll('_', ' ')
                            .toUpperCase(),
                        tone: JaikalkiBrand.teal,
                        icon: Icons.event_available,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _StatCard(
                        label: 'Homework due',
                        value: '${d.pendingHomework}',
                        tone: JaikalkiBrand.saffron,
                        icon: Icons.menu_book,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: _StatCard(
                        label: 'Fees due',
                        value: '₹${d.feeDueAmount.toStringAsFixed(0)}',
                        tone: d.feeDueAmount > 0
                            ? const Color(0xFFD32F2F)
                            : JaikalkiBrand.teal,
                        icon: Icons.payments,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _StatCard(
                        label: 'Documents',
                        value: '${d.documentsCount}',
                        tone: JaikalkiBrand.indigo,
                        icon: Icons.folder_outlined,
                      ),
                    ),
                  ],
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.label,
    required this.value,
    required this.tone,
    required this.icon,
  });
  final String label;
  final String value;
  final Color tone;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: tone.withOpacity(0.10),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: tone.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: tone, size: 20),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w800,
              color: tone,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label.toUpperCase(),
            style: const TextStyle(
              fontSize: 10,
              letterSpacing: 0.4,
              fontWeight: FontWeight.w600,
              color: JaikalkiBrand.textSecondary,
            ),
          ),
        ],
      ),
    );
  }
}

// ---- Attendance ------------------------------------------------------------

class _StudentAttendancePage extends StatefulWidget {
  const _StudentAttendancePage();

  @override
  State<_StudentAttendancePage> createState() => _StudentAttendancePageState();
}

class _StudentAttendancePageState extends State<_StudentAttendancePage> {
  late Future<List<AttendanceRow>> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<StudentRepository>().attendance();
  }

  Future<void> _refresh() async {
    setState(() => _future = locator<StudentRepository>().attendance());
    await _future;
  }

  Color _tone(String status) {
    switch (status) {
      case 'present':
        return JaikalkiBrand.teal;
      case 'absent':
        return const Color(0xFFD32F2F);
      case 'late':
      case 'half_day':
        return JaikalkiBrand.marigold;
      default:
        return JaikalkiBrand.textSecondary;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My attendance')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<AttendanceRow>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            final rows = snap.data ?? const <AttendanceRow>[];
            if (rows.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 80),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text('No attendance records yet.',
                        style:
                            TextStyle(color: JaikalkiBrand.textSecondary)),
                  ),
                ),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
              itemCount: rows.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) {
                final r = rows[i];
                final tone = _tone(r.status);
                return Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: JaikalkiBrand.warmWhite,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: JaikalkiBrand.saffronPale),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(r.date,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                  color: JaikalkiBrand.indigoDark,
                                )),
                            if (r.period.isNotEmpty)
                              Text(r.period,
                                  style: const TextStyle(
                                    fontSize: 12,
                                    color: JaikalkiBrand.textSecondary,
                                  )),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: tone.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          r.status.replaceAll('_', ' ').toUpperCase(),
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            color: tone,
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}

// ---- Homework --------------------------------------------------------------

class _StudentHomeworkPage extends StatefulWidget {
  const _StudentHomeworkPage();

  @override
  State<_StudentHomeworkPage> createState() => _StudentHomeworkPageState();
}

class _StudentHomeworkPageState extends State<_StudentHomeworkPage> {
  late Future<List<HomeworkItem>> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<StudentRepository>().homework();
  }

  Future<void> _refresh() async {
    setState(() => _future = locator<StudentRepository>().homework());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My homework')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<HomeworkItem>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            final all = snap.data ?? const <HomeworkItem>[];
            if (all.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 80),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text('No homework assigned yet.',
                        style:
                            TextStyle(color: JaikalkiBrand.textSecondary)),
                  ),
                ),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
              itemCount: all.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) => _HomeworkCard(
                item: all[i],
                onChanged: _refresh,
              ),
            );
          },
        ),
      ),
    );
  }
}

class _HomeworkCard extends StatelessWidget {
  const _HomeworkCard({required this.item, required this.onChanged});
  final HomeworkItem item;
  final Future<void> Function() onChanged;

  @override
  Widget build(BuildContext context) {
    final status = item.submissionStatus;
    return Container(
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      child: ListTile(
        title: Text(item.title,
            style: const TextStyle(
              fontWeight: FontWeight.w700,
              color: JaikalkiBrand.indigoDark,
            )),
        subtitle: Text(
          [
            if (item.subjectName != null) item.subjectName!,
            'Due ${item.dueDate}',
          ].join(' · '),
          style: const TextStyle(fontSize: 12),
        ),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: JaikalkiBrand.saffronPale,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            status.toUpperCase(),
            style: const TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w800,
              color: JaikalkiBrand.saffronDarker,
            ),
          ),
        ),
        onTap: () async {
          await Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => _HomeworkDetailPage(item: item),
            ),
          );
          await onChanged();
        },
      ),
    );
  }
}

class _HomeworkDetailPage extends StatefulWidget {
  const _HomeworkDetailPage({required this.item});
  final HomeworkItem item;

  @override
  State<_HomeworkDetailPage> createState() => _HomeworkDetailPageState();
}

class _HomeworkDetailPageState extends State<_HomeworkDetailPage> {
  final _ctrl = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final content = _ctrl.text.trim();
    if (content.isEmpty) return;
    setState(() => _submitting = true);
    try {
      await locator<StudentRepository>().submitHomework(
        homeworkId: widget.item.id,
        content: content,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Submitted.')));
      Navigator.of(context).pop();
    } catch (_) {
      if (!mounted) return;
      setState(() => _submitting = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not submit. Try again.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final item = widget.item;
    return Scaffold(
      appBar: AppBar(title: Text(item.title)),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 40),
        children: [
          if (item.subjectName != null)
            Text(item.subjectName!,
                style: const TextStyle(color: JaikalkiBrand.textSecondary)),
          const SizedBox(height: 6),
          Text(item.title,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w800,
                color: JaikalkiBrand.indigoDark,
              )),
          const SizedBox(height: 8),
          Text('Due ${item.dueDate}',
              style: const TextStyle(color: JaikalkiBrand.textSecondary)),
          const SizedBox(height: 16),
          if (item.description != null && item.description!.isNotEmpty)
            Text(item.description!,
                style: const TextStyle(fontSize: 14, height: 1.5)),
          const SizedBox(height: 20),
          if (item.isOpen) ...[
            const Text('Your answer',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: JaikalkiBrand.indigoDark,
                )),
            const SizedBox(height: 8),
            TextField(
              controller: _ctrl,
              maxLines: 6,
              decoration: InputDecoration(
                hintText: 'Type your answer…',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _submitting ? null : _submit,
                style: ElevatedButton.styleFrom(
                  backgroundColor: JaikalkiBrand.saffron,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                ),
                child: _submitting
                    ? const SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2),
                      )
                    : const Text('Submit'),
              ),
            ),
          ] else
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: JaikalkiBrand.tealPale,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                item.isGraded
                    ? 'Graded: ${item.marksObtained?.toStringAsFixed(0) ?? "?"} / ${item.maxMarks?.toStringAsFixed(0) ?? "?"}'
                    : 'Already submitted.',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
            ),
        ],
      ),
    );
  }
}

// ---- More ------------------------------------------------------------------

class _StudentMorePage extends StatelessWidget {
  const _StudentMorePage();

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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('More')),
      body: ListView(
        children: [
          _Tile(
            icon: Icons.badge_outlined,
            label: 'My profile',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const _StudentProfilePage()),
            ),
          ),
          _Tile(
            icon: Icons.workspace_premium_outlined,
            label: 'Result cards',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const _StudentResultsPage()),
            ),
          ),
          _Tile(
            icon: Icons.calendar_view_week_outlined,
            label: 'Timetable',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const _StudentTimetablePage()),
            ),
          ),
          _Tile(
            icon: Icons.insights_outlined,
            label: 'Attendance by subject',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const _StudentBySubjectPage()),
            ),
          ),
          _Tile(
            icon: Icons.menu_book_outlined,
            label: 'Library',
            onTap: () => _open(context, 'Library', const LibraryCatalogPage()),
          ),
          _Tile(
            icon: Icons.campaign_outlined,
            label: 'Notice board',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const NoticeBoardPage()),
            ),
          ),
          _Tile(
            icon: Icons.notifications_outlined,
            label: 'Notifications',
            onTap: () =>
                _open(context, 'Notifications', const NotificationsPage()),
          ),
          _Tile(
            icon: Icons.settings_outlined,
            label: 'Settings',
            onTap: () => _open(context, 'Settings', const SettingsPage()),
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
      trailing:
          const Icon(Icons.chevron_right, color: JaikalkiBrand.textSecondary),
      onTap: onTap,
    );
  }
}

// ---- Profile ---------------------------------------------------------------

class _StudentProfilePage extends StatefulWidget {
  const _StudentProfilePage();

  @override
  State<_StudentProfilePage> createState() => _StudentProfilePageState();
}

class _StudentProfilePageState extends State<_StudentProfilePage> {
  late Future<StudentProfile?> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<StudentRepository>().me();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My profile')),
      body: FutureBuilder<StudentProfile?>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final p = snap.data;
          if (p == null) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('Could not load your profile.',
                    style: TextStyle(color: JaikalkiBrand.textSecondary)),
              ),
            );
          }
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            children: [
              Text(p.fullName,
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                    color: JaikalkiBrand.indigoDark,
                  )),
              Text(p.admissionNumber,
                  style: const TextStyle(color: JaikalkiBrand.textSecondary)),
              const SizedBox(height: 16),
              _row('Class', p.classLabel),
              _row('Section', p.sectionName),
              _row('Roll no.', p.rollNo),
              _row('Date of birth', p.dateOfBirth),
              _row('Gender', p.gender),
              _row('Blood group', p.bloodGroup),
              _row('House', p.houseName),
              _row('Address', p.address),
              _row('Father', p.fatherName),
              _row('Mother', p.motherName),
              _row('Parent phone', p.parentPhone),
              _row('Emergency', p.emergencyPhone),
            ],
          );
        },
      ),
    );
  }

  Widget _row(String label, String? value) {
    if (value == null || value.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(label,
                style: const TextStyle(
                  color: JaikalkiBrand.textSecondary,
                  fontWeight: FontWeight.w600,
                )),
          ),
          Expanded(
            child: Text(value,
                style: const TextStyle(
                  color: JaikalkiBrand.indigoDark,
                  fontWeight: FontWeight.w600,
                )),
          ),
        ],
      ),
    );
  }
}

// ---- Result cards ----------------------------------------------------------

class _StudentResultsPage extends StatefulWidget {
  const _StudentResultsPage();

  @override
  State<_StudentResultsPage> createState() => _StudentResultsPageState();
}

class _StudentResultsPageState extends State<_StudentResultsPage> {
  late Future<List<ResultCardRow>> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<StudentRepository>().reportCards();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Result cards')),
      body: FutureBuilder<List<ResultCardRow>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final rows = snap.data ?? const <ResultCardRow>[];
          if (rows.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('No published result cards yet.',
                    style: TextStyle(color: JaikalkiBrand.textSecondary)),
              ),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            itemCount: rows.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (_, i) {
              final r = rows[i];
              return Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: JaikalkiBrand.warmWhite,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: JaikalkiBrand.saffronPale),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(r.examName,
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                color: JaikalkiBrand.indigoDark,
                              )),
                          if (r.rankInSection != null)
                            Text('Rank ${r.rankInSection}',
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: JaikalkiBrand.textSecondary,
                                )),
                        ],
                      ),
                    ),
                    if (r.percentage != null)
                      Text('${r.percentage!.toStringAsFixed(1)}%',
                          style: const TextStyle(
                            fontWeight: FontWeight.w800,
                            color: JaikalkiBrand.tealDark,
                          )),
                    if (r.overallGrade != null) ...[
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: JaikalkiBrand.saffronPale,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(r.overallGrade!,
                            style: const TextStyle(
                              fontWeight: FontWeight.w800,
                              color: JaikalkiBrand.saffronDarker,
                            )),
                      ),
                    ],
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }
}

// ---- Timetable -------------------------------------------------------------

class _StudentTimetablePage extends StatefulWidget {
  const _StudentTimetablePage();

  @override
  State<_StudentTimetablePage> createState() => _StudentTimetablePageState();
}

class _StudentTimetablePageState extends State<_StudentTimetablePage> {
  late Future<TimetableView?> _future;

  static const _days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  @override
  void initState() {
    super.initState();
    _future = locator<StudentRepository>().timetable();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Timetable')),
      body: FutureBuilder<TimetableView?>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final tt = snap.data;
          if (tt == null || !tt.hasData) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  tt?.note ?? 'No timetable published yet.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: JaikalkiBrand.textSecondary),
                ),
              ),
            );
          }
          // Only render weekdays that actually have cells.
          final activeDays = <int>[];
          for (var d = 0; d < 7; d++) {
            if (tt.dayCells(d).isNotEmpty) activeDays.add(d);
          }
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            children: [
              for (final d in activeDays) ...[
                Padding(
                  padding: const EdgeInsets.fromLTRB(4, 10, 4, 6),
                  child: Text(
                    _days[d].toUpperCase(),
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.8,
                      color: JaikalkiBrand.saffronDark,
                    ),
                  ),
                ),
                for (final c in tt.dayCells(d))
                  Container(
                    margin: const EdgeInsets.only(bottom: 6),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: JaikalkiBrand.warmWhite,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: JaikalkiBrand.saffronPale),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 34,
                          height: 34,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: JaikalkiBrand.saffronPale,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text('${c.periodNumber}',
                              style: const TextStyle(
                                fontWeight: FontWeight.w800,
                                color: JaikalkiBrand.saffronDarker,
                              )),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(c.subjectName ?? 'Free period',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                    color: JaikalkiBrand.indigoDark,
                                  )),
                              Text(
                                [
                                  if (c.teacherName != null) c.teacherName!,
                                  if (c.room != null) 'Room ${c.room}',
                                ].join(' · '),
                                style: const TextStyle(
                                  fontSize: 12,
                                  color: JaikalkiBrand.textSecondary,
                                ),
                              ),
                            ],
                          ),
                        ),
                        if (c.startTime != null)
                          Text(
                            c.startTime!.substring(0, 5),
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: JaikalkiBrand.textSecondary,
                            ),
                          ),
                      ],
                    ),
                  ),
              ],
            ],
          );
        },
      ),
    );
  }
}

// ---- Attendance by subject -------------------------------------------------

class _StudentBySubjectPage extends StatefulWidget {
  const _StudentBySubjectPage();

  @override
  State<_StudentBySubjectPage> createState() => _StudentBySubjectPageState();
}

class _StudentBySubjectPageState extends State<_StudentBySubjectPage> {
  late Future<SubjectAttendanceReport?> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<StudentRepository>().attendanceBySubject();
  }

  Color _tone(double pct) => pct >= 80
      ? JaikalkiBrand.teal
      : pct >= 60
          ? JaikalkiBrand.marigold
          : const Color(0xFFD32F2F);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Attendance by subject')),
      body: FutureBuilder<SubjectAttendanceReport?>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final rep = snap.data;
          if (rep == null || rep.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  rep?.note ?? 'No subject attendance yet.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: JaikalkiBrand.textSecondary),
                ),
              ),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            itemCount: rep.rows.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (_, i) {
              final r = rep.rows[i];
              final tone = _tone(r.percentage);
              return Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: JaikalkiBrand.warmWhite,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: JaikalkiBrand.saffronPale),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(r.subjectName,
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                color: JaikalkiBrand.indigoDark,
                              )),
                        ),
                        Text('${r.percentage.toStringAsFixed(0)}%',
                            style: TextStyle(
                              fontWeight: FontWeight.w800,
                              color: tone,
                            )),
                      ],
                    ),
                    const SizedBox(height: 6),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: (r.percentage / 100).clamp(0, 1),
                        minHeight: 6,
                        backgroundColor: JaikalkiBrand.saffronPale,
                        valueColor: AlwaysStoppedAnimation(tone),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Present ${r.present} · Late ${r.late} · Absent ${r.absent} · of ${r.total}',
                      style: const TextStyle(
                        fontSize: 11,
                        color: JaikalkiBrand.textSecondary,
                      ),
                    ),
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }
}
