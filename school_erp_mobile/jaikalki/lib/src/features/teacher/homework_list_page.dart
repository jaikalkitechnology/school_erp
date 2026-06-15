import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
import 'create_homework_page.dart';
import 'homework_submissions_page.dart';

/// Teacher's own homework — sorted by due date desc, tap to view the
/// submission list + grade.
class HomeworkListPage extends StatefulWidget {
  const HomeworkListPage({super.key});

  @override
  State<HomeworkListPage> createState() => _HomeworkListPageState();
}

class _HomeworkListPageState extends State<HomeworkListPage> {
  late Future<List<TeacherHomework>> _future;
  late Future<TeacherMe> _me;
  int? _sectionFilter; // null = all

  @override
  void initState() {
    super.initState();
    _future = locator<TeacherRepository>().myHomework();
    _me = locator<TeacherRepository>().me();
  }

  Future<void> _reload() async {
    setState(() {
      _future = locator<TeacherRepository>().myHomework();
    });
    await _future;
  }

  Future<void> _createNew() async {
    final me = await _me;
    if (!mounted) return;
    final ok = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => CreateHomeworkPage(sections: me.sections),
      ),
    );
    if (ok == true) _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Homework')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _createNew,
        backgroundColor: JaikalkiBrand.saffron,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: const Text('New'),
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: FutureBuilder<List<TeacherHomework>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: [
                Padding(
                  padding: const EdgeInsets.all(24),
                  child: Text(
                    'Could not load homework: ${snap.error}',
                    style: const TextStyle(color: Color(0xFFD32F2F)),
                  ),
                ),
              ]);
            }
            final all = snap.data ?? const [];
            final items = _sectionFilter == null
                ? all
                : all.where((h) => h.sectionId == _sectionFilter).toList();
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
              children: [
                FutureBuilder<TeacherMe>(
                  future: _me,
                  builder: (_, meSnap) {
                    final secs = meSnap.data?.sections ?? const [];
                    if (secs.length <= 1) return const SizedBox.shrink();
                    return SizedBox(
                      height: 38,
                      child: ListView(
                        scrollDirection: Axis.horizontal,
                        children: [
                          _filterChip('All', _sectionFilter == null,
                              () => setState(() => _sectionFilter = null)),
                          for (final s in secs)
                            _filterChip(
                              s.displayLabel,
                              _sectionFilter == s.sectionId,
                              () => setState(
                                  () => _sectionFilter = s.sectionId),
                            ),
                        ],
                      ),
                    );
                  },
                ),
                const SizedBox(height: 8),
                if (items.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 60),
                    child: Center(
                      child: Text(
                        'Nothing matches.',
                        style: TextStyle(color: JaikalkiBrand.textSecondary),
                      ),
                    ),
                  )
                else
                  ...items.map((h) => Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: _HomeworkCard(item: h),
                      )),
              ],
            );
          },
        ),
      ),
    );
  }
}

Widget _filterChip(String label, bool selected, VoidCallback onTap) => Padding(
      padding: const EdgeInsets.only(right: 6),
      child: ChoiceChip(
        label: Text(label),
        selected: selected,
        onSelected: (_) => onTap(),
        selectedColor: JaikalkiBrand.saffron,
        labelStyle: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          color: selected ? Colors.white : JaikalkiBrand.indigoDark,
        ),
        backgroundColor: JaikalkiBrand.saffronPale.withOpacity(0.5),
      ),
    );

class _HomeworkCard extends StatelessWidget {
  const _HomeworkCard({required this.item});
  final TeacherHomework item;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => HomeworkSubmissionsPage(
              homeworkId: item.id,
              title: item.title,
              maxMarks: item.maxMarks,
            ),
          ),
        ),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: JaikalkiBrand.warmWhite,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: JaikalkiBrand.saffronPale),
          ),
          child: Row(
            children: [
              Container(
                width: 44, height: 44,
                decoration: BoxDecoration(
                  color: JaikalkiBrand.saffronPale,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.assignment_outlined,
                    color: JaikalkiBrand.saffronDark),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item.title,
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: JaikalkiBrand.indigoDark,
                        )),
                    const SizedBox(height: 2),
                    Text(
                      'Due ${item.dueDate} · max ${item.maxMarks.toStringAsFixed(0)}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: JaikalkiBrand.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right,
                  color: JaikalkiBrand.textSecondary),
            ],
          ),
        ),
      ),
    );
  }
}
