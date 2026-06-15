import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Two-tab feed of upcoming holidays + school events for the teacher.
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

  @override
  void initState() {
    super.initState();
    _tab = TabController(length: 2, vsync: this);
    _reload();
  }

  void _reload() {
    final r = locator<TeacherRepository>();
    _holidays = r.holidays();
    _events = r.events();
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
          return RefreshIndicator(
            onRefresh: onRefresh,
            child: ListView(children: const [
              SizedBox(height: 80),
              Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text('No events.',
                      style: TextStyle(color: JaikalkiBrand.textSecondary)),
                ),
              ),
            ]),
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
          return RefreshIndicator(
            onRefresh: onRefresh,
            child: ListView(children: const [
              SizedBox(height: 80),
              Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text('No holidays in window.',
                      style: TextStyle(color: JaikalkiBrand.textSecondary)),
                ),
              ),
            ]),
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
