import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
import 'student_drill_page.dart';

/// Take-attendance flow for one section. Loads the current day's roll
/// (defaults to "all present" server-side for any student without a row
/// yet), lets the teacher tap a chip per student to flip the status,
/// then POSTs the whole batch back.
class TakeAttendancePage extends StatefulWidget {
  const TakeAttendancePage({
    super.key,
    required this.sectionId,
    required this.sectionLabel,
  });

  final int sectionId;
  final String sectionLabel;

  @override
  State<TakeAttendancePage> createState() => _TakeAttendancePageState();
}

class _TakeAttendancePageState extends State<TakeAttendancePage> {
  late Future<SectionRoll> _future;
  // Local edits keyed by student_id. Saved on Save.
  final Map<int, String> _statusOverrides = {};
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _future = locator<TeacherRepository>().attendanceFor(widget.sectionId);
  }

  Future<void> _reload() async {
    setState(() {
      _statusOverrides.clear();
      _error = null;
      _future = locator<TeacherRepository>().attendanceFor(widget.sectionId);
    });
    await _future;
  }

  Future<void> _save(SectionRoll roll) async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    final entries = [
      for (final s in roll.students)
        MarkEntry(
          studentId: s.studentId,
          status: _statusOverrides[s.studentId] ?? s.status,
        ),
    ];
    try {
      final updated = await locator<TeacherRepository>().markAttendance(
        sectionId: widget.sectionId,
        date: roll.date,
        entries: entries,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Attendance saved for ${entries.length} students'),
        ),
      );
      setState(() {
        _future = Future.value(updated);
        _statusOverrides.clear();
      });
    } catch (e) {
      setState(() => _error = 'Save failed: $e');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.sectionLabel),
        actions: [
          IconButton(
            onPressed: _submitting ? null : _reload,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: FutureBuilder<SectionRoll>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Padding(
              padding: const EdgeInsets.all(24),
              child: Text(
                'Could not load roster: ${snap.error}',
                style: const TextStyle(color: Color(0xFFD32F2F)),
              ),
            );
          }
          final roll = snap.data!;
          return Column(
            children: [
              _Header(
                roll: roll,
                overrides: _statusOverrides,
                onMarkAllPresent: () => setState(() {
                  for (final s in roll.students) {
                    _statusOverrides[s.studentId] = 'present';
                  }
                }),
              ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Text(_error!,
                      style: const TextStyle(color: Color(0xFFD32F2F))),
                ),
              Expanded(
                child: ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                  itemCount: roll.students.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 6),
                  itemBuilder: (_, i) => _StudentRow(
                    student: roll.students[i],
                    selected: _statusOverrides[roll.students[i].studentId]
                        ?? roll.students[i].status,
                    onChange: (status) => setState(() {
                      _statusOverrides[roll.students[i].studentId] = status;
                    }),
                  ),
                ),
              ),
              SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _submitting ? null : () => _save(roll),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: JaikalkiBrand.saffron,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      child: _submitting
                          ? const SizedBox(
                              height: 18, width: 18,
                              child: CircularProgressIndicator(
                                color: Colors.white, strokeWidth: 2,
                              ),
                            )
                          : Text(
                              _statusOverrides.isEmpty
                                  ? 'Save attendance'
                                  : 'Save ${_statusOverrides.length} changes',
                              style: const TextStyle(
                                fontSize: 15, fontWeight: FontWeight.w700,
                              ),
                            ),
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({
    required this.roll,
    required this.overrides,
    required this.onMarkAllPresent,
  });
  final SectionRoll roll;
  final Map<int, String> overrides;
  final VoidCallback onMarkAllPresent;

  int _count(String code) {
    var n = 0;
    for (final s in roll.students) {
      final eff = overrides[s.studentId] ?? s.status;
      if (eff == code) n++;
    }
    return n;
  }

  @override
  Widget build(BuildContext context) {
    final present = _count('present');
    final absent = _count('absent');
    final late = _count('late');
    return Container(
      padding: const EdgeInsets.all(14),
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(roll.date,
              style: const TextStyle(
                fontSize: 12, color: JaikalkiBrand.textSecondary,
                fontWeight: FontWeight.w600,
              )),
          const SizedBox(height: 6),
          Row(
            children: [
              _Pill(label: 'Present', n: present, tone: JaikalkiBrand.teal),
              const SizedBox(width: 6),
              _Pill(label: 'Absent', n: absent, tone: const Color(0xFFD32F2F)),
              const SizedBox(width: 6),
              _Pill(label: 'Late', n: late, tone: JaikalkiBrand.marigold),
              const Spacer(),
              TextButton.icon(
                onPressed: onMarkAllPresent,
                icon: const Icon(Icons.done_all, size: 16),
                label: const Text('All present',
                    style: TextStyle(fontSize: 12)),
                style: TextButton.styleFrom(
                  foregroundColor: JaikalkiBrand.tealDark,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({required this.label, required this.n, required this.tone});
  final String label;
  final int n;
  final Color tone;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: tone.withOpacity(0.15),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('$n',
                style: TextStyle(
                  fontWeight: FontWeight.w800, color: tone, fontSize: 13,
                )),
            const SizedBox(width: 4),
            Text(label,
                style: TextStyle(
                  fontSize: 11, fontWeight: FontWeight.w600, color: tone,
                )),
          ],
        ),
      );
}

class _StudentRow extends StatelessWidget {
  const _StudentRow({
    required this.student,
    required this.selected,
    required this.onChange,
  });
  final StudentRollEntry student;
  final String selected;
  final ValueChanged<String> onChange;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      child: Row(
        children: [
          InkWell(
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => StudentDrillPage(studentId: student.studentId),
              ),
            ),
            borderRadius: BorderRadius.circular(16),
            child: CircleAvatar(
              radius: 16,
              backgroundColor: JaikalkiBrand.saffronPale,
              foregroundColor: JaikalkiBrand.saffronDark,
              child: Text(
                student.rollNo ?? _initials(student.fullName),
                style: const TextStyle(
                  fontSize: 11, fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: InkWell(
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => StudentDrillPage(studentId: student.studentId),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(student.fullName,
                      style: const TextStyle(
                        fontSize: 14, fontWeight: FontWeight.w700,
                        color: JaikalkiBrand.indigoDark,
                      ),
                      maxLines: 1, overflow: TextOverflow.ellipsis),
                  Text(student.admissionNumber,
                      style: const TextStyle(
                        fontSize: 11, color: JaikalkiBrand.textSecondary,
                      )),
                ],
              ),
            ),
          ),
          Wrap(
            spacing: 4,
            children: [
              _StatusChip(
                code: 'present', label: 'P', tone: JaikalkiBrand.teal,
                selected: selected == 'present',
                onTap: () => onChange('present'),
              ),
              _StatusChip(
                code: 'absent', label: 'A', tone: const Color(0xFFD32F2F),
                selected: selected == 'absent',
                onTap: () => onChange('absent'),
              ),
              _StatusChip(
                code: 'late', label: 'L', tone: JaikalkiBrand.marigold,
                selected: selected == 'late',
                onTap: () => onChange('late'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _initials(String n) {
    final parts = n.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts[0].isEmpty) return '?';
    if (parts.length == 1) return parts[0][0].toUpperCase();
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.code,
    required this.label,
    required this.tone,
    required this.selected,
    required this.onTap,
  });
  final String code;
  final String label;
  final Color tone;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        width: 30, height: 30,
        decoration: BoxDecoration(
          color: selected ? tone : tone.withOpacity(0.12),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: tone, width: selected ? 0 : 1),
        ),
        alignment: Alignment.center,
        child: Text(
          label,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w800,
            color: selected ? Colors.white : tone,
          ),
        ),
      ),
    );
  }
}
