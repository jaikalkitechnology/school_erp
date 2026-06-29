import 'package:flutter/material.dart';

import '../../api/principal_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Single unified pending queue for the principal — student leaves +
/// staff leaves with one-tap accept / reject.
class PrincipalApprovalsPage extends StatefulWidget {
  const PrincipalApprovalsPage({super.key});

  @override
  State<PrincipalApprovalsPage> createState() => _PrincipalApprovalsPageState();
}

class _PrincipalApprovalsPageState extends State<PrincipalApprovalsPage> {
  late Future<List<ApprovalRow>> _future;
  String _kind = 'all';
  final Set<int> _busy = <int>{};

  @override
  void initState() {
    super.initState();
    _future = locator<PrincipalRepository>().approvals();
  }

  Future<void> _refresh() async {
    setState(() {
      _future = locator<PrincipalRepository>()
          .approvals(kind: _kind == 'all' ? null : _kind);
    });
    await _future;
  }

  Future<void> _decide(ApprovalRow row, bool approve) async {
    setState(() => _busy.add(row.id));
    final ok = await locator<PrincipalRepository>().decideApproval(
      kind: row.kind,
      rowId: row.id,
      approve: approve,
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(ok
            ? (approve ? 'Approved' : 'Rejected')
            : 'Could not save decision'),
      ),
    );
    setState(() => _busy.remove(row.id));
    if (ok) await _refresh();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Approvals'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(48),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 4, 12, 10),
            child: SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'all', label: Text('All')),
                ButtonSegment(value: 'student_leave', label: Text('Student')),
                ButtonSegment(value: 'staff_leave', label: Text('Staff')),
              ],
              selected: {_kind},
              onSelectionChanged: (s) {
                setState(() => _kind = s.first);
                _refresh();
              },
            ),
          ),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<ApprovalRow>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            final rows = snap.data ?? const <ApprovalRow>[];
            if (rows.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'Inbox is empty — nothing waiting on you.',
                      style: TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                ),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: rows.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) {
                final r = rows[i];
                final busy = _busy.contains(r.id);
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 12, 8, 8),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Chip(
                              label: Text(
                                r.kind == 'staff_leave'
                                    ? 'STAFF'
                                    : 'STUDENT',
                                style: const TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 1.2,
                                ),
                              ),
                              backgroundColor: r.kind == 'staff_leave'
                                  ? const Color(0xFFE6F0FF)
                                  : JaikalkiBrand.saffronPale,
                              visualDensity: VisualDensity.compact,
                              materialTapTargetSize:
                                  MaterialTapTargetSize.shrinkWrap,
                              side: BorderSide.none,
                            ),
                            const Spacer(),
                            Text(
                              '${r.startDate}  →  ${r.endDate}',
                              style: const TextStyle(
                                fontSize: 12,
                                color: JaikalkiBrand.textSecondary,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        Text(r.title,
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              fontSize: 15,
                            )),
                        if (r.subtitle.isNotEmpty) ...[
                          const SizedBox(height: 2),
                          Text(r.subtitle,
                              style: const TextStyle(
                                fontSize: 12,
                                color: JaikalkiBrand.textSecondary,
                              )),
                        ],
                        const SizedBox(height: 8),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            TextButton.icon(
                              onPressed: busy ? null : () => _decide(r, false),
                              icon: const Icon(Icons.close,
                                  color: Color(0xFFC00000)),
                              label: const Text(
                                'Reject',
                                style: TextStyle(color: Color(0xFFC00000)),
                              ),
                            ),
                            const SizedBox(width: 4),
                            FilledButton.icon(
                              onPressed: busy ? null : () => _decide(r, true),
                              icon: busy
                                  ? const SizedBox(
                                      width: 14, height: 14,
                                      child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          color: Colors.white),
                                    )
                                  : const Icon(Icons.check),
                              label: const Text('Approve'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}
