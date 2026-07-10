import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../api/operations_repository.dart';
import '../../core/children_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

const _KIND_ICONS = <String, IconData>{
  'visit': Icons.healing_outlined,
  'vaccination': Icons.vaccines_outlined,
  'allergy': Icons.warning_amber_outlined,
  'note': Icons.notes_outlined,
};

/// Parent-facing health record feed for the currently-selected
/// child. Ordered chronologically, colour-coded by severity.
class ChildHealthPage extends StatelessWidget {
  const ChildHealthPage({super.key});

  @override
  Widget build(BuildContext context) {
    // Provide the ChildrenCubit ourselves so the page works whether
    // it's mounted inside the parent shell (which already provides it)
    // or pushed via MaterialPageRoute from the More menu (no ancestor
    // BlocProvider). ``BlocProvider.value`` is a no-op re-wrap when the
    // same instance is already up the tree.
    return BlocProvider.value(
      value: locator<ChildrenCubit>(),
      child: Scaffold(
        appBar: AppBar(title: const Text('Health records')),
        body: BlocBuilder<ChildrenCubit, ChildrenState>(
          builder: (context, state) {
            if (state is! ChildrenLoaded || state.selectedId == null) {
              return const Center(
                child: Text('Pick a child first from the top bar.'),
              );
            }
            return _HealthFeed(studentId: state.selectedId!);
          },
        ),
      ),
    );
  }
}

class _HealthFeed extends StatefulWidget {
  const _HealthFeed({required this.studentId});
  final int studentId;

  @override
  State<_HealthFeed> createState() => _HealthFeedState();
}

class _HealthFeedState extends State<_HealthFeed> {
  late Future<List<HealthRow>> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<OperationsRepository>().childHealth(widget.studentId);
  }

  @override
  void didUpdateWidget(covariant _HealthFeed old) {
    super.didUpdateWidget(old);
    if (old.studentId != widget.studentId) {
      _future = locator<OperationsRepository>().childHealth(widget.studentId);
    }
  }

  Future<void> _refresh() async {
    setState(() {
      _future = locator<OperationsRepository>().childHealth(widget.studentId);
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<List<HealthRow>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final rows = snap.data ?? const <HealthRow>[];
          if (rows.isEmpty) {
            return ListView(children: const [
              SizedBox(height: 160),
              Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'No health records on file yet.',
                    textAlign: TextAlign.center,
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
              return Card(
                child: ExpansionTile(
                  leading: Icon(
                    _KIND_ICONS[r.kind] ?? Icons.healing,
                    color: _severityColor(r.severity),
                  ),
                  title: Text(
                    r.title,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  subtitle: Text('${r.occurredOn} · ${r.kind}'),
                  childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                  children: [
                    if (r.description != null && r.description!.isNotEmpty)
                      _kv('Description', r.description!),
                    if (r.severity != null && r.severity!.isNotEmpty)
                      _kv('Severity', r.severity!),
                    if (r.treatment != null && r.treatment!.isNotEmpty)
                      _kv('Treatment', r.treatment!),
                    if (r.medication != null && r.medication!.isNotEmpty)
                      _kv('Medication', r.medication!),
                    if (r.followUpOn != null && r.followUpOn!.isNotEmpty)
                      _kv('Follow-up', r.followUpOn!),
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }

  Widget _kv(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 90,
              child: Text(
                label,
                style: const TextStyle(
                  fontSize: 11,
                  color: JaikalkiBrand.textSecondary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            Expanded(
              child: Text(
                value,
                style: const TextStyle(fontSize: 13),
              ),
            ),
          ],
        ),
      );
}

Color? _severityColor(String? severity) {
  switch (severity) {
    case 'major':
      return const Color(0xFFC00000);
    case 'moderate':
      return JaikalkiBrand.saffronDark;
    case 'minor':
      return const Color(0xFF137333);
    default:
      return JaikalkiBrand.saffron;
  }
}
