import 'package:flutter/material.dart';

import '../../api/parent_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Holidays + upcoming events feed. Backend exposes these as two flat
/// lists scoped to a ±day window; we interleave them client-side into a
/// single chronological timeline so parents see the school calendar
/// without having to flip between two tabs.
class CalendarPage extends StatefulWidget {
  const CalendarPage({super.key});

  @override
  State<CalendarPage> createState() => _CalendarPageState();
}

class _CalendarPageState extends State<CalendarPage>
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
    final repo = locator<ParentRepository>();
    _holidays = repo.holidays();
    _events = repo.events();
  }

  @override
  void dispose() {
    _tab.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Material(
          color: Colors.transparent,
          child: TabBar(
            controller: _tab,
            labelColor: JaikalkiBrand.indigoDark,
            unselectedLabelColor: JaikalkiBrand.textSecondary,
            indicatorColor: JaikalkiBrand.saffron,
            tabs: const [
              Tab(icon: Icon(Icons.event_outlined), text: 'Events'),
              Tab(icon: Icon(Icons.beach_access_outlined), text: 'Holidays'),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
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
        ),
      ],
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
        return RefreshIndicator(
          onRefresh: onRefresh,
          child: rows.isEmpty
              ? ListView(children: const [
                  SizedBox(height: 80),
                  Center(
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: Text('No upcoming events.',
                          style: TextStyle(color: JaikalkiBrand.textSecondary)),
                    ),
                  ),
                ])
              : ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
                  itemCount: rows.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (_, i) => _EventCard(event: rows[i]),
                ),
        );
      },
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
        return RefreshIndicator(
          onRefresh: onRefresh,
          child: rows.isEmpty
              ? ListView(children: const [
                  SizedBox(height: 80),
                  Center(
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: Text('No holidays in this window.',
                          style: TextStyle(color: JaikalkiBrand.textSecondary)),
                    ),
                  ),
                ])
              : ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
                  itemCount: rows.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (_, i) => _HolidayCard(holiday: rows[i]),
                ),
        );
      },
    );
  }
}

class _EventCard extends StatelessWidget {
  const _EventCard({required this.event});
  final SchoolEvent event;

  Color _toneFor(String kind) {
    switch (kind) {
      case 'exam':
        return const Color(0xFFD32F2F);
      case 'sports':
        return JaikalkiBrand.teal;
      case 'cultural':
        return JaikalkiBrand.marigold;
      case 'parent_teacher':
        return JaikalkiBrand.indigoDark;
      case 'holiday':
        return JaikalkiBrand.saffron;
      default:
        return JaikalkiBrand.saffron;
    }
  }

  String _fmtDate(String iso) {
    if (iso.isEmpty) return '';
    final dt = DateTime.tryParse(iso);
    if (dt == null) return iso;
    return '${dt.day.toString().padLeft(2, '0')} ${_month(dt.month)} ${dt.year}';
  }

  String _fmtTime(String iso) {
    final dt = DateTime.tryParse(iso);
    if (dt == null) return '';
    return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  }

  static const _months = [
    'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec',
  ];
  String _month(int m) => _months[(m - 1).clamp(0, 11)];

  @override
  Widget build(BuildContext context) {
    final tone = _toneFor(event.kind);
    return Card(
      elevation: 0,
      color: JaikalkiBrand.warmWhite,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(color: tone.withOpacity(0.3)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: tone.withOpacity(0.15),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Column(
                children: [
                  Text(_fmtDate(event.startsAt).split(' ').take(2).join(' '),
                      style: TextStyle(
                        color: tone, fontWeight: FontWeight.w700, fontSize: 12,
                      )),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(event.title,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        color: JaikalkiBrand.indigoDark,
                      )),
                  const SizedBox(height: 4),
                  Wrap(
                    spacing: 8,
                    children: [
                      _chip(event.kind.replaceAll('_', ' '), tone),
                      if (!event.isAllDay)
                        _chip(_fmtTime(event.startsAt), JaikalkiBrand.textSecondary),
                    ],
                  ),
                  if (event.description != null && event.description!.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(event.description!,
                          style: const TextStyle(
                            fontSize: 12,
                            color: JaikalkiBrand.textSecondary,
                          )),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _chip(String text, Color tone) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: tone.withOpacity(0.15),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(text,
            style: TextStyle(
              fontSize: 11, fontWeight: FontWeight.w700, color: tone,
            )),
      );
}

class _HolidayCard extends StatelessWidget {
  const _HolidayCard({required this.holiday});
  final Holiday holiday;

  Color _toneFor(String kind) {
    switch (kind) {
      case 'vacation':
        return JaikalkiBrand.teal;
      case 'school':
        return JaikalkiBrand.indigoDark;
      case 'optional':
        return JaikalkiBrand.textSecondary;
      default:
        return JaikalkiBrand.saffron;
    }
  }

  @override
  Widget build(BuildContext context) {
    final tone = _toneFor(holiday.kind);
    return Card(
      elevation: 0,
      color: JaikalkiBrand.warmWhite,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(color: tone.withOpacity(0.3)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: tone.withOpacity(0.15),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(Icons.beach_access_outlined, color: tone),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(holiday.name,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        color: JaikalkiBrand.indigoDark,
                      )),
                  const SizedBox(height: 2),
                  Text('${holiday.date} · ${holiday.kind}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: JaikalkiBrand.textSecondary,
                      )),
                  if (holiday.description != null &&
                      holiday.description!.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(holiday.description!,
                          style: const TextStyle(
                            fontSize: 12,
                            color: JaikalkiBrand.textSecondary,
                          )),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
