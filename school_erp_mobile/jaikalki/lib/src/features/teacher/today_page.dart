import 'package:flutter/material.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
import 'take_attendance_page.dart';
import 'teacher_id_card_preview.dart';
import 'weekly_timetable.dart';

class TodayPage extends StatefulWidget {
  const TodayPage({super.key});

  @override
  State<TodayPage> createState() => _TodayPageState();
}

class _TodayPageState extends State<TodayPage> {
  late Future<TeacherToday> _future;
  late Future<TeacherMe> _me;
  late Future<TeacherWeekTimetable> _tt;

  @override
  void initState() {
    super.initState();
    final repo = locator<TeacherRepository>();
    _future = repo.today();
    _me = repo.me();
    _tt = repo.timetable();
  }

  Future<void> _reload() async {
    final repo = locator<TeacherRepository>();
    setState(() {
      _future = repo.today();
      _me = repo.me();
      _tt = repo.timetable();
    });
    await Future.wait<dynamic>([_future, _me, _tt]);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Today')),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: FutureBuilder<TeacherToday>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: [
                Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text(
                    'Could not load today: ${snap.error}',
                    style: const TextStyle(color: Color(0xFFD32F2F)),
                  ),
                ),
              ]);
            }
            final today = snap.data!;
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              children: [
                FutureBuilder<TeacherMe>(
                  future: _me,
                  builder: (_, meSnap) =>
                      _Greeting(profile: meSnap.data?.profile),
                ),
                const SizedBox(height: 12),
                _CountStrip(today: today),
                const SizedBox(height: 16),
                FutureBuilder<TeacherMe>(
                  future: _me,
                  builder: (_, meSnap) {
                    if (meSnap.data == null) return const SizedBox.shrink();
                    return _IdCardTile(profile: meSnap.data!.profile);
                  },
                ),
                const SizedBox(height: 16),
                const _SectionLabel('Today'),
                const SizedBox(height: 8),
                if (today.periods.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 24),
                    child: Center(
                      child: Text(
                        'No periods scheduled for today.',
                        style: TextStyle(color: JaikalkiBrand.textSecondary),
                      ),
                    ),
                  )
                else
                  ...today.periods.map((p) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: _PeriodCard(period: p),
                      )),
                const SizedBox(height: 16),
                const _SectionLabel('Weekly timetable'),
                const SizedBox(height: 8),
                FutureBuilder<TeacherWeekTimetable>(
                  future: _tt,
                  builder: (_, ttSnap) {
                    if (ttSnap.connectionState != ConnectionState.done) {
                      return const Padding(
                        padding: EdgeInsets.symmetric(vertical: 24),
                        child: Center(child: CircularProgressIndicator()),
                      );
                    }
                    final tt = ttSnap.data ??
                        const TeacherWeekTimetable(days: [], rows: []);
                    return WeeklyTimetable(
                      tt: tt,
                      onTapPeriod: (p) {
                        if (p.sectionId != null) {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => TakeAttendancePage(
                                sectionId: p.sectionId!,
                                sectionLabel: p.sectionLabel ?? 'Section',
                              ),
                            ),
                          );
                        }
                      },
                    );
                  },
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _Greeting extends StatelessWidget {
  const _Greeting({required this.profile});
  final TeacherProfile? profile;

  @override
  Widget build(BuildContext context) {
    final firstName = (profile?.fullName.split(' ').first) ?? 'there';
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [JaikalkiBrand.indigoDark, Color(0xFF3A2A6B)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          const CircleAvatar(
            radius: 24,
            backgroundColor: Colors.white24,
            child: Icon(Icons.school, color: Colors.white),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Namaste, $firstName',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    )),
                const SizedBox(height: 2),
                Text(
                  profile?.designation ?? 'Teacher',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.85),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _CountStrip extends StatelessWidget {
  const _CountStrip({required this.today});
  final TeacherToday today;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _CountTile(
          icon: Icons.event_available_outlined,
          label: 'To mark',
          value: today.sectionsToMarkAttendance.toString(),
          tone: JaikalkiBrand.saffron,
        ),
        const SizedBox(width: 8),
        _CountTile(
          icon: Icons.assignment_outlined,
          label: 'To grade',
          value: today.pendingHomeworkCount.toString(),
          tone: JaikalkiBrand.teal,
        ),
        const SizedBox(width: 8),
        _CountTile(
          icon: Icons.mail_outlined,
          label: 'Leaves',
          value: today.pendingLeavesCount.toString(),
          tone: JaikalkiBrand.marigold,
        ),
      ],
    );
  }
}

class _CountTile extends StatelessWidget {
  const _CountTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.tone,
  });
  final IconData icon;
  final String label;
  final String value;
  final Color tone;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: tone.withOpacity(0.08),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: tone.withOpacity(0.4)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: tone, size: 18),
            const SizedBox(height: 6),
            Text(value,
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: tone,
                )),
            Text(label,
                style: const TextStyle(
                  fontSize: 11,
                  color: JaikalkiBrand.textSecondary,
                  fontWeight: FontWeight.w600,
                )),
          ],
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Text(
        text.toUpperCase(),
        style: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          letterSpacing: 0.6,
          color: JaikalkiBrand.textSecondary,
        ),
      );
}

class _IdCardTile extends StatefulWidget {
  const _IdCardTile({required this.profile});
  final TeacherProfile profile;

  @override
  State<_IdCardTile> createState() => _IdCardTileState();
}

class _IdCardTileState extends State<_IdCardTile> {
  bool _downloading = false;

  Future<void> _download() async {
    setState(() => _downloading = true);
    final messenger = ScaffoldMessenger.of(context);
    try {
      final dir = await getTemporaryDirectory();
      final safe = widget.profile.employeeNo
          .replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');
      final path = '${dir.path}/teacher_id_$safe.pdf';
      await locator<TeacherRepository>().downloadIdCard(path);
      await OpenFilex.open(path);
    } catch (e) {
      messenger.showSnackBar(
        SnackBar(content: Text('Could not open ID card: $e')),
      );
    } finally {
      if (mounted) setState(() => _downloading = false);
    }
  }

  void _preview() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Scaffold(
          appBar: AppBar(title: const Text('ID card')),
          body: TeacherIdCardPreview(
            profile: widget.profile,
            schoolName:
                widget.profile.designation != null ? 'Jaikalki' : 'Jaikalki',
          ),
        ),
      ),
    );
  }

  String _initials(String name) {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts[0].isEmpty) return '?';
    if (parts.length == 1) return parts[0][0].toUpperCase();
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.profile;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [JaikalkiBrand.tealDark, Color(0xFF0B5C57)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: JaikalkiBrand.tealDark.withOpacity(0.18),
            blurRadius: 12, offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 26,
                backgroundColor: Colors.white.withOpacity(0.18),
                foregroundColor: Colors.white,
                child: Text(
                  _initials(p.fullName),
                  style: const TextStyle(
                    fontSize: 16, fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(p.fullName,
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 15, fontWeight: FontWeight.w700,
                        )),
                    Text(
                      [p.designation, p.employeeNo]
                          .where((s) => s != null && s!.isNotEmpty)
                          .join(' · '),
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.85),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.badge_outlined,
                  color: Colors.white, size: 22),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _preview,
                  icon: const Icon(Icons.visibility_outlined),
                  label: const Text('Preview'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white,
                    side: BorderSide(color: Colors.white.withOpacity(0.6)),
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: _downloading ? null : _download,
                  icon: _downloading
                      ? const SizedBox(
                          width: 14, height: 14,
                          child: CircularProgressIndicator(
                            strokeWidth: 2, color: JaikalkiBrand.tealDark,
                          ),
                        )
                      : const Icon(Icons.download_outlined),
                  label: const Text('Download PDF'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: JaikalkiBrand.tealDark,
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _PeriodCard extends StatelessWidget {
  const _PeriodCard({required this.period});
  final TodayPeriod period;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => TakeAttendancePage(
              sectionId: period.sectionId,
              sectionLabel: period.sectionLabel,
            ),
          ),
        ),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: JaikalkiBrand.warmWhite,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: JaikalkiBrand.saffronPale),
          ),
          child: Row(
            children: [
              Container(
                width: 44, height: 44,
                decoration: BoxDecoration(
                  color: JaikalkiBrand.saffronPale,
                  borderRadius: BorderRadius.circular(10),
                ),
                alignment: Alignment.center,
                child: Text('${period.periodNumber}',
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      color: JaikalkiBrand.saffronDark,
                    )),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(period.subjectName ?? 'Free',
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: JaikalkiBrand.indigoDark,
                        )),
                    Text(
                      [period.sectionLabel, period.room]
                          .where((s) => s != null && s!.isNotEmpty)
                          .join(' · '),
                      style: const TextStyle(
                        fontSize: 12,
                        color: JaikalkiBrand.textSecondary,
                      ),
                    ),
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
