import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Three-tab feed of upcoming events, holidays, and published exams
/// for the teacher. The Exams tab pairs with the "Upcoming exams"
/// counter on the Today screen so the dashboard count and the calendar
/// agree.
class TeacherCalendarPage extends StatefulWidget {
  const TeacherCalendarPage({super.key});

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
    _tab = TabController(length: 3, vsync: this);
    _reload();
  }

  void _reload() {
    final r = locator<TeacherRepository>();
    _holidays = r.holidays();
    _events = r.events();
    _exams = r.exams();
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
        bottom: TabBar(controller: _tab, tabs: const [
          Tab(text: 'Events'),
          Tab(text: 'Exams'),
          Tab(text: 'Holidays'),
        ]),
      ),
      body: TabBarView(
        controller: _tab,
        children: [
          _EventsTab(future: _events, onRefresh: () async {
            setState(_reload);
            await _events;
          }),
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
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (_, i) => _row(rows[i]),
          ),
        );
      },
    );
  }

  Widget _row(ExamCalendarRow e) {
    final tone = _toneFor(e.status);
    final hasStart = e.startDate != null && e.startDate!.isNotEmpty;
    final hasEnd = e.endDate != null && e.endDate!.isNotEmpty;
    final dateLine = hasStart && hasEnd && e.startDate != e.endDate
        ? '${e.startDate} → ${e.endDate}'
        : (hasStart ? e.startDate! : 'Date TBD');
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: tone.withOpacity(0.4)),
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
                  color: tone.withOpacity(0.13),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(Icons.assignment_outlined,
                    color: tone, size: 20),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(e.name,
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          color: JaikalkiBrand.indigoDark,
                        )),
                    Text('${_kindLabel(e.kind)} · $dateLine',
                        style: const TextStyle(
                          fontSize: 11,
                          color: JaikalkiBrand.textSecondary,
                          fontWeight: FontWeight.w600,
                        )),
                  ],
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
                  e.status.toUpperCase(),
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.w800,
                    color: tone,
                  ),
                ),
              ),
            ],
          ),
          if (e.notes != null && e.notes!.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 8, left: 48),
              child: Text(e.notes!,
                  style: const TextStyle(
                    fontSize: 12,
                    color: JaikalkiBrand.textSecondary,
                    height: 1.4,
                  )),
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
