import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../theme/brand.dart';

/// Compact weekly grid: rows = period numbers, columns = days that have
/// any assignment. Today's column is highlighted. Tap a cell to deep-link
/// into the take-attendance flow for that section.
class WeeklyTimetable extends StatelessWidget {
  const WeeklyTimetable({
    required this.tt,
    required this.onTapPeriod,
    super.key,
  });

  final TeacherWeekTimetable tt;
  final void Function(WeekPeriod period) onTapPeriod;

  static const _dowLabels = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now().weekday - 1; // Mon = 1 → 0
    if (tt.rows.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: JaikalkiBrand.warmWhite,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: JaikalkiBrand.saffronPale),
        ),
        child: const Center(
          child: Text(
            'No timetable assigned to you yet.',
            style: TextStyle(color: JaikalkiBrand.textSecondary),
          ),
        ),
      );
    }

    // Period rows: sorted distinct period_number across all entries.
    final periods = (tt.rows.map((r) => r.periodNumber).toSet().toList()
      ..sort());
    // Show all weekdays the teacher works (0..6) — default Mon-Sat if data
    // doesn't include Sunday.
    final days = (tt.days.toSet()..addAll([0, 1, 2, 3, 4, 5])).toList()..sort();
    // Index for fast lookup: (dow, period) → row.
    final byCell = <String, WeekPeriod>{};
    for (final r in tt.rows) {
      byCell['${r.dayOfWeek}_${r.periodNumber}'] = r;
    }

    return Container(
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      padding: const EdgeInsets.all(8),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          columnSpacing: 14,
          headingRowHeight: 32,
          dataRowMinHeight: 44,
          dataRowMaxHeight: 56,
          headingTextStyle: const TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w800,
            color: JaikalkiBrand.indigoDark,
            letterSpacing: 0.5,
          ),
          columns: [
            const DataColumn(label: Text('P')),
            for (final d in days)
              DataColumn(
                label: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 6, vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: d == today
                        ? JaikalkiBrand.saffron.withOpacity(0.18)
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(_dowLabels[d.clamp(0, 6)]),
                ),
              ),
          ],
          rows: [
            for (final p in periods)
              DataRow(
                cells: [
                  DataCell(Text(
                    '$p',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: JaikalkiBrand.saffronDark,
                    ),
                  )),
                  for (final d in days)
                    DataCell(_cell(context, byCell['${d}_$p'], d == today)),
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget _cell(BuildContext context, WeekPeriod? cell, bool isToday) {
    if (cell == null) {
      return Container(
        width: 90,
        alignment: Alignment.center,
        child: const Text(
          '—',
          style: TextStyle(color: JaikalkiBrand.textSecondary, fontSize: 11),
        ),
      );
    }
    return InkWell(
      onTap: () => onTapPeriod(cell),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        width: 96,
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
        decoration: BoxDecoration(
          color: isToday
              ? JaikalkiBrand.saffron.withOpacity(0.12)
              : JaikalkiBrand.tealPale.withOpacity(0.35),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: (isToday
                    ? JaikalkiBrand.saffron
                    : JaikalkiBrand.teal)
                .withOpacity(0.3),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              cell.subjectName ?? '—',
              maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: JaikalkiBrand.indigoDark,
              ),
            ),
            Text(
              cell.sectionLabel ?? '',
              maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 10,
                color: JaikalkiBrand.textSecondary,
              ),
            ),
            if (cell.startsAt != null)
              Text(
                cell.startsAt!,
                style: const TextStyle(
                  fontSize: 9,
                  color: JaikalkiBrand.textSecondary,
                  fontWeight: FontWeight.w600,
                ),
              ),
          ],
        ),
      ),
    );
  }
}
