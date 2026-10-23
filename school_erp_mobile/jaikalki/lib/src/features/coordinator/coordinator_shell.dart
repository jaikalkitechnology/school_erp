import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../api/coordinator_repository.dart';
import '../../core/auth_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
import '../teacher/sections_page.dart';
import '../teacher/take_attendance_page.dart';
import '../teacher/teacher_more_page.dart';

/// Coordinator's screens: the school's day at a glance (Today), teachers
/// away and their periods to cover (Cover), every class's attendance
/// (Classes), and the usual teacher tools (More) — coordinators often
/// teach too.
class CoordinatorShell extends StatefulWidget {
  const CoordinatorShell({super.key});

  @override
  State<CoordinatorShell> createState() => _CoordinatorShellState();
}

class _CoordinatorShellState extends State<CoordinatorShell> {
  int _index = 0;
  late Future<CoordinatorDay> _day;

  @override
  void initState() {
    super.initState();
    _day = locator<CoordinatorRepository>().today();
  }

  /// One load shared by Today, Cover and Classes.
  Future<void> _reload() async {
    setState(() => _day = locator<CoordinatorRepository>().today());
    try {
      await _day;
    } catch (_) {
      // Shown by the pages.
    }
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      _TodayPage(day: _day, onRefresh: _reload, onOpenCover: () => setState(() => _index = 1)),
      _CoverPage(day: _day, onRefresh: _reload),
      _ClassesPage(day: _day, onRefresh: _reload),
      const TeacherMorePage(),
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
              icon: Icon(Icons.dashboard_outlined),
              selectedIcon: Icon(Icons.dashboard),
              label: 'Today',
            ),
            NavigationDestination(
              icon: Icon(Icons.swap_horiz),
              label: 'Cover',
            ),
            NavigationDestination(
              icon: Icon(Icons.class_outlined),
              selectedIcon: Icon(Icons.class_),
              label: 'Classes',
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

/// Renders [builder] once the day has loaded, with pull-to-refresh and an
/// error card + Retry instead of an empty page when loading fails.
class _DayView extends StatelessWidget {
  const _DayView({required this.day, required this.onRefresh, required this.builder});

  final Future<CoordinatorDay> day;
  final Future<void> Function() onRefresh;
  final List<Widget> Function(BuildContext context, CoordinatorDay d) builder;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<CoordinatorDay>(
      future: day,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final children = snap.hasError
            ? [
                Card(
                  color: Theme.of(context).colorScheme.errorContainer,
                  child: ListTile(
                    title: const Text("Couldn't load today's overview"),
                    subtitle: Text('${snap.error}'),
                    trailing: TextButton(onPressed: onRefresh, child: const Text('Retry')),
                  ),
                ),
              ]
            : builder(context, snap.data!);
        return RefreshIndicator(
          onRefresh: onRefresh,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: children,
          ),
        );
      },
    );
  }
}

class _TodayPage extends StatelessWidget {
  const _TodayPage({required this.day, required this.onRefresh, required this.onOpenCover});

  final Future<CoordinatorDay> day;
  final Future<void> Function() onRefresh;
  final VoidCallback onOpenCover;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Today')),
      body: _DayView(
        day: day,
        onRefresh: onRefresh,
        builder: (context, d) {
          final unmarked = d.sectionRows.where((s) => !s.marked).toList();
          final toCover = d.coverNeeded - d.coverCovered;
          return [
            Text(_longDate(d.date), style: t.titleMedium),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _Stat(
                    label: 'Attendance taken',
                    value: '${d.markedSections}/${d.sections}',
                    hint: 'classes',
                    tone: d.markedSections == d.sections ? _Tone.good : _Tone.warn,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _Stat(
                    label: 'Present',
                    value: d.percent == null ? '—' : '${d.percent!.toStringAsFixed(d.percent! % 1 == 0 ? 0 : 1)}%',
                    hint: '${d.present} present · ${d.absent} absent',
                    tone: _Tone.neutral,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: _Stat(
                    label: 'Teachers away',
                    value: '${d.absentTeachers.length}',
                    hint: d.absentTeachers.isEmpty ? 'everyone is in' : 'today',
                    tone: d.absentTeachers.isEmpty ? _Tone.good : _Tone.warn,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _Stat(
                    label: 'Periods to cover',
                    value: '$toCover',
                    hint: '${d.coverCovered} of ${d.coverNeeded} covered',
                    tone: toCover == 0 ? _Tone.good : _Tone.bad,
                    onTap: onOpenCover,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Text('ATTENDANCE NOT TAKEN', style: t.labelSmall?.copyWith(color: JaikalkiBrand.saffronDark)),
            const SizedBox(height: 6),
            if (unmarked.isEmpty)
              const ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(Icons.check_circle_outline, color: Color(0xFF0F766E)),
                title: Text('Every class has taken attendance.'),
              )
            else
              for (final s in unmarked)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.pending_outlined, color: JaikalkiBrand.saffronDark),
                  title: Text(s.label),
                  subtitle: Text(s.classTeacher == null ? 'No class teacher' : 'Class teacher: ${s.classTeacher}'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => _openAttendance(context, s),
                ),
          ];
        },
      ),
    );
  }
}

class _CoverPage extends StatelessWidget {
  const _CoverPage({required this.day, required this.onRefresh});

  final Future<CoordinatorDay> day;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Cover')),
      body: _DayView(
        day: day,
        onRefresh: onRefresh,
        builder: (context, d) {
          if (d.absentTeachers.isEmpty) {
            return const [
              ListTile(
                leading: Icon(Icons.check_circle_outline, color: Color(0xFF0F766E)),
                title: Text('No teachers away today.'),
                subtitle: Text('Teachers marked absent or on approved leave show up here.'),
              ),
            ];
          }
          return [
            for (final teacher in d.absentTeachers)
              Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(14, 12, 8, 6),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(teacher.name, style: t.titleMedium),
                      Text(teacher.reason, style: t.bodySmall),
                      const SizedBox(height: 4),
                      if (teacher.periods.isEmpty)
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 8),
                          child: Text('No periods on the timetable today.'),
                        ),
                      for (final p in teacher.periods)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: CircleAvatar(
                            radius: 16,
                            backgroundColor: JaikalkiBrand.saffronPale,
                            child: Text(
                              'P${p.period}',
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w700,
                                color: JaikalkiBrand.saffronDark,
                              ),
                            ),
                          ),
                          title: Text(p.subject == null ? p.sectionLabel : '${p.sectionLabel} · ${p.subject}'),
                          subtitle: Text(
                            p.covered ? 'Covered by ${p.substituteName}' : 'Needs cover',
                            style: TextStyle(
                              color: p.covered ? const Color(0xFF0F766E) : const Color(0xFFD32F2F),
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          trailing: p.covered
                              ? const Icon(Icons.check_circle, color: Color(0xFF0F766E))
                              : FilledButton(
                                  // The app theme makes buttons full width;
                                  // in a list row that squeezes the title.
                                  style: FilledButton.styleFrom(
                                    minimumSize: const Size(88, 36),
                                    padding: const EdgeInsets.symmetric(horizontal: 16),
                                  ),
                                  onPressed: () => _assign(context, d.date, teacher, p),
                                  child: const Text('Assign'),
                                ),
                        ),
                    ],
                  ),
                ),
              ),
          ];
        },
      ),
    );
  }

  Future<void> _assign(BuildContext context, String date, AbsentTeacher teacher, CoverPeriod p) async {
    final picked = await showModalBottomSheet<int>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
              child: Text('Cover P${p.period} · ${p.sectionLabel}', style: Theme.of(ctx).textTheme.titleMedium),
            ),
            if (p.suggestions.isEmpty)
              const Padding(
                padding: EdgeInsets.fromLTRB(20, 8, 20, 24),
                child: Text('No free teacher found for this period. Assign cover from the admin website.'),
              )
            else
              for (final s in p.suggestions)
                ListTile(
                  leading: const Icon(Icons.person_outline),
                  title: Text(s.name),
                  subtitle: const Text('Free this period'),
                  onTap: () => Navigator.of(ctx).pop(s.userId),
                ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
    if (picked == null || !context.mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await locator<CoordinatorRepository>().assignCover(
        date: date,
        sectionId: p.sectionId,
        period: p.period,
        substituteUserId: picked,
        reason: '${teacher.name}: ${teacher.reason}',
      );
      messenger.showSnackBar(const SnackBar(content: Text('Cover assigned.')));
      await onRefresh();
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text("Couldn't assign: $e")));
    }
  }
}

class _ClassesPage extends StatelessWidget {
  const _ClassesPage({required this.day, required this.onRefresh});

  final Future<CoordinatorDay> day;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Classes'),
        actions: [
          TextButton.icon(
            icon: const Icon(Icons.person_outline),
            label: const Text('My classes'),
            onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SectionsPage())),
          ),
        ],
      ),
      body: _DayView(
        day: day,
        onRefresh: onRefresh,
        builder: (context, d) => [
          if (d.sectionRows.isEmpty) const ListTile(title: Text('No classes set up yet.')),
          for (final s in d.sectionRows)
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(s.label),
              subtitle: Text([
                if (s.classTeacher != null) s.classTeacher!,
                '${s.strength} students',
              ].join(' · ')),
              trailing: s.marked
                  ? Text('${s.present} in · ${s.absent} out',
                      style: const TextStyle(color: Color(0xFF0F766E), fontWeight: FontWeight.w600))
                  : const Text('Not taken',
                      style: TextStyle(color: JaikalkiBrand.saffronDark, fontWeight: FontWeight.w600)),
              onTap: () => _openAttendance(context, s),
            ),
        ],
      ),
    );
  }
}

void _openAttendance(BuildContext context, SectionDay s) {
  Navigator.of(context).push(
    MaterialPageRoute(builder: (_) => TakeAttendancePage(sectionId: s.sectionId, sectionLabel: s.label)),
  );
}

String _longDate(String ymd) {
  final d = DateTime.tryParse(ymd);
  if (d == null) return ymd;
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return '${days[d.weekday - 1]}, ${d.day} ${months[d.month - 1]} ${d.year}';
}

enum _Tone { good, warn, bad, neutral }

class _Stat extends StatelessWidget {
  const _Stat({required this.label, required this.value, required this.hint, required this.tone, this.onTap});

  final String label;
  final String value;
  final String hint;
  final _Tone tone;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final color = switch (tone) {
      _Tone.good => const Color(0xFF0F766E),
      _Tone.warn => JaikalkiBrand.saffronDark,
      _Tone.bad => const Color(0xFFD32F2F),
      _Tone.neutral => JaikalkiBrand.indigoDark,
    };
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Theme.of(context).colorScheme.outline),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label.toUpperCase(), style: t.labelSmall?.copyWith(color: JaikalkiBrand.textSecondary)),
            const SizedBox(height: 6),
            Text(value, style: t.headlineSmall?.copyWith(color: color, fontWeight: FontWeight.w700)),
            Text(hint, style: t.bodySmall),
          ],
        ),
      ),
    );
  }
}
