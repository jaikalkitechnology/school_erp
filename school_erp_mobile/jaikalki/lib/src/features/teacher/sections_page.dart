import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
import 'take_attendance_page.dart';

/// Lists every section the teacher has access to — class-teacher row(s)
/// at the top, then subject-teacher rows underneath.
class SectionsPage extends StatefulWidget {
  const SectionsPage({super.key});

  @override
  State<SectionsPage> createState() => _SectionsPageState();
}

class _SectionsPageState extends State<SectionsPage> {
  late Future<TeacherMe> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<TeacherRepository>().me();
  }

  Future<void> _reload() async {
    setState(() {
      _future = locator<TeacherRepository>().me();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My classes')),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: FutureBuilder<TeacherMe>(
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
                    'Could not load classes: ${snap.error}',
                    style: const TextStyle(color: Color(0xFFD32F2F)),
                  ),
                ),
              ]);
            }
            final me = snap.data!;
            if (me.sections.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 80),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No sections assigned to you yet.\nAsk the school admin to assign you as a class teacher or subject teacher.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                ),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              itemCount: me.sections.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) => _SectionCard(section: me.sections[i]),
            );
          },
        ),
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.section});
  final SectionAccess section;

  @override
  Widget build(BuildContext context) {
    final tone = section.isClassTeacher
        ? JaikalkiBrand.saffron
        : JaikalkiBrand.teal;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => TakeAttendancePage(
              sectionId: section.sectionId,
              sectionLabel: section.displayLabel,
            ),
          ),
        ),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: JaikalkiBrand.warmWhite,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: tone.withOpacity(0.4)),
          ),
          child: Row(
            children: [
              Container(
                width: 48, height: 48,
                decoration: BoxDecoration(
                  color: tone.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                alignment: Alignment.center,
                child: Icon(
                  section.isClassTeacher
                      ? Icons.workspace_premium_outlined
                      : Icons.school_outlined,
                  color: tone,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(section.displayLabel,
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: JaikalkiBrand.indigoDark,
                        )),
                    const SizedBox(height: 4),
                    Wrap(
                      spacing: 6, runSpacing: 4,
                      children: [
                        if (section.isClassTeacher)
                          _chip('Class teacher', JaikalkiBrand.saffron),
                        if (section.subjects.isNotEmpty)
                          _chip(section.subjects.join(' · '),
                              JaikalkiBrand.tealDark),
                        _chip('${section.studentCount} students',
                            JaikalkiBrand.indigoDark),
                      ],
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
