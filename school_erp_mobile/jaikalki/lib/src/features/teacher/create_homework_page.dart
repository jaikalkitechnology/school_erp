import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Create a new homework assignment — pick a section the teacher
/// covers, fill title/description/due-date/max-marks, optionally
/// attach worksheet PDFs or photos. Each attachment uploads in the
/// background as soon as it's picked so the create POST is one fast
/// request when Save is tapped.
class CreateHomeworkPage extends StatefulWidget {
  const CreateHomeworkPage({super.key, this.sections = const []});

  /// Optional — when launched from a section page, pre-select it.
  final List<SectionAccess> sections;

  @override
  State<CreateHomeworkPage> createState() => _CreateHomeworkPageState();
}

class _CreateHomeworkPageState extends State<CreateHomeworkPage> {
  final _formKey = GlobalKey<FormState>();
  final _title = TextEditingController();
  final _description = TextEditingController();
  final _maxMarks = TextEditingController(text: '10');

  SectionAccess? _section;
  late List<SectionAccess> _sections;
  DateTime _dueDate = DateTime.now().add(const Duration(days: 2));
  final List<_PickedAttachment> _attachments = [];
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _sections = widget.sections;
    if (_sections.length == 1) _section = _sections.first;
    if (_sections.isEmpty) {
      _loadSections();
    }
  }

  Future<void> _loadSections() async {
    try {
      final me = await locator<TeacherRepository>().me();
      if (!mounted) return;
      setState(() {
        _sections = me.sections;
        if (_sections.length == 1) _section = _sections.first;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = 'Could not load sections: $e');
    }
  }

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    _maxMarks.dispose();
    super.dispose();
  }

  Future<void> _pickDueDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _dueDate,
      firstDate: DateTime.now().subtract(const Duration(days: 1)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) setState(() => _dueDate = picked);
  }

  Future<void> _pickPhoto(ImageSource src) async {
    final picker = ImagePicker();
    final xfile = await picker.pickImage(
      source: src, maxWidth: 1600, imageQuality: 85,
    );
    if (xfile == null) return;
    _addAndUpload(_PickedAttachment(path: xfile.path, name: xfile.name));
  }

  Future<void> _pickFile() async {
    final res = await FilePicker.platform.pickFiles(
      withData: false,
      type: FileType.custom,
      allowedExtensions: ['pdf', 'docx', 'jpg', 'jpeg', 'png'],
    );
    if (res == null || res.files.isEmpty) return;
    final f = res.files.first;
    if (f.path == null) return;
    _addAndUpload(_PickedAttachment(path: f.path!, name: f.name));
  }

  void _addAndUpload(_PickedAttachment att) {
    setState(() => _attachments.add(att));
    _upload(att);
  }

  Future<void> _upload(_PickedAttachment att) async {
    try {
      final path = await locator<TeacherRepository>().uploadFile(
        localPath: att.path,
        category: 'homework',
        subcategory: 'assignments',
      );
      if (!mounted) return;
      setState(() {
        att.uploadedPath = path;
        att.uploading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        att.uploading = false;
        att.error = '$e';
      });
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_section == null) {
      setState(() => _error = 'Pick a section');
      return;
    }
    if (_attachments.any((a) => a.uploading)) {
      setState(() => _error = 'Wait for attachments to finish uploading');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final paths = _attachments
          .where((a) => a.uploadedPath != null)
          .map((a) => a.uploadedPath!)
          .toList();
      await locator<TeacherRepository>().createHomework(
        sectionId: _section!.sectionId,
        title: _title.text.trim(),
        description: _description.text.trim().isEmpty
            ? null : _description.text.trim(),
        dueDate:
            '${_dueDate.year}-${_dueDate.month.toString().padLeft(2, "0")}-${_dueDate.day.toString().padLeft(2, "0")}',
        maxMarks: double.tryParse(_maxMarks.text.trim()) ?? 10,
        attachments: paths,
      );
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (e) {
      setState(() => _error = 'Save failed: $e');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('New homework')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
          children: [
            DropdownButtonFormField<SectionAccess>(
              value: _section,
              decoration: const InputDecoration(
                labelText: 'Section',
                border: OutlineInputBorder(),
              ),
              items: _sections
                  .map((s) => DropdownMenuItem(
                        value: s,
                        child: Text(
                          '${s.displayLabel}${s.subjects.isEmpty ? "" : " · ${s.subjects.join("/")}"}',
                        ),
                      ))
                  .toList(),
              onChanged: (v) => setState(() => _section = v),
              validator: (v) => v == null ? 'Required' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _title,
              decoration: const InputDecoration(
                labelText: 'Title',
                border: OutlineInputBorder(),
              ),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Required' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _description,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'Instructions (optional)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: InkWell(
                    onTap: _pickDueDate,
                    child: InputDecorator(
                      decoration: const InputDecoration(
                        labelText: 'Due date',
                        border: OutlineInputBorder(),
                      ),
                      child: Text(
                        '${_dueDate.year}-${_dueDate.month.toString().padLeft(2, "0")}-${_dueDate.day.toString().padLeft(2, "0")}',
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                SizedBox(
                  width: 110,
                  child: TextFormField(
                    controller: _maxMarks,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Max marks',
                      border: OutlineInputBorder(),
                    ),
                    validator: (v) {
                      final n = double.tryParse(v ?? '');
                      if (n == null || n < 0) return 'Bad';
                      return null;
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _pickPhoto(ImageSource.camera),
                    icon: const Icon(Icons.camera_alt_outlined),
                    label: const Text('Camera'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _pickPhoto(ImageSource.gallery),
                    icon: const Icon(Icons.photo_library_outlined),
                    label: const Text('Gallery'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _pickFile,
                    icon: const Icon(Icons.attach_file_outlined),
                    label: const Text('File'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ..._attachments.map(_attachmentRow),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(_error!,
                  style: const TextStyle(color: Color(0xFFD32F2F))),
            ],
            const SizedBox(height: 18),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _submitting ? null : _submit,
                style: ElevatedButton.styleFrom(
                  backgroundColor: JaikalkiBrand.saffron,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: _submitting
                    ? const SizedBox(
                        height: 18, width: 18,
                        child: CircularProgressIndicator(
                          color: Colors.white, strokeWidth: 2,
                        ),
                      )
                    : const Text('Post homework'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _attachmentRow(_PickedAttachment att) {
    return ListTile(
      dense: true,
      leading: const Icon(Icons.insert_drive_file_outlined),
      title: Text(att.name, maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: att.uploading
          ? const LinearProgressIndicator()
          : att.error != null
              ? Text(att.error!,
                  style: const TextStyle(color: Color(0xFFD32F2F)))
              : const Text('Ready'),
      trailing: IconButton(
        icon: const Icon(Icons.close),
        onPressed: () => setState(() => _attachments.remove(att)),
      ),
    );
  }
}

class _PickedAttachment {
  _PickedAttachment({required this.path, required this.name});
  final String path;
  final String name;
  bool uploading = true;
  String? uploadedPath;
  String? error;
}
