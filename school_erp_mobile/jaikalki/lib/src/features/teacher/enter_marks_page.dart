import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Teacher exam-marks entry. Three steps:
///   1. Pick a published exam.
///   2. Pick a {section · subject} the teacher can grade (from the
///      /mark-entry targets endpoint — carries exam_subject_id +
///      section_id so no guessing).
///   3. Enter each student's marks on the roster and save (bulk upsert).
class EnterMarksPage extends StatefulWidget {
  const EnterMarksPage({super.key});

  @override
  State<EnterMarksPage> createState() => _EnterMarksPageState();
}

class _EnterMarksPageState extends State<EnterMarksPage> {
  late Future<List<ExamCalendarRow>> _exams;
  int? _examId;
  Future<List<MarkEntryTarget>>? _targets;

  @override
  void initState() {
    super.initState();
    _exams = locator<TeacherRepository>().exams();
  }

  void _selectExam(int examId) {
    setState(() {
      _examId = examId;
      _targets = locator<TeacherRepository>().markEntryTargets(examId);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Enter exam marks')),
      body: FutureBuilder<List<ExamCalendarRow>>(
        future: _exams,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final exams = snap.data ?? const <ExamCalendarRow>[];
          if (exams.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text(
                  'No published exams yet.\nAsk the office to publish an exam.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: JaikalkiBrand.textSecondary),
                ),
              ),
            );
          }
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            children: [
              const _StepLabel('1 · Pick an exam'),
              const SizedBox(height: 8),
              SizedBox(
                height: 44,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: exams.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (_, i) {
                    final e = exams[i];
                    final selected = e.id == _examId;
                    return ChoiceChip(
                      label: Text(e.name),
                      selected: selected,
                      onSelected: (_) => _selectExam(e.id),
                      selectedColor: JaikalkiBrand.saffronPale,
                      labelStyle: TextStyle(
                        color: selected
                            ? JaikalkiBrand.saffronDarker
                            : JaikalkiBrand.textSecondary,
                        fontWeight: FontWeight.w600,
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 16),
              if (_examId == null)
                const Padding(
                  padding: EdgeInsets.only(top: 40),
                  child: Center(
                    child: Text('Pick an exam to see your papers.',
                        style: TextStyle(color: JaikalkiBrand.textSecondary)),
                  ),
                )
              else
                _TargetsList(future: _targets!),
            ],
          );
        },
      ),
    );
  }
}

class _TargetsList extends StatelessWidget {
  const _TargetsList({required this.future});
  final Future<List<MarkEntryTarget>> future;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<MarkEntryTarget>>(
      future: future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Padding(
            padding: EdgeInsets.only(top: 40),
            child: Center(child: CircularProgressIndicator()),
          );
        }
        final targets = snap.data ?? const <MarkEntryTarget>[];
        if (targets.isEmpty) {
          return const Padding(
            padding: EdgeInsets.only(top: 40),
            child: Center(
              child: Text(
                'No papers to grade for this exam in your sections.',
                textAlign: TextAlign.center,
                style: TextStyle(color: JaikalkiBrand.textSecondary),
              ),
            ),
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const _StepLabel('2 · Pick a paper'),
            const SizedBox(height: 8),
            for (final t in targets)
              Container(
                margin: const EdgeInsets.only(bottom: 8),
                decoration: BoxDecoration(
                  color: JaikalkiBrand.warmWhite,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: JaikalkiBrand.saffronPale),
                ),
                child: ListTile(
                  title: Text('${t.subjectName} · ${t.sectionName}',
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        color: JaikalkiBrand.indigoDark,
                      )),
                  subtitle: Text(
                    [
                      if (t.classLabel != null) t.classLabel!,
                      'Max ${t.maxMarks.toStringAsFixed(0)}',
                      if (t.examDate != null) t.examDate!,
                    ].join(' · '),
                    style: const TextStyle(fontSize: 12),
                  ),
                  trailing: const Icon(Icons.chevron_right,
                      color: JaikalkiBrand.textSecondary),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => _RosterMarksPage(target: t),
                    ),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

class _RosterMarksPage extends StatefulWidget {
  const _RosterMarksPage({required this.target});
  final MarkEntryTarget target;

  @override
  State<_RosterMarksPage> createState() => _RosterMarksPageState();
}

class _RosterMarksPageState extends State<_RosterMarksPage> {
  late Future<ExamRoster> _future;
  final Map<int, TextEditingController> _ctrls = {};
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _future = locator<TeacherRepository>().examRoster(
      examSubjectId: widget.target.examSubjectId,
      sectionId: widget.target.sectionId,
    );
  }

  @override
  void dispose() {
    for (final c in _ctrls.values) {
      c.dispose();
    }
    super.dispose();
  }

  TextEditingController _ctrlFor(ExamRosterRow r) {
    return _ctrls.putIfAbsent(
      r.studentId,
      () => TextEditingController(
        text: r.obtainedMarks == null
            ? ''
            : r.obtainedMarks!.toStringAsFixed(
                r.obtainedMarks! % 1 == 0 ? 0 : 2),
      ),
    );
  }

  Future<void> _save() async {
    final max = widget.target.maxMarks;
    final entries = <Map<String, dynamic>>[];
    for (final entry in _ctrls.entries) {
      final raw = entry.value.text.trim();
      if (raw.isEmpty) continue;
      final v = double.tryParse(raw);
      if (v == null || v < 0 || v > max) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Marks must be between 0 and ${max.toStringAsFixed(0)}.'),
          ),
        );
        return;
      }
      entries.add({'student_id': entry.key, 'obtained_marks': v});
    }
    if (entries.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter at least one mark first.')),
      );
      return;
    }
    setState(() => _saving = true);
    try {
      final written = await locator<TeacherRepository>().submitExamMarks(
        examSubjectId: widget.target.examSubjectId,
        sectionId: widget.target.sectionId,
        entries: entries,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Saved $written mark(s).')),
      );
      Navigator.of(context).pop();
    } catch (_) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not save marks. Try again.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = widget.target;
    return Scaffold(
      appBar: AppBar(title: Text('${t.subjectName} · ${t.sectionName}')),
      body: FutureBuilder<ExamRoster>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final roster = snap.data;
          if (roster == null || roster.rows.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('No students in this section.',
                    style: TextStyle(color: JaikalkiBrand.textSecondary)),
              ),
            );
          }
          return Column(
            children: [
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                color: JaikalkiBrand.saffronPale,
                child: Text(
                  'Max ${roster.maxMarks.toStringAsFixed(0)} · pass ${roster.passingMarks.toStringAsFixed(0)} · ${roster.rows.length} students',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: JaikalkiBrand.saffronDarker,
                  ),
                ),
              ),
              Expanded(
                child: ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 96),
                  itemCount: roster.rows.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (_, i) {
                    final r = roster.rows[i];
                    return Row(
                      children: [
                        Expanded(
                          child: Text(r.studentName,
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                                color: JaikalkiBrand.indigoDark,
                              )),
                        ),
                        SizedBox(
                          width: 88,
                          child: TextField(
                            controller: _ctrlFor(r),
                            keyboardType: const TextInputType.numberWithOptions(
                                decimal: true),
                            textAlign: TextAlign.center,
                            decoration: InputDecoration(
                              hintText: '/${roster.maxMarks.toStringAsFixed(0)}',
                              isDense: true,
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                              ),
                            ),
                          ),
                        ),
                      ],
                    );
                  },
                ),
              ),
            ],
          );
        },
      ),
      bottomNavigationBar: Padding(
        padding: EdgeInsets.fromLTRB(
            16, 8, 16, 8 + MediaQuery.of(context).padding.bottom),
        child: SizedBox(
          width: double.infinity,
          child: ElevatedButton(
            onPressed: _saving ? null : _save,
            style: ElevatedButton.styleFrom(
              backgroundColor: JaikalkiBrand.saffron,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 14),
            ),
            child: _saving
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(
                        color: Colors.white, strokeWidth: 2),
                  )
                : const Text('Save marks'),
          ),
        ),
      ),
    );
  }
}

class _StepLabel extends StatelessWidget {
  const _StepLabel(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Text(
        text.toUpperCase(),
        style: const TextStyle(
          fontSize: 11,
          letterSpacing: 0.5,
          fontWeight: FontWeight.w800,
          color: JaikalkiBrand.textSecondary,
        ),
      );
}
