import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
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

  @override
  void initState() {
    super.initState();
    _future = locator<TeacherRepository>().myHomework();
  }

  Future<void> _reload() async {
    setState(() {
      _future = locator<TeacherRepository>().myHomework();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Homework')),
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
            final items = snap.data ?? const [];
            if (items.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 80),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No homework posted yet.',
                      style: TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                ),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) => _HomeworkCard(item: items[i]),
            );
          },
        ),
      ),
    );
  }
}

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
