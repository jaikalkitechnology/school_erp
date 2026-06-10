import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../api/parent_repository.dart';
import '../../core/attendance_cubit.dart';
import '../../core/children_cubit.dart';
import '../../core/service_locator.dart';
import '../../core/settings_cubit.dart';
import '../../theme/brand.dart';

/// Phase 9 — month calendar with per-day attendance status.
class AttendancePage extends StatefulWidget {
  const AttendancePage({super.key});

  @override
  State<AttendancePage> createState() => _AttendancePageState();
}

class _AttendancePageState extends State<AttendancePage> {
  DateTime _month = DateTime(DateTime.now().year, DateTime.now().month);

  void _loadForSelected() {
    final children = context.read<ChildrenCubit>().state;
    if (children is ChildrenLoaded && children.selectedId != null) {
      context.read<AttendanceCubit>().load(children.selectedId!);
    }
  }

  @override
  void initState() {
    super.initState();
    // Schedule load after first frame so context.read works.
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadForSelected());
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsCubit>().state;
    final s = settings.strings;

    return BlocProvider.value(
      value: locator<AttendanceCubit>(),
      child: BlocListener<ChildrenCubit, ChildrenState>(
        listenWhen: (a, b) =>
            a is ChildrenLoaded &&
            b is ChildrenLoaded &&
            a.selectedId != b.selectedId,
        listener: (context, state) => _loadForSelected(),
        child: Scaffold(
          appBar: AppBar(title: Text(s.tabAttendance)),
          body: BlocBuilder<AttendanceCubit, AttendanceState>(
            builder: (context, state) {
              return RefreshIndicator(
                onRefresh: () async {
                  final children = context.read<ChildrenCubit>().state;
                  if (children is ChildrenLoaded &&
                      children.selectedId != null) {
                    await context
                        .read<AttendanceCubit>()
                        .refresh(children.selectedId!);
                  }
                },
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
                  children: [
                    _MonthHeader(
                      month: _month,
                      onPrev: () => setState(
                        () => _month = DateTime(_month.year, _month.month - 1),
                      ),
                      onNext: () => setState(
                        () => _month = DateTime(_month.year, _month.month + 1),
                      ),
                    ),
                    const SizedBox(height: 12),
                    if (state is AttendanceLoaded)
                      _MonthlySummary(rows: state.rows, month: _month, s: s),
                    const SizedBox(height: 12),
                    if (state is AttendanceLoading)
                      const _LoadingCalendar()
                    else if (state is AttendanceLoaded)
                      _CalendarGrid(rows: state.rows, month: _month)
                    else if (state is AttendanceError)
                      _ErrorBox(message: state.message)
                    else
                      const SizedBox.shrink(),
                    const SizedBox(height: 16),
                    _Legend(s: s),
                  ],
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _MonthHeader extends StatelessWidget {
  const _MonthHeader({required this.month, required this.onPrev, required this.onNext});

  final DateTime month;
  final VoidCallback onPrev;
  final VoidCallback onNext;

  static const _monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        IconButton(
          onPressed: onPrev,
          icon: const Icon(Icons.chevron_left),
        ),
        Expanded(
          child: Center(
            child: Text(
              '${_monthNames[month.month - 1]} ${month.year}',
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: JaikalkiBrand.indigoDark,
              ),
            ),
          ),
        ),
        IconButton(
          onPressed: onNext,
          icon: const Icon(Icons.chevron_right),
        ),
      ],
    );
  }
}

class _MonthlySummary extends StatelessWidget {
  const _MonthlySummary({required this.rows, required this.month, required this.s});

  final List<AttendanceRow> rows;
  final DateTime month;
  final dynamic s;

  @override
  Widget build(BuildContext context) {
    int present = 0, absent = 0, late = 0, halfDay = 0;
    for (final r in rows) {
      final d = DateTime.tryParse(r.date);
      if (d == null) continue;
      if (d.year != month.year || d.month != month.month) continue;
      switch (r.status) {
        case 'present':
          present++;
          break;
        case 'absent':
          absent++;
          break;
        case 'late':
          late++;
          break;
        case 'half_day':
          halfDay++;
          break;
      }
    }
    final total = present + absent + late + halfDay;
    final pct = total == 0
        ? 0
        : ((present + late + 0.5 * halfDay) / total * 100).round();

    return Card(
      color: JaikalkiBrand.warmWhite,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: JaikalkiBrand.saffronPale),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            CircleAvatar(
              radius: 28,
              backgroundColor: pct >= 75
                  ? JaikalkiBrand.tealPale
                  : JaikalkiBrand.saffronPale,
              child: Text(
                '$pct%',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: pct >= 75 ? JaikalkiBrand.tealDark : JaikalkiBrand.saffronDarker,
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(s.attendanceMonthlyPercent,
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        color: JaikalkiBrand.indigoDark,
                      )),
                  const SizedBox(height: 4),
                  Wrap(
                    spacing: 12,
                    children: [
                      _Mini(label: 'P', count: present, color: JaikalkiBrand.teal),
                      _Mini(label: 'A', count: absent, color: const Color(0xFFD32F2F)),
                      _Mini(label: 'L', count: late, color: JaikalkiBrand.marigold),
                      _Mini(label: '½', count: halfDay, color: JaikalkiBrand.saffron),
                    ],
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

class _Mini extends StatelessWidget {
  const _Mini({required this.label, required this.count, required this.color});

  final String label;
  final int count;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 4),
        Text('$label $count',
            style: const TextStyle(fontSize: 12, color: JaikalkiBrand.textSecondary)),
      ],
    );
  }
}

class _CalendarGrid extends StatelessWidget {
  const _CalendarGrid({required this.rows, required this.month});

  final List<AttendanceRow> rows;
  final DateTime month;

  Color _statusColor(String? status) {
    switch (status) {
      case 'present':
        return JaikalkiBrand.teal;
      case 'absent':
        return const Color(0xFFD32F2F);
      case 'late':
        return JaikalkiBrand.marigold;
      case 'half_day':
        return JaikalkiBrand.saffron;
      case 'leave':
        return JaikalkiBrand.indigo;
      default:
        return Colors.transparent;
    }
  }

  @override
  Widget build(BuildContext context) {
    final firstDay = DateTime(month.year, month.month, 1);
    final daysInMonth = DateTime(month.year, month.month + 1, 0).day;
    final leadingBlanks = firstDay.weekday % 7; // 0..6 (Sun=0)

    final byDay = <int, String>{};
    for (final r in rows) {
      final d = DateTime.tryParse(r.date);
      if (d != null && d.year == month.year && d.month == month.month) {
        byDay[d.day] = r.status;
      }
    }

    const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    return Column(
      children: [
        Row(
          children: dayLabels
              .map((d) => Expanded(
                    child: Center(
                      child: Text(d,
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: JaikalkiBrand.textSecondary,
                          )),
                    ),
                  ))
              .toList(),
        ),
        const SizedBox(height: 6),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 7,
            mainAxisSpacing: 6,
            crossAxisSpacing: 6,
          ),
          itemCount: leadingBlanks + daysInMonth,
          itemBuilder: (context, i) {
            if (i < leadingBlanks) return const SizedBox.shrink();
            final day = i - leadingBlanks + 1;
            final status = byDay[day];
            final color = _statusColor(status);
            return Container(
              decoration: BoxDecoration(
                color: status == null ? Colors.transparent : color.withOpacity(0.15),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: status == null ? JaikalkiBrand.saffronPale : color,
                  width: status == null ? 0.5 : 1.2,
                ),
              ),
              alignment: Alignment.center,
              child: Text('$day',
                  style: TextStyle(
                    fontWeight: status == null ? FontWeight.w400 : FontWeight.w700,
                    color: status == null ? JaikalkiBrand.textSecondary : color,
                  )),
            );
          },
        ),
      ],
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend({required this.s});
  final dynamic s;

  @override
  Widget build(BuildContext context) {
    Widget chip(String label, Color color) => Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: color.withOpacity(0.15),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: color, width: 0.8),
          ),
          child: Text(label,
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: color)),
        );

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        chip(s.statusPresent, JaikalkiBrand.teal),
        chip(s.statusAbsent, const Color(0xFFD32F2F)),
        chip(s.statusLate, JaikalkiBrand.marigold),
        chip(s.statusHalfDay, JaikalkiBrand.saffron),
        chip(s.statusLeave, JaikalkiBrand.indigo),
      ],
    );
  }
}

class _LoadingCalendar extends StatelessWidget {
  const _LoadingCalendar();

  @override
  Widget build(BuildContext context) {
    return const SizedBox(
      height: 280,
      child: Center(child: CircularProgressIndicator()),
    );
  }
}

class _ErrorBox extends StatelessWidget {
  const _ErrorBox({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0x1AD32F2F),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(message,
          style: const TextStyle(color: Color(0xFFD32F2F), fontSize: 13)),
    );
  }
}
