import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../api/parent_repository.dart';
import '../../core/attendance_cubit.dart';
import '../../core/children_cubit.dart';
import '../../core/service_locator.dart';
import '../../core/settings_cubit.dart';
import '../../theme/brand.dart';

/// Phase 9 + parent-app P0 additions.
///
/// Layout (top → bottom):
///   ┌────────────────────────────────────────────────────────┐
///   │ Today's status card                                    │  ←  NEW
///   │ ⚠ 75% warning banner (only if < 80% YTD)               │  ←  NEW
///   │ Month picker [<]  May 2026  [>]                         │
///   │ Monthly %  ↑ 4.2% vs last month                        │  ←  NEW delta chip
///   │ Day calendar                                           │
///   │ 30-day trend line                                       │  ←  NEW
///   │ Legend                                                  │
///   └────────────────────────────────────────────────────────┘
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
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadForSelected());
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsCubit>().state;
    final s = settings.strings;

    return MultiBlocProvider(
      providers: [
        BlocProvider.value(value: locator<ChildrenCubit>()),
        BlocProvider.value(value: locator<AttendanceCubit>()),
      ],
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
                    if (state is AttendanceLoaded) ...[
                      _TodayCard(rows: state.rows, s: s),
                      const SizedBox(height: 12),
                      if (state.timetable != null &&
                          state.timetable!.hasData) ...[
                        _TodayScheduleCard(timetable: state.timetable!),
                        const SizedBox(height: 12),
                      ],
                      _ThresholdBanner(rows: state.rows, s: s),
                      if (state.classAverage != null &&
                          state.classAverage!.isMeaningful)
                        _ClassAverageCard(avg: state.classAverage!),
                      if (state.classAverage != null &&
                          state.classAverage!.isMeaningful)
                        const SizedBox(height: 12),
                    ],
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
                    const SizedBox(height: 18),
                    if (state is AttendanceLoaded)
                      _TrendLine(rows: state.rows, s: s),
                    if (state is AttendanceLoaded &&
                        state.bySubject != null) ...[
                      const SizedBox(height: 16),
                      _SubjectBreakdown(report: state.bySubject!),
                    ],
                    if (state is AttendanceLoaded &&
                        state.timetable != null &&
                        state.timetable!.hasData) ...[
                      const SizedBox(height: 16),
                      _WeeklyTimetable(timetable: state.timetable!),
                    ],
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

// ---- Today's status card --------------------------------------------------

class _TodayCard extends StatelessWidget {
  const _TodayCard({required this.rows, required this.s});

  final List<AttendanceRow> rows;
  final dynamic s;

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now();
    final todayKey = _ymd(today);
    AttendanceRow? row;
    for (final r in rows) {
      if (r.date == todayKey) {
        row = r;
        break;
      }
    }
    final tone = row == null
        ? JaikalkiBrand.marigoldPale
        : _statusToneFor(row.status).withOpacity(0.12);
    final accent = row == null
        ? JaikalkiBrand.marigold
        : _statusToneFor(row.status);
    final label = row == null
        ? 'Roll call not done yet'
        : _statusLabel(row.status, s);
    final icon = row == null
        ? Icons.access_time_rounded
        : _statusIcon(row.status);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: tone,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: accent, width: 1.2),
      ),
      child: Row(
        children: [
          Container(
            width: 48, height: 48,
            decoration: BoxDecoration(
              color: accent,
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: Colors.white),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Today, ${_humanDay(today)}',
                  style: const TextStyle(
                    fontSize: 12,
                    color: JaikalkiBrand.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: accent,
                  ),
                ),
                if (row != null && row.markedByName != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Marked by ${row.markedByName!}'
                    '${row.markedAt != null ? " at ${_humanTime(row.markedAt!)}" : ""}',
                    style: const TextStyle(
                      fontSize: 12,
                      color: JaikalkiBrand.textSecondary,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---- 75% warning banner ---------------------------------------------------

class _ThresholdBanner extends StatelessWidget {
  const _ThresholdBanner({required this.rows, required this.s});

  final List<AttendanceRow> rows;
  final dynamic s;

  @override
  Widget build(BuildContext context) {
    int present = 0, late = 0, half = 0, absent = 0;
    for (final r in rows) {
      switch (r.status) {
        case 'present':
          present++;
          break;
        case 'late':
          late++;
          break;
        case 'half_day':
          half++;
          break;
        case 'absent':
          absent++;
          break;
      }
    }
    final total = present + late + half + absent;
    if (total == 0) return const SizedBox.shrink();
    final pct = (present + late + 0.5 * half) / total * 100;

    // Only show when within 5 points of the regulatory cliff or below it.
    if (pct >= 80) return const SizedBox.shrink();

    final isBelow = pct < 75;
    // Days the kid can still afford to be absent while staying ≥ 75%.
    // Solve: (present + late + 0.5*half) / (total + x) ≥ 0.75
    //   -> x ≤ (present + late + 0.5*half) / 0.75 - total
    final allowed =
        ((present + late + 0.5 * half) / 0.75 - total).floor();

    final tone = isBelow ? const Color(0xFFD32F2F) : JaikalkiBrand.saffron;
    final body = isBelow
        ? 'Already below 75%. Talk to the class teacher before the exam window.'
        : (allowed > 0
            ? 'You can afford $allowed more absence${allowed == 1 ? "" : "s"} this term and stay above 75%.'
            : 'One more absence drops below the 75% exam cutoff.');

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: tone.withOpacity(0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: tone, width: 1.2),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.warning_amber_rounded, color: tone, size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Attendance is ${pct.toStringAsFixed(1)}%.',
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                    color: tone,
                  ),
                ),
                const SizedBox(height: 4),
                Text(body, style: const TextStyle(fontSize: 12, height: 1.4)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---- Month header ---------------------------------------------------------

class _MonthHeader extends StatelessWidget {
  const _MonthHeader(
      {required this.month, required this.onPrev, required this.onNext});

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
        IconButton(onPressed: onPrev, icon: const Icon(Icons.chevron_left)),
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
        IconButton(onPressed: onNext, icon: const Icon(Icons.chevron_right)),
      ],
    );
  }
}

// ---- Monthly summary (% + delta chip + counts) ---------------------------

class _MonthlySummary extends StatelessWidget {
  const _MonthlySummary(
      {required this.rows, required this.month, required this.s});

  final List<AttendanceRow> rows;
  final DateTime month;
  final dynamic s;

  ({int p, int a, int l, int h, int total, double pct}) _calc(DateTime m) {
    int present = 0, absent = 0, late = 0, half = 0;
    for (final r in rows) {
      final d = DateTime.tryParse(r.date);
      if (d == null) continue;
      if (d.year != m.year || d.month != m.month) continue;
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
          half++;
          break;
      }
    }
    final total = present + absent + late + half;
    final pct =
        total == 0 ? 0.0 : ((present + late + 0.5 * half) / total * 100);
    return (p: present, a: absent, l: late, h: half, total: total, pct: pct);
  }

  @override
  Widget build(BuildContext context) {
    final current = _calc(month);
    final prevMonth = DateTime(month.year, month.month - 1);
    final previous = _calc(prevMonth);
    final pctInt = current.pct.round();

    double? delta;
    if (previous.total > 0) {
      delta = current.pct - previous.pct;
    }

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
              backgroundColor: pctInt >= 75
                  ? JaikalkiBrand.tealPale
                  : JaikalkiBrand.saffronPale,
              child: Text(
                '$pctInt%',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: pctInt >= 75
                      ? JaikalkiBrand.tealDark
                      : JaikalkiBrand.saffronDarker,
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(s.attendanceMonthlyPercent,
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            color: JaikalkiBrand.indigoDark,
                          )),
                      if (delta != null) ...[
                        const SizedBox(width: 8),
                        _DeltaChip(delta: delta),
                      ],
                    ],
                  ),
                  const SizedBox(height: 4),
                  Wrap(
                    spacing: 12,
                    children: [
                      _Mini(
                          label: 'P',
                          count: current.p,
                          color: JaikalkiBrand.teal),
                      _Mini(
                          label: 'A',
                          count: current.a,
                          color: const Color(0xFFD32F2F)),
                      _Mini(
                          label: 'L',
                          count: current.l,
                          color: JaikalkiBrand.marigold),
                      _Mini(
                          label: '½',
                          count: current.h,
                          color: JaikalkiBrand.saffron),
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

class _DeltaChip extends StatelessWidget {
  const _DeltaChip({required this.delta});
  final double delta;

  @override
  Widget build(BuildContext context) {
    final positive = delta >= 0;
    final color = positive ? JaikalkiBrand.tealDark : const Color(0xFFD32F2F);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(positive ? Icons.trending_up : Icons.trending_down,
              size: 12, color: color),
          const SizedBox(width: 3),
          Text('${positive ? "+" : ""}${delta.toStringAsFixed(1)}%',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: color,
              )),
        ],
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
            style: const TextStyle(
              fontSize: 12,
              color: JaikalkiBrand.textSecondary,
            )),
      ],
    );
  }
}

// ---- Calendar grid with tap-to-detail ------------------------------------

class _CalendarGrid extends StatelessWidget {
  const _CalendarGrid({required this.rows, required this.month});

  final List<AttendanceRow> rows;
  final DateTime month;

  @override
  Widget build(BuildContext context) {
    final firstDay = DateTime(month.year, month.month, 1);
    final daysInMonth = DateTime(month.year, month.month + 1, 0).day;
    final leadingBlanks = firstDay.weekday % 7;

    final byDay = <int, AttendanceRow>{};
    for (final r in rows) {
      final d = DateTime.tryParse(r.date);
      if (d != null && d.year == month.year && d.month == month.month) {
        byDay[d.day] = r;
      }
    }

    const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    return Column(
      children: [
        Row(
          children: dayLabels
              .map((d) => Expanded(
                    child: Center(
                      child: Text(
                        d,
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: JaikalkiBrand.textSecondary,
                        ),
                      ),
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
            final row = byDay[day];
            final color = row == null
                ? Colors.transparent
                : _statusToneFor(row.status);
            return InkWell(
              borderRadius: BorderRadius.circular(10),
              onTap: row == null
                  ? null
                  : () => _showDayDetail(
                      context, DateTime(month.year, month.month, day), row),
              child: Container(
                decoration: BoxDecoration(
                  color: row == null
                      ? Colors.transparent
                      : color.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: row == null ? JaikalkiBrand.saffronPale : color,
                    width: row == null ? 0.5 : 1.2,
                  ),
                ),
                alignment: Alignment.center,
                child: Text('$day',
                    style: TextStyle(
                      fontWeight: row == null
                          ? FontWeight.w400
                          : FontWeight.w700,
                      color: row == null
                          ? JaikalkiBrand.textSecondary
                          : color,
                    )),
              ),
            );
          },
        ),
      ],
    );
  }

  void _showDayDetail(BuildContext context, DateTime date, AttendanceRow row) {
    final s = context.read<SettingsCubit>().state.strings;
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: JaikalkiBrand.warmWhite,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        final color = _statusToneFor(row.status);
        return Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(_statusIcon(row.status), color: color, size: 24),
                  const SizedBox(width: 10),
                  Text(_humanDay(date),
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 16,
                        color: JaikalkiBrand.indigoDark,
                      )),
                ],
              ),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: color.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(_statusLabel(row.status, s),
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: color,
                    )),
              ),
              const SizedBox(height: 14),
              if (row.markedByName != null)
                _kv('Marked by', row.markedByName!),
              if (row.markedAt != null)
                _kv('At', _humanTime(row.markedAt!)),
              if (row.period != 'day')
                _kv('Period', row.period),
              if (row.remarks != null && row.remarks!.isNotEmpty)
                _kv('Remark', row.remarks!),
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: const Text('Close'),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

Widget _kv(String k, String v) => Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(k,
                style: const TextStyle(
                  fontSize: 12,
                  color: JaikalkiBrand.textSecondary,
                )),
          ),
          Expanded(
            child: Text(v,
                style: const TextStyle(
                  fontSize: 13,
                  color: JaikalkiBrand.indigoDark,
                  fontWeight: FontWeight.w500,
                )),
          ),
        ],
      ),
    );

// ---- 30-day trend line ---------------------------------------------------

class _TrendLine extends StatelessWidget {
  const _TrendLine({required this.rows, required this.s});

  final List<AttendanceRow> rows;
  final dynamic s;

  List<FlSpot> _spots() {
    // Compute a 7-day rolling % over the last 30 days.
    final today = DateTime.now();
    final start = DateTime(today.year, today.month, today.day)
        .subtract(const Duration(days: 29));
    final byDay = <String, AttendanceRow>{};
    for (final r in rows) {
      byDay[r.date] = r;
    }
    final spots = <FlSpot>[];
    for (int i = 0; i < 30; i++) {
      final d = start.add(Duration(days: i));
      // Rolling 7-day window ending on this day.
      int p = 0, l = 0, h = 0, total = 0;
      for (int j = -6; j <= 0; j++) {
        final dd = d.add(Duration(days: j));
        final r = byDay[_ymd(dd)];
        if (r == null) continue;
        total++;
        switch (r.status) {
          case 'present':
            p++;
            break;
          case 'late':
            l++;
            break;
          case 'half_day':
            h++;
            break;
        }
      }
      final pct = total == 0 ? 0.0 : ((p + l + 0.5 * h) / total * 100);
      spots.add(FlSpot(i.toDouble(), pct));
    }
    return spots;
  }

  @override
  Widget build(BuildContext context) {
    final spots = _spots();
    final allEmpty = spots.every((s) => s.y == 0);
    if (allEmpty) return const SizedBox.shrink();

    return Card(
      elevation: 0,
      color: JaikalkiBrand.warmWhite,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: JaikalkiBrand.saffronPale),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              '30-day trend',
              style: TextStyle(
                fontWeight: FontWeight.w700,
                color: JaikalkiBrand.indigoDark,
              ),
            ),
            const SizedBox(height: 4),
            const Text(
              '7-day rolling attendance %. Dashed line = 75% exam cutoff.',
              style: TextStyle(
                fontSize: 11,
                color: JaikalkiBrand.textSecondary,
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 140,
              child: LineChart(
                LineChartData(
                  minY: 0,
                  maxY: 100,
                  gridData: const FlGridData(show: false),
                  titlesData: FlTitlesData(
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 28,
                        interval: 25,
                        getTitlesWidget: (v, _) => Text(
                          '${v.toInt()}',
                          style: const TextStyle(
                            fontSize: 10,
                            color: JaikalkiBrand.textSecondary,
                          ),
                        ),
                      ),
                    ),
                    rightTitles: const AxisTitles(
                        sideTitles: SideTitles(showTitles: false)),
                    topTitles: const AxisTitles(
                        sideTitles: SideTitles(showTitles: false)),
                    bottomTitles: const AxisTitles(
                        sideTitles: SideTitles(showTitles: false)),
                  ),
                  borderData: FlBorderData(show: false),
                  extraLinesData: ExtraLinesData(
                    horizontalLines: [
                      HorizontalLine(
                        y: 75,
                        color: const Color(0xFFD32F2F).withOpacity(0.7),
                        strokeWidth: 1,
                        dashArray: [4, 4],
                      ),
                    ],
                  ),
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      color: JaikalkiBrand.saffron,
                      barWidth: 2.5,
                      dotData: const FlDotData(show: false),
                      belowBarData: BarAreaData(
                        show: true,
                        color: JaikalkiBrand.saffron.withOpacity(0.12),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---- Class-average comparison --------------------------------------------

class _ClassAverageCard extends StatelessWidget {
  const _ClassAverageCard({required this.avg});
  final ClassAverage avg;

  @override
  Widget build(BuildContext context) {
    final above = avg.isAboveAverage;
    final accent = above ? JaikalkiBrand.tealDark : const Color(0xFFD32F2F);
    final gap = avg.gap.abs();

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.groups_rounded,
                  size: 18, color: JaikalkiBrand.indigoDark),
              const SizedBox(width: 6),
              const Text(
                'Vs class average',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: JaikalkiBrand.indigoDark,
                ),
              ),
              const Spacer(),
              Text(
                '${avg.windowDays}d · ${avg.classSize} students',
                style: const TextStyle(
                  fontSize: 11,
                  color: JaikalkiBrand.textSecondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: _AvgColumn(
                  label: 'Your child',
                  pct: avg.childPct,
                  color: accent,
                  emphasis: true,
                ),
              ),
              Container(
                width: 1, height: 44,
                color: JaikalkiBrand.saffronPale,
              ),
              Expanded(
                child: _AvgColumn(
                  label: 'Class avg',
                  pct: avg.classPct,
                  color: JaikalkiBrand.indigo,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Icon(
                above ? Icons.trending_up : Icons.trending_down,
                size: 14,
                color: accent,
              ),
              const SizedBox(width: 4),
              Text(
                above
                    ? '+${gap.toStringAsFixed(1)}% above class'
                    : '−${gap.toStringAsFixed(1)}% below class',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: accent,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _AvgColumn extends StatelessWidget {
  const _AvgColumn({
    required this.label,
    required this.pct,
    required this.color,
    this.emphasis = false,
  });

  final String label;
  final double pct;
  final Color color;
  final bool emphasis;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 11,
            color: JaikalkiBrand.textSecondary,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.4,
          ),
        ),
        const SizedBox(height: 2),
        Text(
          '${pct.toStringAsFixed(1)}%',
          style: TextStyle(
            fontSize: emphasis ? 26 : 22,
            fontWeight: FontWeight.w700,
            color: color,
          ),
        ),
      ],
    );
  }
}

// ---- Subject-wise breakdown ----------------------------------------------

class _SubjectBreakdown extends StatelessWidget {
  const _SubjectBreakdown({required this.report});
  final SubjectAttendanceReport report;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.subject_rounded,
                  size: 18, color: JaikalkiBrand.indigoDark),
              const SizedBox(width: 6),
              const Text(
                'By subject',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: JaikalkiBrand.indigoDark,
                ),
              ),
              const Spacer(),
              if (report.windowDays > 0)
                Text(
                  'last ${report.windowDays}d',
                  style: const TextStyle(
                    fontSize: 11,
                    color: JaikalkiBrand.textSecondary,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          if (report.isEmpty)
            Text(
              report.note ?? 'No subject-wise data yet.',
              style: const TextStyle(
                fontSize: 12,
                color: JaikalkiBrand.textSecondary,
                height: 1.4,
              ),
            )
          else ...[
            for (final row in report.rows) _SubjectBar(row: row),
            const SizedBox(height: 4),
            // When the backend reports a note alongside actual rows, it's
            // telling us *how* the breakdown was computed (e.g. "day-level
            // projected onto timetable"). Show it as a quiet hint so the
            // parent doesn't mistake projection for per-subject measurement.
            if (report.note != null) ...[
              const SizedBox(height: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                decoration: BoxDecoration(
                  color: JaikalkiBrand.marigoldPale,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.info_outline,
                        size: 14, color: JaikalkiBrand.indigo),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        report.note!,
                        style: const TextStyle(
                          fontSize: 11,
                          color: JaikalkiBrand.indigoDark,
                          height: 1.35,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 6),
            ],
            Row(
              children: [
                Container(
                  width: 8, height: 8,
                  decoration: BoxDecoration(
                    color: const Color(0xFFD32F2F),
                    borderRadius: BorderRadius.circular(1),
                  ),
                ),
                const SizedBox(width: 4),
                const Text(
                  'dotted line = 75% exam cutoff',
                  style: TextStyle(
                    fontSize: 10,
                    color: JaikalkiBrand.textSecondary,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _SubjectBar extends StatelessWidget {
  const _SubjectBar({required this.row});
  final SubjectAttendanceRow row;

  @override
  Widget build(BuildContext context) {
    final pct = row.percentage.clamp(0, 100).toDouble();
    final isBelow = pct < 75;
    final fillColor =
        isBelow ? const Color(0xFFD32F2F) : JaikalkiBrand.tealDark;

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  row.subjectName,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: JaikalkiBrand.indigoDark,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Text(
                '${pct.toStringAsFixed(0)}%',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: fillColor,
                ),
              ),
              const SizedBox(width: 6),
              Text(
                '${row.present + row.late + (row.halfDay > 0 ? 1 : 0)}/${row.total}',
                style: const TextStyle(
                  fontSize: 10,
                  color: JaikalkiBrand.textSecondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          LayoutBuilder(
            builder: (context, constraints) {
              final width = constraints.maxWidth;
              final fillWidth = (pct / 100) * width;
              final cutoffX = 0.75 * width;
              return Stack(
                children: [
                  Container(
                    height: 8,
                    width: width,
                    decoration: BoxDecoration(
                      color: JaikalkiBrand.saffronPale,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                  Container(
                    height: 8,
                    width: fillWidth,
                    decoration: BoxDecoration(
                      color: fillColor,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                  Positioned(
                    left: cutoffX - 0.5,
                    top: -2,
                    bottom: -2,
                    child: const _CutoffMarker(),
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _CutoffMarker extends StatelessWidget {
  const _CutoffMarker();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 1.5,
      decoration: BoxDecoration(
        color: const Color(0xFFD32F2F).withOpacity(0.7),
        borderRadius: BorderRadius.circular(1),
      ),
    );
  }
}

// ---- Today's schedule card -----------------------------------------------

class _TodayScheduleCard extends StatelessWidget {
  const _TodayScheduleCard({required this.timetable});
  final TimetableView timetable;

  @override
  Widget build(BuildContext context) {
    final weekday = DateTime.now().weekday - 1; // 0=Mon..6=Sun
    final periods = timetable.dayCells(weekday);
    if (periods.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: JaikalkiBrand.warmWhite,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: JaikalkiBrand.saffronPale),
        ),
        child: Row(
          children: const [
            Icon(Icons.event_available_outlined,
                size: 18, color: JaikalkiBrand.textSecondary),
            SizedBox(width: 8),
            Expanded(
              child: Text(
                'No classes scheduled today.',
                style: TextStyle(
                  color: JaikalkiBrand.textSecondary,
                  fontSize: 13,
                ),
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.today_rounded,
                  size: 18, color: JaikalkiBrand.indigoDark),
              const SizedBox(width: 6),
              const Text(
                "Today's classes",
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  color: JaikalkiBrand.indigoDark,
                ),
              ),
              const Spacer(),
              if (timetable.className != null && timetable.sectionName != null)
                Text(
                  '${timetable.className} · ${timetable.sectionName}',
                  style: const TextStyle(
                    fontSize: 11,
                    color: JaikalkiBrand.textSecondary,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          for (int i = 0; i < periods.length; i++) ...[
            _PeriodTile(
              cell: periods[i],
              isLast: i == periods.length - 1,
            ),
          ],
        ],
      ),
    );
  }
}

class _PeriodTile extends StatelessWidget {
  const _PeriodTile({required this.cell, required this.isLast});
  final TimetableCell cell;
  final bool isLast;

  String _humanHM(String? iso) {
    if (iso == null) return '';
    final parts = iso.split(':');
    if (parts.length < 2) return iso;
    final h = int.tryParse(parts[0]) ?? 0;
    final m = parts[1];
    final h12 = h == 0 ? 12 : (h > 12 ? h - 12 : h);
    final ampm = h < 12 ? 'AM' : 'PM';
    return '$h12:$m $ampm';
  }

  bool _isNow() {
    final now = DateTime.now();
    final start = _toToday(cell.startTime);
    final end = _toToday(cell.endTime);
    if (start == null || end == null) return false;
    return now.isAfter(start) && now.isBefore(end);
  }

  DateTime? _toToday(String? iso) {
    if (iso == null) return null;
    final parts = iso.split(':');
    if (parts.length < 2) return null;
    final h = int.tryParse(parts[0]);
    final m = int.tryParse(parts[1]);
    if (h == null || m == null) return null;
    final now = DateTime.now();
    return DateTime(now.year, now.month, now.day, h, m);
  }

  @override
  Widget build(BuildContext context) {
    final now = _isNow();
    final start = _humanHM(cell.startTime);
    final end = _humanHM(cell.endTime);

    return Padding(
      padding: EdgeInsets.only(bottom: isLast ? 0 : 10),
      child: Row(
        children: [
          Container(
            width: 56,
            padding: const EdgeInsets.symmetric(vertical: 6),
            decoration: BoxDecoration(
              color: now ? JaikalkiBrand.saffron : JaikalkiBrand.saffronPale,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              children: [
                Text(
                  'P${cell.periodNumber}',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: now ? Colors.white : JaikalkiBrand.saffronDarker,
                  ),
                ),
                if (start.isNotEmpty)
                  Text(
                    start.split(' ')[0],
                    style: TextStyle(
                      fontSize: 11,
                      color: now ? Colors.white : JaikalkiBrand.saffronDarker,
                    ),
                  ),
              ],
            ),
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
                        cell.subjectName ?? '—',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 14,
                          color: now
                              ? JaikalkiBrand.saffronDarker
                              : JaikalkiBrand.indigoDark,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (now)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: JaikalkiBrand.saffron,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Text(
                          'NOW',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 9,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 0.6,
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  [
                    if (cell.teacherName != null) cell.teacherName,
                    if (cell.room != null) 'Room ${cell.room}',
                    if (start.isNotEmpty && end.isNotEmpty) '$start – $end',
                  ].whereType<String>().join(' · '),
                  style: const TextStyle(
                    fontSize: 11,
                    color: JaikalkiBrand.textSecondary,
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

// ---- Weekly timetable (expandable) ---------------------------------------

class _WeeklyTimetable extends StatefulWidget {
  const _WeeklyTimetable({required this.timetable});
  final TimetableView timetable;

  @override
  State<_WeeklyTimetable> createState() => _WeeklyTimetableState();
}

class _WeeklyTimetableState extends State<_WeeklyTimetable> {
  bool _expanded = false;
  int _selectedDay = DateTime.now().weekday - 1; // 0=Mon..6=Sun

  static const _dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  @override
  Widget build(BuildContext context) {
    final cells = widget.timetable.dayCells(_selectedDay);

    return Container(
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  const Icon(Icons.calendar_view_week_rounded,
                      size: 18, color: JaikalkiBrand.indigoDark),
                  const SizedBox(width: 6),
                  const Text(
                    'Weekly schedule',
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: JaikalkiBrand.indigoDark,
                    ),
                  ),
                  const Spacer(),
                  Icon(
                    _expanded
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    color: JaikalkiBrand.textSecondary,
                  ),
                ],
              ),
            ),
          ),
          if (_expanded) ...[
            const Divider(height: 1, color: JaikalkiBrand.saffronPale),
            // Day tabs
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
              child: Row(
                children: [
                  for (int i = 0; i < 7; i++)
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 2),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(8),
                        onTap: () => setState(() => _selectedDay = i),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: _selectedDay == i
                                ? JaikalkiBrand.saffron
                                : Colors.transparent,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color: _selectedDay == i
                                  ? JaikalkiBrand.saffron
                                  : JaikalkiBrand.saffronPale,
                            ),
                          ),
                          child: Text(
                            _dayLabels[i],
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: _selectedDay == i
                                  ? Colors.white
                                  : JaikalkiBrand.indigoDark,
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
              child: cells.isEmpty
                  ? const Text(
                      'No classes on this day.',
                      style: TextStyle(
                        color: JaikalkiBrand.textSecondary,
                        fontSize: 12,
                      ),
                    )
                  : Column(
                      children: [
                        for (int i = 0; i < cells.length; i++)
                          _PeriodTile(
                            cell: cells[i],
                            isLast: i == cells.length - 1,
                          ),
                      ],
                    ),
            ),
          ],
        ],
      ),
    );
  }
}

// ---- Legend / loading / error / helpers ----------------------------------

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
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: color,
              )),
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

// ---- Helpers --------------------------------------------------------------

Color _statusToneFor(String status) {
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
      return JaikalkiBrand.textSecondary;
  }
}

IconData _statusIcon(String status) {
  switch (status) {
    case 'present':
      return Icons.check_circle_rounded;
    case 'absent':
      return Icons.cancel_rounded;
    case 'late':
      return Icons.schedule_rounded;
    case 'half_day':
      return Icons.contrast_rounded;
    case 'leave':
      return Icons.event_busy_rounded;
    default:
      return Icons.help_outline_rounded;
  }
}

String _statusLabel(String status, dynamic s) {
  switch (status) {
    case 'present':
      return s.statusPresent;
    case 'absent':
      return s.statusAbsent;
    case 'late':
      return s.statusLate;
    case 'half_day':
      return s.statusHalfDay;
    case 'leave':
      return s.statusLeave;
    default:
      return status;
  }
}

String _ymd(DateTime d) =>
    '${d.year.toString().padLeft(4, "0")}-'
    '${d.month.toString().padLeft(2, "0")}-'
    '${d.day.toString().padLeft(2, "0")}';

String _humanDay(DateTime d) {
  const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ];
  return '${weekdays[d.weekday - 1]}, ${d.day} ${months[d.month - 1]}';
}

String _humanTime(String iso) {
  final t = DateTime.tryParse(iso);
  if (t == null) return iso;
  final local = t.toLocal();
  final h12 = local.hour == 0
      ? 12
      : local.hour > 12
          ? local.hour - 12
          : local.hour;
  final mm = local.minute.toString().padLeft(2, '0');
  final ampm = local.hour < 12 ? 'AM' : 'PM';
  return '$h12:$mm $ampm';
}
