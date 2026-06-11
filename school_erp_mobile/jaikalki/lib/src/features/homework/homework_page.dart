import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:image_picker/image_picker.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../api/api_client.dart';
import '../../api/parent_repository.dart';
import '../../core/children_cubit.dart';
import '../../core/homework_cubit.dart';
import '../../core/service_locator.dart';
import '../../core/settings_cubit.dart';
import '../../theme/brand.dart';

/// Phase 14 + parent-app P0 enhancements.
///
/// Top → bottom:
///   - Stats row (Pending / This week / Overdue)
///   - Subject filter chips
///   - Tab strip: Pending · Submitted · Graded
///   - Per-card "Due in N days" / "Overdue X days" pill
///   - Detail page with text answer + photo + PDF attachments
class HomeworkPage extends StatefulWidget {
  const HomeworkPage({super.key});

  @override
  State<HomeworkPage> createState() => _HomeworkPageState();
}

class _HomeworkPageState extends State<HomeworkPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  String? _subjectFilter; // null = all

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadForSelected());
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  void _loadForSelected() {
    final children = context.read<ChildrenCubit>().state;
    if (children is ChildrenLoaded && children.selectedId != null) {
      context.read<HomeworkCubit>().load(children.selectedId!);
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsCubit>().state;
    final s = settings.strings;

    return MultiBlocProvider(
      providers: [
        BlocProvider.value(value: locator<ChildrenCubit>()),
        BlocProvider.value(value: locator<HomeworkCubit>()),
      ],
      child: BlocListener<ChildrenCubit, ChildrenState>(
        listenWhen: (a, b) =>
            b is ChildrenLoaded &&
            b.selectedId != null &&
            (a is! ChildrenLoaded || a.selectedId != b.selectedId),
        listener: (context, state) => _loadForSelected(),
        child: Scaffold(
          appBar: AppBar(
            title: Text(s.tabHomework),
            bottom: TabBar(
              controller: _tabs,
              labelColor: JaikalkiBrand.saffron,
              unselectedLabelColor: JaikalkiBrand.textSecondary,
              indicatorColor: JaikalkiBrand.saffron,
              tabs: [
                Tab(text: s.hwOpen),       // "Pending"
                Tab(text: s.hwSubmitted),
                Tab(text: s.hwGraded),
              ],
            ),
          ),
          body: BlocBuilder<HomeworkCubit, HomeworkState>(
            builder: (context, state) {
              if (state is HomeworkLoading || state is HomeworkInitial) {
                return const Center(child: CircularProgressIndicator());
              }
              if (state is HomeworkError) {
                return Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(state.message,
                      style: const TextStyle(color: Color(0xFFD32F2F))),
                );
              }
              final loaded = state as HomeworkLoaded;
              final stats = _Stats.fromItems(loaded.items);
              final subjects = _uniqueSubjects(loaded.items);

              return Column(
                children: [
                  if (stats.total > 0) _StatsBar(stats: stats),
                  if (loaded.items.isNotEmpty)
                    _WeeklyProgressBar(items: loaded.items),
                  if (subjects.length > 1)
                    _SubjectCompletionRow(items: loaded.items, subjects: subjects),
                  if (loaded.items.any((h) => h.isOpen)) _UpcomingTimeline(items: loaded.items),
                  if (subjects.length > 1)
                    _SubjectFilterChips(
                      subjects: subjects,
                      selected: _subjectFilter,
                      onSelect: (v) => setState(() => _subjectFilter = v),
                    ),
                  Expanded(
                    child: TabBarView(
                      controller: _tabs,
                      children: [
                        _HomeworkList(
                          items: _applyFilter(loaded.open),
                          showOverdueFirst: true,
                          emptyHint: s.hwNoneOpen,
                          s: s,
                        ),
                        _HomeworkList(
                          items: _applyFilter(loaded.submitted),
                          showOverdueFirst: false,
                          emptyHint: '',
                          s: s,
                        ),
                        _HomeworkList(
                          items: _applyFilter(loaded.graded),
                          showOverdueFirst: false,
                          emptyHint: '',
                          s: s,
                        ),
                      ],
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  List<HomeworkItem> _applyFilter(List<HomeworkItem> items) {
    if (_subjectFilter == null) return items;
    return items.where((h) => h.subjectName == _subjectFilter).toList();
  }

  List<String> _uniqueSubjects(List<HomeworkItem> items) {
    final s = <String>{};
    for (final h in items) {
      if (h.subjectName != null && h.subjectName!.isNotEmpty) s.add(h.subjectName!);
    }
    final out = s.toList()..sort();
    return out;
  }
}

// ---- Stats summary -------------------------------------------------------

class _Stats {
  const _Stats({
    required this.pending,
    required this.dueThisWeek,
    required this.overdue,
    required this.total,
  });

  final int pending;
  final int dueThisWeek;
  final int overdue;
  final int total;

  factory _Stats.fromItems(List<HomeworkItem> items) {
    final today = DateTime.now();
    final weekEnd = today.add(const Duration(days: 7));
    int pending = 0, dueWeek = 0, overdue = 0;
    for (final h in items) {
      if (!h.isOpen) continue;
      final due = DateTime.tryParse(h.dueDate);
      if (due == null) {
        pending++;
        continue;
      }
      if (due.isBefore(DateTime(today.year, today.month, today.day))) {
        overdue++;
      } else {
        pending++;
        if (due.isBefore(weekEnd)) dueWeek++;
      }
    }
    return _Stats(
      pending: pending,
      dueThisWeek: dueWeek,
      overdue: overdue,
      total: items.length,
    );
  }
}

class _StatsBar extends StatelessWidget {
  const _StatsBar({required this.stats});
  final _Stats stats;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 6),
      child: Row(
        children: [
          Expanded(
            child: _StatTile(
              label: 'Pending',
              value: stats.pending,
              tone: JaikalkiBrand.saffron,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _StatTile(
              label: 'Due in 7 days',
              value: stats.dueThisWeek,
              tone: JaikalkiBrand.marigold,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: _StatTile(
              label: 'Overdue',
              value: stats.overdue,
              tone: const Color(0xFFD32F2F),
            ),
          ),
        ],
      ),
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({required this.label, required this.value, required this.tone});

  final String label;
  final int value;
  final Color tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      decoration: BoxDecoration(
        color: tone.withOpacity(0.10),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: tone.withOpacity(0.45)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.4,
              color: JaikalkiBrand.textSecondary,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            '$value',
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: tone,
            ),
          ),
        ],
      ),
    );
  }
}

// ---- Subject filter chips ------------------------------------------------

class _SubjectFilterChips extends StatelessWidget {
  const _SubjectFilterChips({
    required this.subjects,
    required this.selected,
    required this.onSelect,
  });

  final List<String> subjects;
  final String? selected;
  final ValueChanged<String?> onSelect;

  Widget _chip({required String label, required bool active, required VoidCallback onTap}) {
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: active ? JaikalkiBrand.saffron : Colors.transparent,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: active ? JaikalkiBrand.saffron : JaikalkiBrand.saffronPale,
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: active ? Colors.white : JaikalkiBrand.indigoDark,
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 6),
      child: Row(
        children: [
          _chip(
            label: 'All',
            active: selected == null,
            onTap: () => onSelect(null),
          ),
          for (final s in subjects)
            _chip(
              label: s,
              active: selected == s,
              onTap: () => onSelect(selected == s ? null : s),
            ),
        ],
      ),
    );
  }
}

// ---- P1: This-week progress ----------------------------------------------

class _WeeklyProgressBar extends StatelessWidget {
  const _WeeklyProgressBar({required this.items});
  final List<HomeworkItem> items;

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now();
    final weekAgo = DateTime(today.year, today.month, today.day)
        .subtract(const Duration(days: 7));

    int dueThisWeek = 0;
    int submittedThisWeek = 0;
    for (final h in items) {
      final due = DateTime.tryParse(h.dueDate);
      if (due == null) continue;
      if (due.isBefore(weekAgo) || due.isAfter(today)) continue;
      dueThisWeek++;
      if (h.isSubmitted || h.isGraded) submittedThisWeek++;
    }

    if (dueThisWeek == 0) return const SizedBox.shrink();

    final pct = submittedThisWeek / dueThisWeek;
    final isStrong = pct >= 0.8;

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: JaikalkiBrand.warmWhite,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: JaikalkiBrand.saffronPale),
        ),
        child: Row(
          children: [
            SizedBox(
              width: 52, height: 52,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  CircularProgressIndicator(
                    value: pct.clamp(0, 1),
                    strokeWidth: 5,
                    backgroundColor: JaikalkiBrand.saffronPale,
                    valueColor: AlwaysStoppedAnimation(
                      isStrong ? JaikalkiBrand.tealDark : JaikalkiBrand.saffron,
                    ),
                  ),
                  Text(
                    '${(pct * 100).round()}%',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: isStrong
                          ? JaikalkiBrand.tealDark
                          : JaikalkiBrand.saffronDarker,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'This week',
                    style: TextStyle(
                      fontSize: 11,
                      letterSpacing: 0.4,
                      fontWeight: FontWeight.w600,
                      color: JaikalkiBrand.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '$submittedThisWeek of $dueThisWeek submitted',
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: JaikalkiBrand.indigoDark,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    isStrong
                        ? 'On track. Keep it up.'
                        : 'Falling behind — ${dueThisWeek - submittedThisWeek} pending.',
                    style: TextStyle(
                      fontSize: 11,
                      color: isStrong
                          ? JaikalkiBrand.tealDark
                          : JaikalkiBrand.saffronDarker,
                    ),
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

// ---- P1: Per-subject completion % ----------------------------------------

class _SubjectCompletionRow extends StatelessWidget {
  const _SubjectCompletionRow({required this.items, required this.subjects});
  final List<HomeworkItem> items;
  final List<String> subjects;

  @override
  Widget build(BuildContext context) {
    // Look-back window: 30 days. Match the attendance-by-subject heuristic.
    final today = DateTime.now();
    final cutoff = DateTime(today.year, today.month, today.day)
        .subtract(const Duration(days: 30));

    final perSubject = <String, ({int done, int total})>{};
    for (final h in items) {
      if (h.subjectName == null) continue;
      final assigned = DateTime.tryParse(h.assignedOn);
      if (assigned != null && assigned.isBefore(cutoff)) continue;
      final existing = perSubject[h.subjectName!] ?? (done: 0, total: 0);
      final isDone = h.isSubmitted || h.isGraded;
      perSubject[h.subjectName!] = (
        done: existing.done + (isDone ? 1 : 0),
        total: existing.total + 1,
      );
    }
    if (perSubject.isEmpty) return const SizedBox.shrink();

    // Sort by completion % asc — lowest first, most actionable.
    final sorted = perSubject.entries.toList()
      ..sort((a, b) {
        final pa = a.value.total == 0 ? 1.0 : a.value.done / a.value.total;
        final pb = b.value.total == 0 ? 1.0 : b.value.done / b.value.total;
        return pa.compareTo(pb);
      });

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: SizedBox(
        height: 92,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemBuilder: (context, i) {
            final e = sorted[i];
            final pct = e.value.total == 0 ? 0.0 : e.value.done / e.value.total;
            final pctInt = (pct * 100).round();
            final tone = pct >= 0.8
                ? JaikalkiBrand.tealDark
                : pct >= 0.5
                    ? JaikalkiBrand.marigold
                    : const Color(0xFFD32F2F);
            return Container(
              width: 110,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: JaikalkiBrand.warmWhite,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: tone.withOpacity(0.4)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    e.key,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: JaikalkiBrand.indigoDark,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '$pctInt%',
                    style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                      color: tone,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    '${e.value.done}/${e.value.total} done',
                    style: const TextStyle(
                      fontSize: 10,
                      color: JaikalkiBrand.textSecondary,
                    ),
                  ),
                ],
              ),
            );
          },
          separatorBuilder: (_, __) => const SizedBox(width: 8),
          itemCount: sorted.length,
        ),
      ),
    );
  }
}

// ---- P1: Upcoming timeline -----------------------------------------------

class _UpcomingTimeline extends StatelessWidget {
  const _UpcomingTimeline({required this.items});
  final List<HomeworkItem> items;

  static const _weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now();
    final todayMidnight = DateTime(today.year, today.month, today.day);

    // Group open items by due-day for the next 7 days.
    final byDay = <int, List<HomeworkItem>>{};
    for (final h in items) {
      if (!h.isOpen) continue;
      final due = DateTime.tryParse(h.dueDate);
      if (due == null) continue;
      final diff = due.difference(todayMidnight).inDays;
      if (diff < 0 || diff > 6) continue;
      byDay.putIfAbsent(diff, () => []).add(h);
    }

    if (byDay.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: SizedBox(
        height: 80,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemBuilder: (context, i) {
            final date = todayMidnight.add(Duration(days: i));
            final dayItems = byDay[i] ?? const <HomeworkItem>[];
            final isToday = i == 0;
            return Container(
              width: 78,
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: isToday
                    ? JaikalkiBrand.saffron.withOpacity(0.10)
                    : JaikalkiBrand.warmWhite,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: isToday
                      ? JaikalkiBrand.saffron
                      : JaikalkiBrand.saffronPale,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _weekdays[date.weekday - 1],
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.4,
                      color: isToday
                          ? JaikalkiBrand.saffronDarker
                          : JaikalkiBrand.textSecondary,
                    ),
                  ),
                  Text(
                    '${date.day}',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: isToday
                          ? JaikalkiBrand.saffronDarker
                          : JaikalkiBrand.indigoDark,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Expanded(
                    child: dayItems.isEmpty
                        ? const Text(
                            '—',
                            style: TextStyle(
                              fontSize: 11,
                              color: JaikalkiBrand.textSecondary,
                            ),
                          )
                        : Text(
                            dayItems.length == 1
                                ? dayItems.first.subjectName ?? '1 task'
                                : '${dayItems.length} tasks',
                            style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: JaikalkiBrand.indigoDark,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                  ),
                ],
              ),
            );
          },
          separatorBuilder: (_, __) => const SizedBox(width: 6),
          itemCount: 7,
        ),
      ),
    );
  }
}

// ---- Lists ---------------------------------------------------------------

class _HomeworkList extends StatelessWidget {
  const _HomeworkList({
    required this.items,
    required this.showOverdueFirst,
    required this.emptyHint,
    required this.s,
  });

  final List<HomeworkItem> items;
  final bool showOverdueFirst;
  final String emptyHint;
  final dynamic s;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            emptyHint,
            textAlign: TextAlign.center,
            style: const TextStyle(color: JaikalkiBrand.textSecondary),
          ),
        ),
      );
    }

    // Sort: overdue first (most-overdue at top), then pending by due-date
    // asc (most-urgent next), then everything else by id desc.
    final sorted = [...items];
    if (showOverdueFirst) {
      sorted.sort((a, b) {
        final da = _dueDate(a);
        final db = _dueDate(b);
        if (da == null && db == null) return b.id.compareTo(a.id);
        if (da == null) return 1;
        if (db == null) return -1;
        return da.compareTo(db);
      });
    }

    final today = DateTime(
      DateTime.now().year, DateTime.now().month, DateTime.now().day);
    final overdueCount = showOverdueFirst
        ? sorted.where((h) {
            final d = _dueDate(h);
            return d != null && d.isBefore(today);
          }).length
        : 0;

    return RefreshIndicator(
      onRefresh: () async {
        final children = context.read<ChildrenCubit>().state;
        if (children is ChildrenLoaded && children.selectedId != null) {
          await context
              .read<HomeworkCubit>()
              .refresh(children.selectedId!);
        }
      },
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        itemBuilder: (context, i) {
          // Insert a small "Overdue" header above the overdue group.
          if (showOverdueFirst && overdueCount > 0 && i == 0) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  Container(
                    width: 8, height: 8,
                    decoration: const BoxDecoration(
                      color: Color(0xFFD32F2F),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    'Overdue · $overdueCount',
                    style: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.4,
                      color: Color(0xFFD32F2F),
                    ),
                  ),
                ],
              ),
            );
          }
          final adj = showOverdueFirst && overdueCount > 0 ? i - 1 : i;
          // Insert "Upcoming" divider once we cross the overdue → pending boundary.
          if (showOverdueFirst && overdueCount > 0 && adj == overdueCount) {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: 6),
              child: Row(
                children: [
                  Expanded(child: Divider(color: JaikalkiBrand.saffronPale)),
                  Padding(
                    padding: EdgeInsets.symmetric(horizontal: 8),
                    child: Text(
                      'UPCOMING',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.6,
                        color: JaikalkiBrand.textSecondary,
                      ),
                    ),
                  ),
                  Expanded(child: Divider(color: JaikalkiBrand.saffronPale)),
                ],
              ),
            );
          }
          // Map raw index to item index, accounting for inserted headers.
          int itemIdx = i;
          if (showOverdueFirst && overdueCount > 0) itemIdx -= 1;
          if (showOverdueFirst && overdueCount > 0 && itemIdx >= overdueCount) {
            itemIdx -= 1;
          }
          return _HomeworkCard(item: sorted[itemIdx], s: s);
        },
        separatorBuilder: (_, __) => const SizedBox(height: 10),
        itemCount: sorted.length +
            (showOverdueFirst && overdueCount > 0 ? 1 : 0) +
            (showOverdueFirst && overdueCount > 0 && overdueCount < sorted.length
                ? 1
                : 0),
      ),
    );
  }
}

DateTime? _dueDate(HomeworkItem h) => DateTime.tryParse(h.dueDate);

// ---- Per-row card with due-in pill ---------------------------------------

class _HomeworkCard extends StatelessWidget {
  const _HomeworkCard({required this.item, required this.s});

  final HomeworkItem item;
  final dynamic s;

  Color _statusTone(String status) {
    switch (status) {
      case 'submitted':
        return JaikalkiBrand.teal;
      case 'late':
        return JaikalkiBrand.marigold;
      case 'graded':
        return JaikalkiBrand.indigo;
      case 'missing':
        return const Color(0xFFD32F2F);
      default:
        return JaikalkiBrand.saffron;
    }
  }

  /// Returns (label, color, isUrgent) for the due-in pill, or null if no
  /// date or already submitted/graded.
  ({String label, Color color})? _duePill() {
    if (!item.isOpen) return null;
    final due = DateTime.tryParse(item.dueDate);
    if (due == null) return null;
    final today = DateTime(
      DateTime.now().year, DateTime.now().month, DateTime.now().day);
    final days = due.difference(today).inDays;
    if (days < 0) {
      return (label: 'Overdue ${-days}d', color: const Color(0xFFD32F2F));
    }
    if (days == 0) {
      return (label: 'Due today', color: const Color(0xFFD32F2F));
    }
    if (days == 1) return (label: 'Due tomorrow', color: JaikalkiBrand.marigold);
    if (days <= 3) {
      return (label: 'Due in ${days}d', color: JaikalkiBrand.marigold);
    }
    if (days <= 7) {
      return (label: 'Due in ${days}d', color: JaikalkiBrand.saffron);
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final tone = _statusTone(item.submissionStatus);
    final due = _duePill();

    return Card(
      elevation: 0,
      color: JaikalkiBrand.warmWhite,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(
          color: due?.color.withOpacity(0.4) ?? JaikalkiBrand.saffronPale,
          width: due == null ? 1 : 1.4,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(context),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      item.title,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        color: JaikalkiBrand.indigoDark,
                      ),
                    ),
                  ),
                  if (due != null) ...[
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 7, vertical: 3),
                      decoration: BoxDecoration(
                        color: due.color,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        due.label,
                        style: const TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ] else ...[
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: tone.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        item.submissionStatus,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: tone,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
              if (item.subjectName != null) ...[
                const SizedBox(height: 4),
                Text(item.subjectName!,
                    style: const TextStyle(
                      fontSize: 12,
                      color: JaikalkiBrand.textSecondary,
                    )),
              ],
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.event,
                      size: 14, color: JaikalkiBrand.textSecondary),
                  const SizedBox(width: 4),
                  Text('${s.hwDueOn} ${item.dueDate}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: JaikalkiBrand.textSecondary,
                      )),
                  if (item.maxMarks != null) ...[
                    const SizedBox(width: 12),
                    Icon(Icons.workspace_premium, size: 14, color: tone),
                    const SizedBox(width: 4),
                    Text(
                      item.isGraded
                          ? '${item.marksObtained?.toStringAsFixed(0) ?? "?"} / ${item.maxMarks!.toStringAsFixed(0)}'
                          : '/ ${item.maxMarks!.toStringAsFixed(0)}',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: tone,
                      ),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _openDetail(BuildContext context) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => MultiBlocProvider(
          providers: [
            BlocProvider.value(value: context.read<HomeworkCubit>()),
            BlocProvider.value(value: context.read<ChildrenCubit>()),
            BlocProvider.value(value: context.read<SettingsCubit>()),
          ],
          child: _HomeworkDetailPage(item: item, s: s),
        ),
      ),
    );
  }
}

// ---- Detail page with file attachments -----------------------------------

class _HomeworkDetailPage extends StatefulWidget {
  const _HomeworkDetailPage({required this.item, required this.s});

  final HomeworkItem item;
  final dynamic s;

  @override
  State<_HomeworkDetailPage> createState() => _HomeworkDetailPageState();
}

class _StagedAttachment {
  _StagedAttachment({
    required this.localPath,
    required this.displayName,
    this.serverPath,
    this.uploading = false,
    this.error,
  });

  final String localPath;
  final String displayName;
  String? serverPath;
  bool uploading;
  String? error;

  bool get isReady => serverPath != null && !uploading && error == null;
}

class _HomeworkDetailPageState extends State<_HomeworkDetailPage> {
  final _ctrl = TextEditingController();
  final List<_StagedAttachment> _attachments = [];

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _pickPhoto(ImageSource source) async {
    try {
      final picker = ImagePicker();
      final file = await picker.pickImage(
        source: source, maxWidth: 1920, imageQuality: 85,
      );
      if (file == null) return;
      _addAttachment(file.path, file.name);
    } catch (e) {
      _toast('Could not open camera/gallery: $e');
    }
  }

  Future<void> _pickFile() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'doc', 'docx'],
        withData: false,
      );
      if (result == null || result.files.isEmpty) return;
      final f = result.files.first;
      if (f.path != null) _addAttachment(f.path!, f.name);
    } catch (e) {
      _toast('Could not pick file: $e');
    }
  }

  void _addAttachment(String localPath, String displayName) async {
    if (_attachments.length >= 3) {
      _toast('Maximum 3 attachments per submission.');
      return;
    }
    final att = _StagedAttachment(
      localPath: localPath, displayName: displayName, uploading: true);
    setState(() => _attachments.add(att));
    try {
      final path = await context
          .read<HomeworkCubit>()
          .uploadAttachment(localPath);
      setState(() {
        att.serverPath = path;
        att.uploading = false;
      });
    } catch (e) {
      setState(() {
        att.uploading = false;
        att.error = e.toString();
      });
    }
  }

  void _removeAttachment(int idx) {
    setState(() => _attachments.removeAt(idx));
  }

  void _toast(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  @override
  Widget build(BuildContext context) {
    final item = widget.item;
    final s = widget.s;
    return Scaffold(
      appBar: AppBar(title: Text(item.title)),
      body: BlocBuilder<HomeworkCubit, HomeworkState>(
        builder: (context, state) {
          final submitting = state is HomeworkLoaded && state.submitting;
          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 40),
            children: [
              if (item.subjectName != null)
                Text(item.subjectName!,
                    style: const TextStyle(
                      fontSize: 13,
                      color: JaikalkiBrand.textSecondary,
                    )),
              const SizedBox(height: 6),
              Text(item.title,
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                    color: JaikalkiBrand.indigoDark,
                  )),
              const SizedBox(height: 10),
              Wrap(
                spacing: 12,
                children: [
                  _meta('${s.hwDueOn} ${item.dueDate}'),
                  if (item.maxMarks != null)
                    _meta('${s.hwMarks}: ${item.maxMarks!.toStringAsFixed(0)}'),
                ],
              ),
              const SizedBox(height: 18),
              if (item.description != null && item.description!.isNotEmpty)
                Text(item.description!,
                    style: const TextStyle(fontSize: 14, height: 1.5)),
              if (item.teacherAttachments.isNotEmpty) ...[
                const SizedBox(height: 14),
                _TeacherAttachmentsCard(paths: item.teacherAttachments),
              ],
              const SizedBox(height: 18),
              if (item.isGraded)
                _graderCard(s)
              else if (item.isOpen) ...[
                TextField(
                  controller: _ctrl,
                  maxLines: 6,
                  decoration: InputDecoration(
                    hintText: s.hwAnswerHint,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                _AttachmentsSection(
                  attachments: _attachments,
                  onTakePhoto: () => _pickPhoto(ImageSource.camera),
                  onPickGallery: () => _pickPhoto(ImageSource.gallery),
                  onPickFile: _pickFile,
                  onRemove: _removeAttachment,
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: (submitting ||
                            _attachments.any((a) => a.uploading) ||
                            (_ctrl.text.trim().isEmpty &&
                                _attachments.isEmpty))
                        ? null
                        : _submit,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: JaikalkiBrand.saffron,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: submitting
                        ? const SizedBox(
                            height: 18, width: 18,
                            child: CircularProgressIndicator(
                                color: Colors.white, strokeWidth: 2),
                          )
                        : Text(s.hwSubmitButton),
                  ),
                ),
              ] else
                _submittedCard(s),
            ],
          );
        },
      ),
    );
  }

  Widget _meta(String text) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: JaikalkiBrand.saffronPale,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(text,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: JaikalkiBrand.saffronDarker,
            )),
      );

  Widget _graderCard(dynamic s) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: JaikalkiBrand.tealPale,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (widget.item.marksObtained != null)
              Text(
                '${widget.item.marksObtained!.toStringAsFixed(0)} / ${widget.item.maxMarks?.toStringAsFixed(0) ?? "?"}',
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  color: JaikalkiBrand.tealDark,
                ),
              ),
            if (widget.item.feedback != null && widget.item.feedback!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(s.hwTeacherFeedback,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: JaikalkiBrand.tealDark,
                  )),
              const SizedBox(height: 4),
              Text(widget.item.feedback!,
                  style: const TextStyle(fontSize: 13, height: 1.4)),
            ],
          ],
        ),
      );

  Widget _submittedCard(dynamic s) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: JaikalkiBrand.marigoldPale,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            const Icon(Icons.check_circle, color: JaikalkiBrand.marigold),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                widget.item.submittedAt != null
                    ? '${s.hwSubmitted}: ${widget.item.submittedAt}'
                    : s.hwSubmitted,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
      );

  Future<void> _submit() async {
    final s = widget.s;
    final content = _ctrl.text.trim();
    final ready = _attachments.where((a) => a.isReady).toList();
    if (content.isEmpty && ready.isEmpty) return;
    final children = context.read<ChildrenCubit>().state;
    if (children is! ChildrenLoaded || children.selectedId == null) return;
    final ok = await context.read<HomeworkCubit>().submit(
          homeworkId: widget.item.id,
          studentId: children.selectedId!,
          content: content.isEmpty ? '(see attachments)' : content,
          attachmentPaths:
              ready.isEmpty ? null : ready.map((a) => a.serverPath!).toList(),
        );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(ok ? s.hwSubmitSuccess : s.hwSubmitFailed)),
    );
    if (ok) Navigator.of(context).pop();
  }
}

// ---- Attachments section -------------------------------------------------

class _AttachmentsSection extends StatelessWidget {
  const _AttachmentsSection({
    required this.attachments,
    required this.onTakePhoto,
    required this.onPickGallery,
    required this.onPickFile,
    required this.onRemove,
  });

  final List<_StagedAttachment> attachments;
  final VoidCallback onTakePhoto;
  final VoidCallback onPickGallery;
  final VoidCallback onPickFile;
  final ValueChanged<int> onRemove;

  @override
  Widget build(BuildContext context) {
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
            children: const [
              Icon(Icons.attach_file_rounded,
                  size: 16, color: JaikalkiBrand.indigoDark),
              SizedBox(width: 6),
              Text(
                'Attachments (optional, up to 3)',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                  color: JaikalkiBrand.indigoDark,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (int i = 0; i < attachments.length; i++)
                _AttachmentChip(
                  att: attachments[i],
                  onRemove: () => onRemove(i),
                ),
            ],
          ),
          if (attachments.length < 3) ...[
            if (attachments.isNotEmpty) const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              children: [
                _PickerButton(
                    icon: Icons.photo_camera_outlined,
                    label: 'Camera',
                    onTap: onTakePhoto),
                _PickerButton(
                    icon: Icons.photo_library_outlined,
                    label: 'Gallery',
                    onTap: onPickGallery),
                _PickerButton(
                    icon: Icons.insert_drive_file_outlined,
                    label: 'PDF',
                    onTap: onPickFile),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _AttachmentChip extends StatelessWidget {
  const _AttachmentChip({required this.att, required this.onRemove});
  final _StagedAttachment att;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final isImage = att.localPath.toLowerCase().endsWith('.jpg') ||
        att.localPath.toLowerCase().endsWith('.jpeg') ||
        att.localPath.toLowerCase().endsWith('.png');
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: att.error != null
            ? const Color(0x1AD32F2F)
            : JaikalkiBrand.saffronPale,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: att.error != null
              ? const Color(0xFFD32F2F)
              : JaikalkiBrand.saffronPale,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (isImage)
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: Image.file(
                File(att.localPath),
                width: 28, height: 28, fit: BoxFit.cover,
                errorBuilder: (_, __, ___) =>
                    const Icon(Icons.image, size: 18),
              ),
            )
          else
            const Icon(Icons.picture_as_pdf_rounded,
                size: 18, color: JaikalkiBrand.saffronDarker),
          const SizedBox(width: 6),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 110),
            child: Text(
              att.displayName,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 11),
            ),
          ),
          const SizedBox(width: 6),
          if (att.uploading)
            const SizedBox(
              width: 12, height: 12,
              child: CircularProgressIndicator(strokeWidth: 1.6),
            )
          else
            InkWell(
              onTap: onRemove,
              child: const Icon(Icons.close_rounded, size: 14),
            ),
        ],
      ),
    );
  }
}

class _PickerButton extends StatelessWidget {
  const _PickerButton({required this.icon, required this.label, required this.onTap});

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: JaikalkiBrand.saffron.withOpacity(0.08),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: JaikalkiBrand.saffron.withOpacity(0.4)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 16, color: JaikalkiBrand.saffronDarker),
            const SizedBox(width: 6),
            Text(label,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: JaikalkiBrand.saffronDarker,
                )),
          ],
        ),
      ),
    );
  }
}


// ---- P2: Teacher attachments on the assignment ---------------------------

class _TeacherAttachmentsCard extends StatelessWidget {
  const _TeacherAttachmentsCard({required this.paths});
  final List<String> paths;

  String _filename(String p) {
    final clean = p.split('/').last.split('\\').last;
    return clean.isEmpty ? p : clean;
  }

  bool _isImage(String p) {
    final lower = p.toLowerCase();
    return lower.endsWith('.jpg') ||
        lower.endsWith('.jpeg') ||
        lower.endsWith('.png');
  }

  Future<void> _download(BuildContext context, String path) async {
    final api = locator<ApiClient>();
    final dir = await getTemporaryDirectory();
    final filename = _filename(path);
    final localPath = '${dir.path}/$filename';
    try {
      await api.dio.download('/v1/uploads/$path', localPath);
      await OpenFilex.open(localPath);
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not open file: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: JaikalkiBrand.tealPale.withOpacity(0.45),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: JaikalkiBrand.teal.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: const [
              Icon(Icons.folder_shared_outlined,
                  size: 16, color: JaikalkiBrand.tealDark),
              SizedBox(width: 6),
              Text(
                'From the teacher',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                  color: JaikalkiBrand.tealDark,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          for (final p in paths)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: InkWell(
                borderRadius: BorderRadius.circular(8),
                onTap: () => _download(context, p),
                child: Row(
                  children: [
                    Icon(
                      _isImage(p)
                          ? Icons.image_outlined
                          : Icons.insert_drive_file_outlined,
                      size: 18,
                      color: JaikalkiBrand.tealDark,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _filename(p),
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: JaikalkiBrand.tealDark,
                          decoration: TextDecoration.underline,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const Icon(Icons.download_rounded,
                        size: 16, color: JaikalkiBrand.tealDark),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
