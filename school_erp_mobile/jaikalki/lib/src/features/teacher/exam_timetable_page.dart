import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Subject-wise schedule for one exam. Renders papers grouped by date
/// so the teacher can scan "what's on Monday → Friday" at a glance,
/// with an "Unscheduled" bucket for papers whose date isn't set yet.
class ExamTimetablePage extends StatefulWidget {
  const ExamTimetablePage({
    super.key,
    required this.examId,
    required this.examName,
  });

  final int examId;
  final String examName;

  @override
  State<ExamTimetablePage> createState() => _ExamTimetablePageState();
}

class _ExamTimetablePageState extends State<ExamTimetablePage> {
  late Future<ExamTimetable> _future;

  static const _months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ];
  static const _days = [
    'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun',
  ];

  @override
  void initState() {
    super.initState();
    _future = locator<TeacherRepository>().examTimetable(widget.examId);
  }

  Future<void> _reload() async {
    setState(() {
      _future = locator<TeacherRepository>().examTimetable(widget.examId);
    });
    await _future;
  }

  String _formatDate(String iso) {
    try {
      final d = DateTime.parse(iso);
      return '${_days[d.weekday - 1]}, ${d.day} ${_months[d.month - 1]}';
    } catch (_) {
      return iso;
    }
  }

  String _formatTime(String? hhmmss) {
    if (hhmmss == null || hhmmss.isEmpty) return '';
    final parts = hhmmss.split(':');
    if (parts.length < 2) return hhmmss;
    final h = int.tryParse(parts[0]) ?? 0;
    final m = parts[1];
    final period = h >= 12 ? 'PM' : 'AM';
    final h12 = ((h + 11) % 12) + 1;
    return '$h12:$m $period';
  }

  Map<String, List<ExamPaper>> _groupByDate(List<ExamPaper> papers) {
    final out = <String, List<ExamPaper>>{};
    for (final p in papers) {
      final key = p.examDate ?? '';
      out.putIfAbsent(key, () => []).add(p);
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.examName)),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: FutureBuilder<ExamTimetable>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return Padding(
                padding: const EdgeInsets.all(24),
                child: Text('Could not load timetable: ${snap.error}',
                    style: const TextStyle(color: Color(0xFFD32F2F))),
              );
            }
            final t = snap.data!;
            if (t.papers.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 80),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No subject-wise schedule yet.\n'
                      'The admin needs to add papers to this exam.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                ),
              ]);
            }
            final byDate = _groupByDate(t.papers);
            final keys = byDate.keys.toList()
              ..sort((a, b) {
                if (a.isEmpty) return 1;
                if (b.isEmpty) return -1;
                return a.compareTo(b);
              });
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              children: [
                _ExamHeader(timetable: t, formatDate: _formatDate),
                const SizedBox(height: 16),
                for (final key in keys) ...[
                  _DateLabel(
                    label: key.isEmpty ? 'Date TBD' : _formatDate(key),
                  ),
                  const SizedBox(height: 8),
                  ...byDate[key]!.map(
                    (p) => Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: _PaperCard(
                        paper: p,
                        startTime: _formatTime(p.startsAt),
                        endTime: _formatTime(p.endsAt),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                ],
              ],
            );
          },
        ),
      ),
    );
  }
}

class _ExamHeader extends StatelessWidget {
  const _ExamHeader({required this.timetable, required this.formatDate});
  final ExamTimetable timetable;
  final String Function(String) formatDate;

  String _kindLabel(String k) {
    switch (k) {
      case 'unit_test': return 'Unit test';
      case 'midterm': return 'Mid-term';
      case 'final': return 'Final';
      case 'quarterly': return 'Quarterly';
      case 'half_yearly': return 'Half-yearly';
      case 'annual': return 'Annual';
      case 'practical': return 'Practical';
      default: return k.replaceAll('_', ' ');
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = timetable.startDate;
    final e = timetable.endDate;
    final dateLine = (s != null && e != null && s != e)
        ? '${formatDate(s)} → ${formatDate(e)}'
        : (s != null ? formatDate(s) : 'Date TBD');
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
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _kindLabel(timetable.examKind).toUpperCase(),
            style: TextStyle(
              fontSize: 10,
              letterSpacing: 1.2,
              fontWeight: FontWeight.w800,
              color: JaikalkiBrand.marigoldPale.withOpacity(0.9),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            timetable.examName,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              const Icon(Icons.event_outlined,
                  color: JaikalkiBrand.marigoldPale, size: 14),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  dateLine,
                  style: TextStyle(
                    color: JaikalkiBrand.marigoldPale.withOpacity(0.95),
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              const Icon(Icons.assignment_outlined,
                  color: JaikalkiBrand.marigoldPale, size: 14),
              const SizedBox(width: 6),
              Text(
                '${timetable.papers.length} paper${timetable.papers.length == 1 ? "" : "s"}',
                style: TextStyle(
                  color: JaikalkiBrand.marigoldPale.withOpacity(0.95),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DateLabel extends StatelessWidget {
  const _DateLabel({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: JaikalkiBrand.saffronPale,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        label,
        style: const TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w800,
          color: JaikalkiBrand.saffronDarker,
          letterSpacing: 0.4,
        ),
      ),
    );
  }
}

class _PaperCard extends StatelessWidget {
  const _PaperCard({
    required this.paper,
    required this.startTime,
    required this.endTime,
  });

  final ExamPaper paper;
  final String startTime;
  final String endTime;

  @override
  Widget build(BuildContext context) {
    final timeLine = [
      if (startTime.isNotEmpty) startTime,
      if (endTime.isNotEmpty) '– $endTime',
    ].join(' ').trim();
    return Container(
      padding: const EdgeInsets.all(12),
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
              Container(
                width: 38, height: 38,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: JaikalkiBrand.teal.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.menu_book_outlined,
                    color: JaikalkiBrand.teal, size: 20),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      paper.subjectName,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        color: JaikalkiBrand.indigoDark,
                      ),
                    ),
                    Text(
                      paper.className,
                      style: const TextStyle(
                        fontSize: 11,
                        color: JaikalkiBrand.textSecondary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              if (paper.maxMarks != null)
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: JaikalkiBrand.marigoldPale,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    '${paper.maxMarks!.toStringAsFixed(0)} marks',
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      color: JaikalkiBrand.indigoDark,
                    ),
                  ),
                ),
            ],
          ),
          if (timeLine.isNotEmpty) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                const SizedBox(width: 48),
                const Icon(Icons.access_time,
                    color: JaikalkiBrand.textSecondary, size: 14),
                const SizedBox(width: 4),
                Text(
                  timeLine,
                  style: const TextStyle(
                    fontSize: 12,
                    color: JaikalkiBrand.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (paper.passingMarks != null) ...[
                  const SizedBox(width: 10),
                  const Icon(Icons.flag_outlined,
                      color: JaikalkiBrand.textSecondary, size: 14),
                  const SizedBox(width: 4),
                  Text(
                    'Pass: ${paper.passingMarks!.toStringAsFixed(0)}',
                    style: const TextStyle(
                      fontSize: 12,
                      color: JaikalkiBrand.textSecondary,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }
}
