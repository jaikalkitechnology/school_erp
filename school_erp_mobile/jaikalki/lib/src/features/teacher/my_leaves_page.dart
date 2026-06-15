import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Teacher's own leave applications — list + apply.
class MyLeavesPage extends StatefulWidget {
  const MyLeavesPage({super.key});

  @override
  State<MyLeavesPage> createState() => _MyLeavesPageState();
}

class _MyLeavesPageState extends State<MyLeavesPage> {
  late Future<List<StaffLeaveRow>> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<TeacherRepository>().myLeaves();
  }

  Future<void> _reload() async {
    setState(() {
      _future = locator<TeacherRepository>().myLeaves();
    });
    await _future;
  }

  Future<void> _apply() async {
    final res = await showDialog<bool>(
      context: context,
      builder: (_) => const _ApplyLeaveDialog(),
    );
    if (res == true) _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My leaves')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _apply,
        backgroundColor: JaikalkiBrand.saffron,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: const Text('Apply'),
      ),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: FutureBuilder<List<StaffLeaveRow>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            final rows = snap.data ?? const <StaffLeaveRow>[];
            if (rows.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 80),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No leaves applied yet.',
                      style: TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                ),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
              itemCount: rows.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) => _LeaveCard(row: rows[i]),
            );
          },
        ),
      ),
    );
  }
}

class _LeaveCard extends StatelessWidget {
  const _LeaveCard({required this.row});
  final StaffLeaveRow row;

  Color _toneFor(String status) {
    switch (status) {
      case 'approved':
        return JaikalkiBrand.teal;
      case 'rejected':
        return const Color(0xFFD32F2F);
      case 'cancelled':
        return Colors.grey;
      default:
        return JaikalkiBrand.marigold;
    }
  }

  @override
  Widget build(BuildContext context) {
    final tone = _toneFor(row.status);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: tone.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  '${row.startDate} → ${row.endDate}',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: JaikalkiBrand.indigoDark,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: tone.withOpacity(0.18),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  row.status.toUpperCase(),
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    color: tone,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Text('Kind: ${row.kind}',
              style: const TextStyle(
                fontSize: 11,
                color: JaikalkiBrand.textSecondary,
                fontWeight: FontWeight.w600,
              )),
          if (row.reason.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(row.reason,
                style: const TextStyle(fontSize: 13, height: 1.4)),
          ],
          if (row.decisionRemarks != null &&
              row.decisionRemarks!.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text('Note: ${row.decisionRemarks!}',
                style: const TextStyle(
                  fontSize: 12,
                  fontStyle: FontStyle.italic,
                  color: JaikalkiBrand.textSecondary,
                )),
          ],
        ],
      ),
    );
  }
}

class _ApplyLeaveDialog extends StatefulWidget {
  const _ApplyLeaveDialog();

  @override
  State<_ApplyLeaveDialog> createState() => _ApplyLeaveDialogState();
}

class _ApplyLeaveDialogState extends State<_ApplyLeaveDialog> {
  DateTime _start = DateTime.now();
  DateTime _end = DateTime.now();
  String _kind = 'casual';
  final _reason = TextEditingController();
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  String _fmt(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, "0")}-${d.day.toString().padLeft(2, "0")}';

  Future<void> _pickStart() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _start,
      firstDate: DateTime.now().subtract(const Duration(days: 30)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) {
      setState(() {
        _start = picked;
        if (_end.isBefore(picked)) _end = picked;
      });
    }
  }

  Future<void> _pickEnd() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _end,
      firstDate: _start,
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) setState(() => _end = picked);
  }

  Future<void> _save() async {
    if (_reason.text.trim().length < 3) {
      setState(() => _error = 'Reason is required');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await locator<TeacherRepository>().applyMyLeave(
        startDate: _fmt(_start),
        endDate: _fmt(_end),
        reason: _reason.text.trim(),
        kind: _kind,
      );
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (e) {
      setState(() => _error = 'Save failed: $e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Apply for leave'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: InkWell(
                    onTap: _pickStart,
                    child: InputDecorator(
                      decoration: const InputDecoration(labelText: 'From'),
                      child: Text(_fmt(_start)),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: InkWell(
                    onTap: _pickEnd,
                    child: InputDecorator(
                      decoration: const InputDecoration(labelText: 'To'),
                      child: Text(_fmt(_end)),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: _kind,
              decoration: const InputDecoration(labelText: 'Kind'),
              items: const [
                DropdownMenuItem(value: 'casual', child: Text('Casual')),
                DropdownMenuItem(value: 'sick', child: Text('Sick')),
                DropdownMenuItem(value: 'earned', child: Text('Earned')),
                DropdownMenuItem(value: 'unpaid', child: Text('Unpaid')),
                DropdownMenuItem(value: 'other', child: Text('Other')),
              ],
              onChanged: (v) => setState(() => _kind = v ?? 'casual'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _reason,
              decoration: const InputDecoration(labelText: 'Reason'),
              minLines: 2, maxLines: 4,
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
              : const Text('Apply'),
        ),
      ],
    );
  }
}
