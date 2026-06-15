import 'package:flutter/material.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../api/api_client.dart';
import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Per-homework submissions list. Shows each student's submission
/// (content + attachments), exposes a "Grade" inline form for submitted
/// rows, marks graded rows with their score.
class HomeworkSubmissionsPage extends StatefulWidget {
  const HomeworkSubmissionsPage({
    super.key,
    required this.homeworkId,
    required this.title,
    required this.maxMarks,
  });

  final int homeworkId;
  final String title;
  final double maxMarks;

  @override
  State<HomeworkSubmissionsPage> createState() =>
      _HomeworkSubmissionsPageState();
}

class _HomeworkSubmissionsPageState extends State<HomeworkSubmissionsPage> {
  late Future<List<HomeworkSubmissionRow>> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<TeacherRepository>().submissionsFor(widget.homeworkId);
  }

  Future<void> _reload() async {
    setState(() {
      _future = locator<TeacherRepository>().submissionsFor(widget.homeworkId);
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: FutureBuilder<List<HomeworkSubmissionRow>>(
          future: _future,
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
            final subs = snap.data ?? const <HomeworkSubmissionRow>[];
            if (subs.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 80),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No submissions yet.',
                      style: TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                ),
              ]);
            }
            // Sort: submitted-but-not-graded first.
            final sorted = [...subs]..sort((a, b) {
                if (a.isGraded != b.isGraded) return a.isGraded ? 1 : -1;
                return (a.submittedAt ?? '').compareTo(b.submittedAt ?? '');
              });
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              itemCount: sorted.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) => _SubmissionCard(
                row: sorted[i],
                maxMarks: widget.maxMarks,
                onGraded: (updated) {
                  setState(() {
                    final next = [...subs];
                    final idx = next.indexWhere((s) => s.id == updated.id);
                    if (idx >= 0) next[idx] = updated;
                    _future = Future.value(next);
                  });
                },
              ),
            );
          },
        ),
      ),
    );
  }
}

class _SubmissionCard extends StatefulWidget {
  const _SubmissionCard({
    required this.row,
    required this.maxMarks,
    required this.onGraded,
  });
  final HomeworkSubmissionRow row;
  final double maxMarks;
  final void Function(HomeworkSubmissionRow) onGraded;

  @override
  State<_SubmissionCard> createState() => _SubmissionCardState();
}

class _SubmissionCardState extends State<_SubmissionCard> {
  late final TextEditingController _marks;
  late final TextEditingController _feedback;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _marks = TextEditingController(
      text: widget.row.marks?.toStringAsFixed(0) ?? '',
    );
    _feedback = TextEditingController(text: widget.row.feedback ?? '');
  }

  @override
  void dispose() {
    _marks.dispose();
    _feedback.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final m = double.tryParse(_marks.text.trim());
    if (m == null) {
      setState(() => _error = 'Marks must be a number');
      return;
    }
    if (m < 0 || m > widget.maxMarks) {
      setState(() => _error = 'Marks must be between 0 and ${widget.maxMarks.toStringAsFixed(0)}');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final updated = await locator<TeacherRepository>().gradeSubmission(
        submissionId: widget.row.id,
        marks: m,
        feedback: _feedback.text.trim(),
      );
      widget.onGraded(updated);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Graded ${m.toStringAsFixed(0)}/${widget.maxMarks.toStringAsFixed(0)}')),
      );
    } catch (e) {
      setState(() => _error = 'Save failed: $e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final r = widget.row;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: r.isGraded
              ? JaikalkiBrand.teal.withOpacity(0.4)
              : JaikalkiBrand.saffronPale,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text('Student #${r.studentId}',
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: JaikalkiBrand.indigoDark,
                    )),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: (r.isGraded
                          ? JaikalkiBrand.teal
                          : JaikalkiBrand.marigold)
                      .withOpacity(0.18),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  r.status,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    color: r.isGraded
                        ? JaikalkiBrand.tealDark
                        : JaikalkiBrand.saffronDark,
                  ),
                ),
              ),
            ],
          ),
          if (r.submittedAt != null)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Text(r.submittedAt!,
                  style: const TextStyle(
                    fontSize: 11,
                    color: JaikalkiBrand.textSecondary,
                  )),
            ),
          if (r.content != null && r.content!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: JaikalkiBrand.saffronPale.withOpacity(0.4),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(r.content!,
                  style: const TextStyle(fontSize: 13, height: 1.4)),
            ),
          ],
          if (r.attachments.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 6, runSpacing: 6,
              children: r.attachments.map(_AttachmentChip.new).toList(),
            ),
          ],
          if (!r.isGraded) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                SizedBox(
                  width: 80,
                  child: TextField(
                    controller: _marks,
                    keyboardType: TextInputType.number,
                    decoration: InputDecoration(
                      labelText: 'Marks',
                      helperText: '/ ${widget.maxMarks.toStringAsFixed(0)}',
                      isDense: true,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _feedback,
                    decoration: InputDecoration(
                      labelText: 'Feedback',
                      isDense: true,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                    ),
                  ),
                ),
              ],
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(_error!,
                    style: const TextStyle(
                        fontSize: 12, color: Color(0xFFD32F2F))),
              ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _saving ? null : _save,
                style: ElevatedButton.styleFrom(
                  backgroundColor: JaikalkiBrand.saffron,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
                child: _saving
                    ? const SizedBox(
                        width: 18, height: 18,
                        child: CircularProgressIndicator(
                          color: Colors.white, strokeWidth: 2,
                        ),
                      )
                    : const Text('Save grade'),
              ),
            ),
          ] else
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Row(
                children: [
                  const Icon(Icons.star_rounded,
                      color: JaikalkiBrand.marigold, size: 18),
                  const SizedBox(width: 4),
                  Text(
                    '${r.marks?.toStringAsFixed(0) ?? "—"} / ${widget.maxMarks.toStringAsFixed(0)}',
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w800,
                      color: JaikalkiBrand.tealDark,
                    ),
                  ),
                  if (r.feedback != null && r.feedback!.isNotEmpty) ...[
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        r.feedback!,
                        maxLines: 2, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 12,
                          color: JaikalkiBrand.textSecondary,
                          fontStyle: FontStyle.italic,
                        ),
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

class _AttachmentChip extends StatefulWidget {
  const _AttachmentChip(this.path);
  final String path;

  @override
  State<_AttachmentChip> createState() => _AttachmentChipState();
}

class _AttachmentChipState extends State<_AttachmentChip> {
  bool _loading = false;

  String get _name {
    final s = widget.path.split('/').last;
    return s.isEmpty ? widget.path : s;
  }

  bool get _isImage =>
      RegExp(r'\.(jpe?g|png|gif|webp)$', caseSensitive: false)
          .hasMatch(_name);

  Future<void> _open() async {
    final api = locator<ApiClient>();
    setState(() => _loading = true);
    try {
      final dir = await getTemporaryDirectory();
      final local = '${dir.path}/$_name';
      await api.dio.download('/v1/uploads/${widget.path}', local);
      await OpenFilex.open(local);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not open file: $e')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: _loading ? null : _open,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        decoration: BoxDecoration(
          color: JaikalkiBrand.tealPale.withOpacity(0.45),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: JaikalkiBrand.teal.withOpacity(0.4)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _isImage
                  ? Icons.image_outlined
                  : Icons.insert_drive_file_outlined,
              size: 14, color: JaikalkiBrand.tealDark,
            ),
            const SizedBox(width: 4),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 140),
              child: Text(
                _name,
                maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 11,
                  color: JaikalkiBrand.tealDark,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            if (_loading) ...[
              const SizedBox(width: 4),
              const SizedBox(
                width: 12, height: 12,
                child: CircularProgressIndicator(strokeWidth: 1.5),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
