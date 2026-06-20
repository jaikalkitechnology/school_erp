import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
import '../../widgets/authed_photo.dart';
import 'add_behaviour_note_dialog.dart';

/// Per-student profile drill-down opened from the section roster:
/// student details, recent attendance %, behaviour notes log,
/// exam history (Marks tab), quick-action call/SMS buttons.
class StudentDrillPage extends StatefulWidget {
  const StudentDrillPage({super.key, required this.studentId});
  final int studentId;

  @override
  State<StudentDrillPage> createState() => _StudentDrillPageState();
}

class _StudentDrillPageState extends State<StudentDrillPage>
    with SingleTickerProviderStateMixin {
  late Future<StudentDrill> _future;
  late Future<List<StudentExamRow>> _examsFuture;
  late final TabController _tab;

  @override
  void initState() {
    super.initState();
    _tab = TabController(length: 2, vsync: this);
    _future = locator<TeacherRepository>().studentDrill(widget.studentId);
    _examsFuture =
        locator<TeacherRepository>().studentMarks(widget.studentId);
  }

  @override
  void dispose() {
    _tab.dispose();
    super.dispose();
  }

  Future<void> _reload() async {
    setState(() {
      _future = locator<TeacherRepository>().studentDrill(widget.studentId);
      _examsFuture =
          locator<TeacherRepository>().studentMarks(widget.studentId);
    });
    await Future.wait([_future, _examsFuture]);
  }

  Future<void> _call(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not dial $phone')),
      );
    }
  }

  Future<void> _sms(String phone) async {
    final uri = Uri(scheme: 'sms', path: phone);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not open SMS for $phone')),
      );
    }
  }

  Future<void> _addNote(StudentDrill drill) async {
    final added = await showDialog<bool>(
      context: context,
      builder: (_) => AddBehaviourNoteDialog(
        studentId: drill.studentId,
        studentName: drill.fullName,
      ),
    );
    if (added == true) _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Student'),
        bottom: TabBar(
          controller: _tab,
          labelColor: JaikalkiBrand.saffron,
          unselectedLabelColor: JaikalkiBrand.textSecondary,
          indicatorColor: JaikalkiBrand.saffron,
          tabs: const [
            Tab(text: 'Profile'),
            Tab(text: 'Marks'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tab,
        children: [
          _ProfileTab(
            future: _future,
            onReload: _reload,
            onCall: _call,
            onSms: _sms,
            onAddNote: _addNote,
          ),
          _MarksTab(
            future: _examsFuture,
            onReload: _reload,
          ),
        ],
      ),
    );
  }
}

class _ProfileTab extends StatelessWidget {
  const _ProfileTab({
    required this.future,
    required this.onReload,
    required this.onCall,
    required this.onSms,
    required this.onAddNote,
  });
  final Future<StudentDrill> future;
  final Future<void> Function() onReload;
  final void Function(String) onCall;
  final void Function(String) onSms;
  final Future<void> Function(StudentDrill) onAddNote;

  String? _join(String? a, String? b, String sep) {
    final items = [a, b].where((s) => s != null && s.isNotEmpty).toList();
    return items.isEmpty ? null : items.join(sep);
  }

  Widget _row(String label, String? value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 110,
              child: Text(label,
                  style: const TextStyle(
                    fontSize: 12,
                    color: JaikalkiBrand.textSecondary,
                  )),
            ),
            Expanded(
              child: Text(
                value?.isNotEmpty == true ? value! : '—',
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: JaikalkiBrand.indigoDark,
                ),
              ),
            ),
          ],
        ),
      );

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onReload,
      child: FutureBuilder<StudentDrill>(
        future: future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Padding(
              padding: const EdgeInsets.all(24),
              child: Text('Could not load: ${snap.error}',
                  style: const TextStyle(color: Color(0xFFD32F2F))),
            );
          }
          final d = snap.data!;
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            children: [
              _Header(drill: d),
              const SizedBox(height: 12),
              _ContactRow(
                parentPhone: d.parentPhone,
                emergencyPhone: d.emergencyPhone,
                onCall: onCall,
                onSms: onSms,
              ),
              const SizedBox(height: 16),
              _Section(
                title: 'Profile',
                children: [
                  _row('Class', _join(d.classLabel, d.sectionName, ' · ')),
                  _row('Date of birth', d.dateOfBirth),
                  _row('Gender', d.gender),
                  _row('Blood group', d.bloodGroup),
                  if (d.address != null && d.address!.isNotEmpty)
                    _row('Address', d.address!),
                ],
              ),
              const SizedBox(height: 12),
              _Section(
                title: 'Family',
                children: [
                  _row('Father', d.fatherName),
                  _row('Mother', d.motherName),
                  _row('Parent phone', d.parentPhone),
                  _row('Parent email', d.parentEmail),
                ],
              ),
              if ((d.allergies?.isNotEmpty ?? false) ||
                  (d.medicalConditions?.isNotEmpty ?? false)) ...[
                const SizedBox(height: 12),
                _Section(
                  title: 'Medical',
                  children: [
                    _row('Allergies', d.allergies),
                    _row('Conditions', d.medicalConditions),
                  ],
                ),
              ],
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 14),
                      decoration: BoxDecoration(
                        color: JaikalkiBrand.tealPale.withOpacity(0.4),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                            color: JaikalkiBrand.teal.withOpacity(0.4)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            '30-DAY ATTENDANCE',
                            style: TextStyle(
                              fontSize: 10,
                              letterSpacing: 0.7,
                              color: JaikalkiBrand.textSecondary,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            d.attendance30dPct == null
                                ? 'No data'
                                : '${d.attendance30dPct!.toStringAsFixed(1)}%',
                            style: const TextStyle(
                              fontSize: 22,
                              fontWeight: FontWeight.w700,
                              color: JaikalkiBrand.tealDark,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  const Expanded(
                    child: Text(
                      'BEHAVIOUR NOTES',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.6,
                        color: JaikalkiBrand.textSecondary,
                      ),
                    ),
                  ),
                  TextButton.icon(
                    onPressed: () => onAddNote(d),
                    icon: const Icon(Icons.add, size: 16),
                    label: const Text('Add'),
                  ),
                ],
              ),
              if (d.behaviourNotes.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 12),
                  child: Text(
                    'No notes yet.',
                    style: TextStyle(color: JaikalkiBrand.textSecondary),
                  ),
                )
              else
                ...d.behaviourNotes.map((n) => Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: _NoteCard(note: n),
                    )),
            ],
          );
        },
      ),
    );
  }
}

class _MarksTab extends StatelessWidget {
  const _MarksTab({required this.future, required this.onReload});
  final Future<List<StudentExamRow>> future;
  final Future<void> Function() onReload;

  Color _toneFor(String? status) {
    switch (status?.toLowerCase()) {
      case 'pass':
        return JaikalkiBrand.teal;
      case 'fail':
        return const Color(0xFFD32F2F);
      default:
        return JaikalkiBrand.indigoDark;
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onReload,
      child: FutureBuilder<List<StudentExamRow>>(
        future: future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final exams = snap.data ?? const <StudentExamRow>[];
          if (exams.isEmpty) {
            return ListView(children: const [
              SizedBox(height: 80),
              Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'No exam results published yet.',
                    style: TextStyle(color: JaikalkiBrand.textSecondary),
                  ),
                ),
              ),
            ]);
          }
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            itemCount: exams.length,
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemBuilder: (_, i) {
              final e = exams[i];
              return _ExamCard(row: e, tone: _toneFor(e.overallStatus));
            },
          );
        },
      ),
    );
  }
}

class _ExamCard extends StatelessWidget {
  const _ExamCard({required this.row, required this.tone});
  final StudentExamRow row;
  final Color tone;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: tone.withOpacity(0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  row.examName,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: JaikalkiBrand.indigoDark,
                  ),
                ),
              ),
              if (row.overallStatus != null)
                Container(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: tone.withOpacity(0.18),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    row.overallStatus!.toUpperCase(),
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      color: tone,
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            children: [
              Expanded(
                child: _ScorePill(
                  label: 'OBTAINED',
                  value:
                      '${row.totalObtained.toStringAsFixed(0)} / ${row.totalMax.toStringAsFixed(0)}',
                ),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: _ScorePill(
                  label: 'PERCENT',
                  value: '${row.percentage.toStringAsFixed(1)}%',
                ),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: _ScorePill(
                  label: 'GRADE',
                  value: row.overallGrade ?? '—',
                ),
              ),
            ],
          ),
          if (row.subjects.isNotEmpty) ...[
            const SizedBox(height: 8),
            const Text(
              'SUBJECTS',
              style: TextStyle(
                fontSize: 10,
                letterSpacing: 0.5,
                fontWeight: FontWeight.w700,
                color: JaikalkiBrand.textSecondary,
              ),
            ),
            const SizedBox(height: 4),
            ...row.subjects.map((s) {
              final name =
                  (s['subject_name'] ?? s['name'] ?? '').toString();
              final obtained =
                  (s['marks_obtained'] ?? s['obtained'] ?? '').toString();
              final max = (s['max_marks'] ?? s['max'] ?? '').toString();
              final grade = (s['grade'] ?? '').toString();
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(name,
                          style: const TextStyle(
                              fontSize: 12,
                              color: JaikalkiBrand.indigoDark,
                              fontWeight: FontWeight.w600)),
                    ),
                    Text(
                      '$obtained / $max${grade.isNotEmpty ? "  · $grade" : ""}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: JaikalkiBrand.textSecondary,
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ],
      ),
    );
  }
}

class _ScorePill extends StatelessWidget {
  const _ScorePill({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      decoration: BoxDecoration(
        color: JaikalkiBrand.saffronPale.withOpacity(0.4),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: const TextStyle(
                fontSize: 9,
                letterSpacing: 0.5,
                color: JaikalkiBrand.textSecondary,
                fontWeight: FontWeight.w700,
              )),
          const SizedBox(height: 2),
          Text(value,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: JaikalkiBrand.indigoDark,
              )),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.drill});
  final StudentDrill drill;

  String _initials(String n) {
    final parts = n.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts[0].isEmpty) return '?';
    if (parts.length == 1) return parts[0][0].toUpperCase();
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [JaikalkiBrand.indigoDark, Color(0xFF3A2A6B)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Container(
            width: 56, height: 56,
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.white24,
            ),
            clipBehavior: Clip.antiAlias,
            alignment: Alignment.center,
            child: AuthedPhoto(
              path: drill.photoUrl,
              placeholder: Text(
                _initials(drill.fullName),
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                  color: Colors.white,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(drill.fullName,
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 17, fontWeight: FontWeight.w700,
                    )),
                const SizedBox(height: 2),
                Text(
                  '${drill.admissionNumber}${drill.rollNo != null ? " · Roll ${drill.rollNo}" : ""}',
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.85),
                    fontSize: 12,
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

class _ContactRow extends StatelessWidget {
  const _ContactRow({
    required this.parentPhone,
    required this.emergencyPhone,
    required this.onCall,
    required this.onSms,
  });
  final String? parentPhone;
  final String? emergencyPhone;
  final void Function(String) onCall;
  final void Function(String) onSms;

  @override
  Widget build(BuildContext context) {
    final phone = parentPhone ?? emergencyPhone;
    if (phone == null || phone.isEmpty) return const SizedBox.shrink();
    return Row(
      children: [
        Expanded(
          child: OutlinedButton.icon(
            onPressed: () => onCall(phone),
            icon: const Icon(Icons.call_outlined),
            label: Text('Call $phone'),
            style: OutlinedButton.styleFrom(
              foregroundColor: JaikalkiBrand.tealDark,
              padding: const EdgeInsets.symmetric(vertical: 10),
            ),
          ),
        ),
        const SizedBox(width: 8),
        OutlinedButton.icon(
          onPressed: () => onSms(phone),
          icon: const Icon(Icons.sms_outlined),
          label: const Text('SMS'),
          style: OutlinedButton.styleFrom(
            foregroundColor: JaikalkiBrand.indigoDark,
            padding: const EdgeInsets.symmetric(vertical: 10),
          ),
        ),
      ],
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.children});
  final String title;
  final List<Widget> children;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: JaikalkiBrand.warmWhite,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: JaikalkiBrand.saffronPale),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.4,
                  color: JaikalkiBrand.indigoDark,
                )),
            const SizedBox(height: 6),
            ...children,
          ],
        ),
      );
}

class _NoteCard extends StatelessWidget {
  const _NoteCard({required this.note});
  final BehaviourNote note;

  Color _toneFor(String kind) {
    switch (kind) {
      case 'positive':
        return JaikalkiBrand.teal;
      case 'concern':
        return const Color(0xFFD32F2F);
      default:
        return JaikalkiBrand.indigoDark;
    }
  }

  @override
  Widget build(BuildContext context) {
    final tone = _toneFor(note.kind);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: tone.withOpacity(0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: tone.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  note.kind.toUpperCase(),
                  style: TextStyle(
                    fontSize: 10, fontWeight: FontWeight.w800,
                    color: tone, letterSpacing: 0.5,
                  ),
                ),
              ),
              const Spacer(),
              Text(note.occurredOn,
                  style: const TextStyle(
                    fontSize: 11,
                    color: JaikalkiBrand.textSecondary,
                  )),
            ],
          ),
          const SizedBox(height: 4),
          Text(note.headline,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: JaikalkiBrand.indigoDark,
              )),
          if (note.detail != null && note.detail!.isNotEmpty) ...[
            const SizedBox(height: 2),
            Text(note.detail!,
                style: const TextStyle(
                  fontSize: 12, height: 1.4,
                  color: JaikalkiBrand.textSecondary,
                )),
          ],
        ],
      ),
    );
  }
}
