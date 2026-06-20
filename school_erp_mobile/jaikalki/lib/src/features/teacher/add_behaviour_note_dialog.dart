import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

class AddBehaviourNoteDialog extends StatefulWidget {
  const AddBehaviourNoteDialog({
    super.key,
    required this.studentId,
    required this.studentName,
  });

  final int studentId;
  final String studentName;

  @override
  State<AddBehaviourNoteDialog> createState() => _AddBehaviourNoteDialogState();
}

class _AddBehaviourNoteDialogState extends State<AddBehaviourNoteDialog> {
  final _headline = TextEditingController();
  final _detail = TextEditingController();
  String _kind = 'neutral';
  bool _visibleToParent = true;
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _headline.dispose();
    _detail.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_headline.text.trim().isEmpty) {
      setState(() => _error = 'Headline is required');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await locator<TeacherRepository>().addBehaviourNote(
        studentId: widget.studentId,
        headline: _headline.text.trim(),
        kind: _kind,
        detail: _detail.text.trim().isEmpty ? null : _detail.text.trim(),
        visibleToParent: _visibleToParent,
      );
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on DioException catch (e) {
      // Server returns {"detail": "…"} on failure — surface that instead
      // of the opaque "DioException [bad response]" toString.
      final body = e.response?.data;
      final detail = body is Map ? body['detail'] : null;
      setState(() => _error = detail?.toString() ?? 'Save failed: ${e.message ?? e}');
    } catch (e) {
      setState(() => _error = 'Save failed: $e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Note for ${widget.studentName}'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                for (final k in const ['positive', 'neutral', 'concern'])
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: ChoiceChip(
                      label: Text(k),
                      selected: _kind == k,
                      onSelected: (_) => setState(() => _kind = k),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _headline,
              decoration: const InputDecoration(
                labelText: 'Headline',
                hintText: 'Good participation in class',
              ),
              maxLength: 180,
            ),
            TextField(
              controller: _detail,
              decoration: const InputDecoration(labelText: 'Detail (optional)'),
              minLines: 2, maxLines: 5,
            ),
            const SizedBox(height: 8),
            CheckboxListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              value: _visibleToParent,
              onChanged: (v) => setState(() => _visibleToParent = v ?? true),
              title: const Text('Visible to parent'),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(_error!,
                    style: const TextStyle(color: Color(0xFFD32F2F))),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.of(context).pop(false),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _saving ? null : _save,
          style: ElevatedButton.styleFrom(
            backgroundColor: JaikalkiBrand.saffron,
            foregroundColor: Colors.white,
          ),
          child: _saving
              ? const SizedBox(
                  width: 14, height: 14,
                  child: CircularProgressIndicator(
                    strokeWidth: 2, color: Colors.white,
                  ),
                )
              : const Text('Save'),
        ),
      ],
    );
  }
}
