import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
import 'exam_timetable_page.dart';

/// Three-tab feed of upcoming events, holidays, and published exams
/// for the teacher. The Exams tab pairs with the "Upcoming exams"
/// counter on the Today screen so the dashboard count and the calendar
/// agree.
/// Events, exams and holidays. With [staffApi] (non-teaching staff,
/// principal shell) it reads the /v1/staff calendar and has no Exams tab.
class TeacherCalendarPage extends StatefulWidget {
  const TeacherCalendarPage({super.key, this.staffApi = false});

  final bool staffApi;

  @override
  State<TeacherCalendarPage> createState() => _TeacherCalendarPageState();
}

class _TeacherCalendarPageState extends State<TeacherCalendarPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tab;
  Future<List<Holiday>>? _holidays;
  Future<List<SchoolEvent>>? _events;
  Future<List<ExamCalendarRow>>? _exams;

  @override
  void initState() {
    super.initState();
    _tab = TabController(length: widget.staffApi ? 2 : 3, vsync: this);
    _reload();
  }

  void _reload() {
    final r = locator<TeacherRepository>();
    _holidays = r.holidays(staff: widget.staffApi);
    _events = r.events(staff: widget.staffApi);
    if (!widget.staffApi) _exams = r.exams();
  }

  @override
  void dispose() {
    _tab.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Calendar'),
        bottom: TabBar(controller: _tab, tabs: [
          const Tab(text: 'Events'),
          if (!widget.staffApi) const Tab(text: 'Exams'),
          const Tab(text: 'Holidays'),
        ]),
      ),
      body: TabBarView(
        controller: _tab,
        children: [
          _EventsTab(future: _events, onRefresh: () async {
            setState(_reload);
            await _events;
          }),
          if (!widget.staffApi)
            _ExamsTab(future: _exams, onRefresh: () async {
              setState(_reload);
              await _exams;
            }),
          _HolidaysTab(future: _holidays, onRefresh: () async {
            setState(_reload);
            await _holidays;
          }),
        ],
      ),
    );
  }
}

class _EventsTab extends StatelessWidget {
  const _EventsTab({required this.future, required this.onRefresh});
  final Future<List<SchoolEvent>>? future;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<SchoolEvent>>(
      future: future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? const <SchoolEvent>[];
        if (rows.isEmpty) {
          return _EmptyList(text: 'No events.', onRefresh: onRefresh);
        }
        return RefreshIndicator(
          onRefresh: onRefresh,
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            itemCount: rows.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (_, i) => _row(rows[i]),
          ),
        );
      },
    );
  }

  Widget _row(SchoolEvent e) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: JaikalkiBrand.warmWhite,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: JaikalkiBrand.saffronPale),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(e.title,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: JaikalkiBrand.indigoDark,
                )),
            const SizedBox(height: 2),
            Text(e.startsAt.split('T').first,
                style: const TextStyle(
                  fontSize: 11,
                  color: JaikalkiBrand.textSecondary,
                  fontWeight: FontWeight.w600,
                )),
            if (e.description != null && e.description!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(e.description!,
                    style: const TextStyle(
                      fontSize: 12,
                      color: JaikalkiBrand.textSecondary,
                    )),
              ),
          ],
        ),
      );
}

class _ExamsTab extends StatelessWidget {
  const _ExamsTab({required this.future, required this.onRefresh});
  final Future<List<ExamCalendarRow>>? future;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<ExamCalendarRow>>(
      future: future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? const <ExamCalendarRow>[];
        if (rows.isEmpty) {
          return _EmptyList(
            text: 'No exams published in this window.',
            onRefresh: onRefresh,
          );
        }
        return RefreshIndicator(
          onRefresh: onRefresh,
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            itemCount: rows.length,
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemBuilder: (_, i) => _ExamCard(row: rows[i]),
          ),
        );
      },
    );
  }
}

class _ExamCard extends StatelessWidget {
  const _ExamCard({required this.row});
  final ExamCalendarRow row;

  static const _months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ];
  static const _days = [
    'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun',
  ];

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

  Color _toneFor(String status) {
    switch (status) {
      case 'completed':
        return JaikalkiBrand.teal;
      case 'in_progress':
        return JaikalkiBrand.marigold;
      default:
        return JaikalkiBrand.saffron;
    }
  }

  /// Returns ("Mon", "22 Jun") for a given ISO date so the card can
  /// show the day-of-week on top of the date in the date chip.
  ({String day, String date})? _splitDate(String? iso) {
    if (iso == null || iso.isEmpty) return null;
    try {
      final d = DateTime.parse(iso);
      return (
        day: _days[d.weekday - 1],
        date: '${d.day} ${_months[d.month - 1]}',
      );
    } catch (_) {
      return null;
    }
  }

  String _rangeLine() {
    final s = _splitDate(row.startDate);
    final e = _splitDate(row.endDate);
    if (s == null) return 'Date TBD';
    if (e == null || row.startDate == row.endDate) {
      return '${s.day}, ${s.date}';
    }
    return '${s.day}, ${s.date} → ${e.day}, ${e.date}';
  }

  @override
  Widget build(BuildContext context) {
    final tone = _toneFor(row.status);
    final s = _splitDate(row.startDate);
    return Material(
      color: JaikalkiBrand.warmWhite,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => ExamTimetablePage(
              examId: row.id,
              examName: row.name,
            ),
          ),
        ),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: tone.withOpacity(0.4)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _DateChip(
                    day: s?.day ?? 'TBD',
                    date: s?.date ?? '—',
                    tone: tone,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                row.name,
                                style: const TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w700,
                                  color: JaikalkiBrand.indigoDark,
                                ),
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: tone.withOpacity(0.18),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                row.status.toUpperCase(),
                                style: TextStyle(
                                  fontSize: 9,
                                  fontWeight: FontWeight.w800,
                                  color: tone,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _kindLabel(row.kind),
                          style: const TextStyle(
                            fontSize: 11,
                            color: JaikalkiBrand.textSecondary,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.4,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            const Icon(Icons.event_outlined,
                                size: 12,
                                color: JaikalkiBrand.textSecondary),
                            const SizedBox(width: 4),
                            Expanded(
                              child: Text(
                                _rangeLine(),
                                style: const TextStyle(
                                  fontSize: 11,
                                  color: JaikalkiBrand.textSecondary,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              if (row.notes != null && row.notes!.isNotEmpty) ...[
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: JaikalkiBrand.ivory,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    row.notes!,
                    style: const TextStyle(
                      fontSize: 12,
                      color: JaikalkiBrand.textSecondary,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Text(
                    'View timetable',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      color: tone,
                    ),
                  ),
                  const SizedBox(width: 2),
                  Icon(Icons.chevron_right, size: 18, color: tone),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DateChip extends StatelessWidget {
  const _DateChip({
    required this.day,
    required this.date,
    required this.tone,
  });

  final String day;
  final String date;
  final Color tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 60,
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 6),
      decoration: BoxDecoration(
        color: tone.withOpacity(0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: tone.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Text(
            day.toUpperCase(),
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.6,
              color: tone,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            date,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w800,
              color: tone,
              height: 1.05,
            ),
          ),
        ],
      ),
    );
  }
}

class _HolidaysTab extends StatelessWidget {
  const _HolidaysTab({required this.future, required this.onRefresh});
  final Future<List<Holiday>>? future;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Holiday>>(
      future: future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? const <Holiday>[];
        if (rows.isEmpty) {
          return _EmptyList(
            text: 'No holidays in window.',
            onRefresh: onRefresh,
          );
        }
        return RefreshIndicator(
          onRefresh: onRefresh,
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            itemCount: rows.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (_, i) => _row(rows[i]),
          ),
        );
      },
    );
  }

  Widget _row(Holiday h) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: JaikalkiBrand.warmWhite,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: JaikalkiBrand.saffronPale),
        ),
        child: Row(
          children: [
            const Icon(Icons.beach_access_outlined,
                color: JaikalkiBrand.saffron),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(h.name,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        color: JaikalkiBrand.indigoDark,
                      )),
                  Text('${h.date} · ${h.kind}',
                      style: const TextStyle(
                        fontSize: 11,
                        color: JaikalkiBrand.textSecondary,
                      )),
                ],
              ),
            ),
          ],
        ),
      );
}

class _EmptyList extends StatelessWidget {
  const _EmptyList({required this.text, required this.onRefresh});
  final String text;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(children: [
        const SizedBox(height: 80),
        Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(text,
                style: const TextStyle(color: JaikalkiBrand.textSecondary)),
          ),
        ),
      ]),
    );
  }
}
