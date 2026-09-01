import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../api/parent_repository.dart';
import '../../core/children_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Parent-facing leave application. The parent picks a child (auto-selected
/// when there's only one), a date range and a reason, and files a leave.
/// Below the form, the history of every leave they've filed with its
/// approval status.
class LeaveApplicationPage extends StatefulWidget {
  const LeaveApplicationPage({super.key});

  @override
  State<LeaveApplicationPage> createState() => _LeaveApplicationPageState();
}

class _LeaveApplicationPageState extends State<LeaveApplicationPage> {
  final _reasonCtrl = TextEditingController();
  int? _studentId;
  DateTime? _start;
  DateTime? _end;
  bool _submitting = false;

  late Future<List<LeaveApplicationRow>> _history;

  @override
  void initState() {
    super.initState();
    _history = locator<ParentRepository>().myLeaves();
    // Default the child to whatever the parent currently has selected.
    final st = locator<ChildrenCubit>().state;
    if (st is ChildrenLoaded) _studentId = st.selectedId;
  }

  @override
  void dispose() {
    _reasonCtrl.dispose();
    super.dispose();
  }

  Future<void> _reloadHistory() async {
    setState(() => _history = locator<ParentRepository>().myLeaves());
    await _history;
  }

  String _fmt(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  Future<void> _pickDate({required bool isStart}) async {
    final now = DateTime.now();
    final initial = isStart
        ? (_start ?? now)
        : (_end ?? _start ?? now);
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(now.year - 1),
      lastDate: DateTime(now.year + 1),
    );
    if (picked == null) return;
    setState(() {
      if (isStart) {
        _start = picked;
        // Keep end on/after start.
        if (_end != null && _end!.isBefore(picked)) _end = picked;
      } else {
        _end = picked;
      }
    });
  }

  bool get _canSubmit =>
      _studentId != null &&
      _start != null &&
      _end != null &&
      !_end!.isBefore(_start!) &&
      _reasonCtrl.text.trim().length >= 3 &&
      !_submitting;

  Future<void> _submit() async {
    if (!_canSubmit) return;
    setState(() => _submitting = true);
    try {
      await locator<ParentRepository>().applyLeave(
        studentId: _studentId!,
        startDate: _fmt(_start!),
        endDate: _fmt(_end!),
        reason: _reasonCtrl.text.trim(),
      );
      if (!mounted) return;
      _reasonCtrl.clear();
      setState(() {
        _start = null;
        _end = null;
        _submitting = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Leave application submitted.')),
      );
      await _reloadHistory();
    } catch (_) {
      if (!mounted) return;
      setState(() => _submitting = false);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not submit. Please try again.')),
      );
    }
  }

  Color _statusTone(String status) {
    switch (status) {
      case 'approved':
        return JaikalkiBrand.teal;
      case 'rejected':
        return const Color(0xFFD32F2F);
      default:
        return JaikalkiBrand.marigold;
    }
  }

  @override
  Widget build(BuildContext context) {
    final childrenState = locator<ChildrenCubit>().state;
    final children = childrenState is ChildrenLoaded
        ? childrenState.children
        : const <Child>[];

    return Scaffold(
      appBar: AppBar(title: const Text('Apply for leave')),
      body: RefreshIndicator(
        onRefresh: _reloadHistory,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: JaikalkiBrand.warmWhite,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: JaikalkiBrand.saffronPale),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('New application',
                      style: TextStyle(
                        fontWeight: FontWeight.w800,
                        fontSize: 16,
                        color: JaikalkiBrand.indigoDark,
                      )),
                  const SizedBox(height: 12),
                  if (children.length > 1) ...[
                    const _FieldLabel('Child'),
                    DropdownButtonFormField<int>(
                      value: _studentId,
                      isExpanded: true,
                      decoration: _dec(),
                      items: [
                        for (final c in children)
                          DropdownMenuItem(
                            value: c.studentId,
                            child: Text(c.fullName),
                          ),
                      ],
                      onChanged: (v) => setState(() => _studentId = v),
                    ),
                    const SizedBox(height: 12),
                  ],
                  Row(
                    children: [
                      Expanded(
                        child: _DateField(
                          label: 'From',
                          value: _start == null ? null : _fmt(_start!),
                          onTap: () => _pickDate(isStart: true),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _DateField(
                          label: 'To',
                          value: _end == null ? null : _fmt(_end!),
                          onTap: () => _pickDate(isStart: false),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  const _FieldLabel('Reason'),
                  TextField(
                    controller: _reasonCtrl,
                    maxLines: 3,
                    onChanged: (_) => setState(() {}),
                    decoration: _dec(hint: 'eg. Fever, family function…'),
                  ),
                  const SizedBox(height: 14),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _canSubmit ? _submit : null,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: JaikalkiBrand.saffron,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      child: _submitting
                          ? const SizedBox(
                              height: 18,
                              width: 18,
                              child: CircularProgressIndicator(
                                  color: Colors.white, strokeWidth: 2),
                            )
                          : const Text('Submit application'),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            const Text('History',
                style: TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 16,
                  color: JaikalkiBrand.indigoDark,
                )),
            const SizedBox(height: 8),
            FutureBuilder<List<LeaveApplicationRow>>(
              future: _history,
              builder: (context, snap) {
                if (snap.connectionState != ConnectionState.done) {
                  return const Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                final rows = snap.data ?? const <LeaveApplicationRow>[];
                if (rows.isEmpty) {
                  return const Padding(
                    padding: EdgeInsets.all(16),
                    child: Text('No leave applications yet.',
                        style: TextStyle(color: JaikalkiBrand.textSecondary)),
                  );
                }
                return Column(
                  children: [
                    for (final r in rows)
                      Container(
                        margin: const EdgeInsets.only(bottom: 8),
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: JaikalkiBrand.warmWhite,
                          borderRadius: BorderRadius.circular(12),
                          border:
                              Border.all(color: JaikalkiBrand.saffronPale),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    '${r.startDate}  →  ${r.endDate}',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w700,
                                      color: JaikalkiBrand.indigoDark,
                                    ),
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color:
                                        _statusTone(r.status).withOpacity(0.15),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Text(
                                    r.status.toUpperCase(),
                                    style: TextStyle(
                                      fontSize: 10,
                                      fontWeight: FontWeight.w800,
                                      color: _statusTone(r.status),
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(r.reason,
                                style: const TextStyle(fontSize: 13)),
                            if ((r.decisionRemarks ?? '').isNotEmpty) ...[
                              const SizedBox(height: 4),
                              Text('Remark: ${r.decisionRemarks}',
                                  style: const TextStyle(
                                    fontSize: 12,
                                    color: JaikalkiBrand.textSecondary,
                                  )),
                            ],
                          ],
                        ),
                      ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  InputDecoration _dec({String? hint}) => InputDecoration(
        hintText: hint,
        isDense: true,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      );
}

class _FieldLabel extends StatelessWidget {
  const _FieldLabel(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: Text(
          text.toUpperCase(),
          style: const TextStyle(
            fontSize: 10,
            letterSpacing: 0.4,
            fontWeight: FontWeight.w700,
            color: JaikalkiBrand.textSecondary,
          ),
        ),
      );
}

class _DateField extends StatelessWidget {
  const _DateField({
    required this.label,
    required this.value,
    required this.onTap,
  });
  final String label;
  final String? value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _FieldLabel(label),
        InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(10),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            decoration: BoxDecoration(
              border: Border.all(color: JaikalkiBrand.saffronPale),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Row(
              children: [
                const Icon(Icons.event, size: 16,
                    color: JaikalkiBrand.textSecondary),
                const SizedBox(width: 8),
                Text(
                  value ?? 'Pick date',
                  style: TextStyle(
                    color: value == null
                        ? JaikalkiBrand.textSecondary
                        : JaikalkiBrand.indigoDark,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
