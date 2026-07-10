import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../api/operations_repository.dart';
import '../../core/children_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

Color _severityColor(String s) {
  switch (s) {
    case 'major':
      return const Color(0xFFC00000);
    case 'moderate':
      return JaikalkiBrand.saffronDark;
    default:
      return const Color(0xFF808080);
  }
}

/// Parent-facing discipline register for the currently-selected
/// child. Read-only — parents can see incidents but can't file
/// their own.
class ChildDisciplinePage extends StatelessWidget {
  const ChildDisciplinePage({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider.value(
      value: locator<ChildrenCubit>(),
      child: Scaffold(
        appBar: AppBar(title: const Text('Discipline register')),
        body: BlocBuilder<ChildrenCubit, ChildrenState>(
          builder: (context, state) {
            if (state is! ChildrenLoaded || state.selectedId == null) {
              return const Center(
                child: Text('Pick a child first from the top bar.'),
              );
            }
            return _Feed(studentId: state.selectedId!);
          },
        ),
      ),
    );
  }
}

class _Feed extends StatefulWidget {
  const _Feed({required this.studentId});
  final int studentId;

  @override
  State<_Feed> createState() => _FeedState();
}

class _FeedState extends State<_Feed> {
  late Future<List<DisciplineRow>> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<OperationsRepository>().childDiscipline(widget.studentId);
  }

  @override
  void didUpdateWidget(covariant _Feed old) {
    super.didUpdateWidget(old);
    if (old.studentId != widget.studentId) {
      _future = locator<OperationsRepository>().childDiscipline(widget.studentId);
    }
  }

  Future<void> _refresh() async {
    setState(() {
      _future = locator<OperationsRepository>().childDiscipline(widget.studentId);
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<List<DisciplineRow>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final rows = snap.data ?? const <DisciplineRow>[];
          if (rows.isEmpty) {
            return ListView(children: const [
              SizedBox(height: 160),
              Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'No incidents on file. Everything is quiet.',
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
              final tone = _severityColor(r.severity);
              return Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: tone.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              r.severity.toUpperCase(),
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w800,
                                color: tone,
                                letterSpacing: 1,
                              ),
                            ),
                          ),
                          const Spacer(),
                          Text(
                            r.occurredOn,
                            style: const TextStyle(
                              fontSize: 11,
                              color: JaikalkiBrand.textSecondary,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        r.headline,
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 15,
                        ),
                      ),
                      if (r.location != null && r.location!.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: 2),
                          child: Text(
                            'At ${r.location}',
                            style: const TextStyle(
                              fontSize: 12,
                              color: JaikalkiBrand.textSecondary,
                            ),
                          ),
                        ),
                      if (r.description != null && r.description!.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: 8),
                          child: Text(r.description!),
                        ),
                      if (r.actionTaken != null && r.actionTaken!.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: JaikalkiBrand.saffronPale,
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.gavel_outlined,
                                  size: 14, color: JaikalkiBrand.saffronDarker),
                              const SizedBox(width: 6),
                              Expanded(
                                child: Text(
                                  r.actionTaken!,
                                  style: const TextStyle(
                                    fontSize: 12,
                                    color: JaikalkiBrand.saffronDarker,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
