import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../api/parent_repository.dart';
import '../../core/children_cubit.dart';
import '../../core/homework_cubit.dart';
import '../../core/service_locator.dart';
import '../../core/settings_cubit.dart';
import '../../theme/brand.dart';

/// Phase 14 — homework feed (Open / Submitted / Graded) + submit screen.
class HomeworkPage extends StatefulWidget {
  const HomeworkPage({super.key});

  @override
  State<HomeworkPage> createState() => _HomeworkPageState();
}

class _HomeworkPageState extends State<HomeworkPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadForSelected());
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  void _loadForSelected() {
    final children = context.read<ChildrenCubit>().state;
    if (children is ChildrenLoaded && children.selectedId != null) {
      context.read<HomeworkCubit>().load(children.selectedId!);
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsCubit>().state;
    final s = settings.strings;

    return BlocProvider.value(
      value: locator<HomeworkCubit>(),
      child: BlocListener<ChildrenCubit, ChildrenState>(
        listenWhen: (a, b) =>
            a is ChildrenLoaded &&
            b is ChildrenLoaded &&
            a.selectedId != b.selectedId,
        listener: (context, state) => _loadForSelected(),
        child: Scaffold(
          appBar: AppBar(
            title: Text(s.tabHomework),
            bottom: TabBar(
              controller: _tabs,
              labelColor: JaikalkiBrand.saffron,
              unselectedLabelColor: JaikalkiBrand.textSecondary,
              indicatorColor: JaikalkiBrand.saffron,
              tabs: [
                Tab(text: s.hwOpen),
                Tab(text: s.hwSubmitted),
                Tab(text: s.hwGraded),
              ],
            ),
          ),
          body: BlocBuilder<HomeworkCubit, HomeworkState>(
            builder: (context, state) {
              if (state is HomeworkLoading || state is HomeworkInitial) {
                return const Center(child: CircularProgressIndicator());
              }
              if (state is HomeworkError) {
                return Padding(
                  padding: const EdgeInsets.all(16),
                  child: Text(state.message,
                      style: const TextStyle(color: Color(0xFFD32F2F))),
                );
              }
              final loaded = state as HomeworkLoaded;
              return TabBarView(
                controller: _tabs,
                children: [
                  _HomeworkList(items: loaded.open, emptyHint: s.hwNoneOpen, s: s),
                  _HomeworkList(items: loaded.submitted, emptyHint: '', s: s),
                  _HomeworkList(items: loaded.graded, emptyHint: '', s: s),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class _HomeworkList extends StatelessWidget {
  const _HomeworkList({required this.items, required this.emptyHint, required this.s});

  final List<HomeworkItem> items;
  final String emptyHint;
  final dynamic s;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(
            emptyHint,
            textAlign: TextAlign.center,
            style: const TextStyle(color: JaikalkiBrand.textSecondary),
          ),
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: () async {
        final children = context.read<ChildrenCubit>().state;
        if (children is ChildrenLoaded && children.selectedId != null) {
          await context
              .read<HomeworkCubit>()
              .refresh(children.selectedId!);
        }
      },
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        itemBuilder: (context, i) => _HomeworkCard(item: items[i], s: s),
        separatorBuilder: (_, __) => const SizedBox(height: 10),
        itemCount: items.length,
      ),
    );
  }
}

class _HomeworkCard extends StatelessWidget {
  const _HomeworkCard({required this.item, required this.s});

  final HomeworkItem item;
  final dynamic s;

  Color _statusTone(String status) {
    switch (status) {
      case 'submitted':
        return JaikalkiBrand.teal;
      case 'late':
        return JaikalkiBrand.marigold;
      case 'graded':
        return JaikalkiBrand.indigo;
      case 'missing':
        return const Color(0xFFD32F2F);
      default:
        return JaikalkiBrand.saffron;
    }
  }

  @override
  Widget build(BuildContext context) {
    final tone = _statusTone(item.submissionStatus);
    return Card(
      elevation: 0,
      color: JaikalkiBrand.warmWhite,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: JaikalkiBrand.saffronPale),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(context),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(item.title,
                        style: const TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: JaikalkiBrand.indigoDark,
                        )),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: tone.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(item.submissionStatus,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: tone,
                        )),
                  ),
                ],
              ),
              if (item.subjectName != null) ...[
                const SizedBox(height: 4),
                Text(item.subjectName!,
                    style: const TextStyle(
                      fontSize: 12,
                      color: JaikalkiBrand.textSecondary,
                    )),
              ],
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.event,
                      size: 14, color: JaikalkiBrand.textSecondary),
                  const SizedBox(width: 4),
                  Text('${s.hwDueOn} ${item.dueDate}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: JaikalkiBrand.textSecondary,
                      )),
                  if (item.maxMarks != null) ...[
                    const SizedBox(width: 12),
                    Icon(Icons.workspace_premium,
                        size: 14, color: tone),
                    const SizedBox(width: 4),
                    Text(
                      item.isGraded
                          ? '${item.marksObtained?.toStringAsFixed(0) ?? "?"} / ${item.maxMarks!.toStringAsFixed(0)}'
                          : '/ ${item.maxMarks!.toStringAsFixed(0)}',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: tone,
                      ),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _openDetail(BuildContext context) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => BlocProvider.value(
          value: context.read<HomeworkCubit>(),
          child: BlocProvider.value(
            value: context.read<ChildrenCubit>(),
            child: BlocProvider.value(
              value: context.read<SettingsCubit>(),
              child: _HomeworkDetailPage(item: item, s: s),
            ),
          ),
        ),
      ),
    );
  }
}

class _HomeworkDetailPage extends StatefulWidget {
  const _HomeworkDetailPage({required this.item, required this.s});

  final HomeworkItem item;
  final dynamic s;

  @override
  State<_HomeworkDetailPage> createState() => _HomeworkDetailPageState();
}

class _HomeworkDetailPageState extends State<_HomeworkDetailPage> {
  final _ctrl = TextEditingController();

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final item = widget.item;
    final s = widget.s;
    return Scaffold(
      appBar: AppBar(title: Text(item.title)),
      body: BlocBuilder<HomeworkCubit, HomeworkState>(
        builder: (context, state) {
          final submitting = state is HomeworkLoaded && state.submitting;
          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 40),
            children: [
              if (item.subjectName != null)
                Text(item.subjectName!,
                    style: const TextStyle(
                      fontSize: 13,
                      color: JaikalkiBrand.textSecondary,
                    )),
              const SizedBox(height: 6),
              Text(item.title,
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                    color: JaikalkiBrand.indigoDark,
                  )),
              const SizedBox(height: 10),
              Wrap(
                spacing: 12,
                children: [
                  _meta('${s.hwDueOn} ${item.dueDate}'),
                  if (item.maxMarks != null)
                    _meta('${s.hwMarks}: ${item.maxMarks!.toStringAsFixed(0)}'),
                ],
              ),
              const SizedBox(height: 18),
              if (item.description != null && item.description!.isNotEmpty)
                Text(item.description!,
                    style: const TextStyle(fontSize: 14, height: 1.5)),
              const SizedBox(height: 18),
              if (item.isGraded) ...[
                _graderCard(s),
              ] else if (item.isOpen) ...[
                TextField(
                  controller: _ctrl,
                  maxLines: 6,
                  decoration: InputDecoration(
                    hintText: s.hwAnswerHint,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: submitting ? null : () => _submit(),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: JaikalkiBrand.saffron,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    child: submitting
                        ? const SizedBox(
                            height: 18, width: 18,
                            child: CircularProgressIndicator(
                                color: Colors.white, strokeWidth: 2),
                          )
                        : Text(s.hwSubmitButton),
                  ),
                ),
              ] else
                _submittedCard(s),
            ],
          );
        },
      ),
    );
  }

  Widget _meta(String text) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: JaikalkiBrand.saffronPale,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(text,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: JaikalkiBrand.saffronDarker,
            )),
      );

  Widget _graderCard(dynamic s) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: JaikalkiBrand.tealPale,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (widget.item.marksObtained != null)
              Text(
                '${widget.item.marksObtained!.toStringAsFixed(0)} / ${widget.item.maxMarks?.toStringAsFixed(0) ?? "?"}',
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  color: JaikalkiBrand.tealDark,
                ),
              ),
            if (widget.item.feedback != null && widget.item.feedback!.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(s.hwTeacherFeedback,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: JaikalkiBrand.tealDark,
                  )),
              const SizedBox(height: 4),
              Text(widget.item.feedback!,
                  style: const TextStyle(fontSize: 13, height: 1.4)),
            ],
          ],
        ),
      );

  Widget _submittedCard(dynamic s) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: JaikalkiBrand.marigoldPale,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            const Icon(Icons.check_circle, color: JaikalkiBrand.marigold),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                widget.item.submittedAt != null
                    ? '${s.hwSubmitted}: ${widget.item.submittedAt}'
                    : s.hwSubmitted,
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
      );

  Future<void> _submit() async {
    final s = widget.s;
    final content = _ctrl.text.trim();
    if (content.isEmpty) return;
    final children = context.read<ChildrenCubit>().state;
    if (children is! ChildrenLoaded || children.selectedId == null) return;
    final ok = await context.read<HomeworkCubit>().submit(
          homeworkId: widget.item.id,
          studentId: children.selectedId!,
          content: content,
        );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(ok ? s.hwSubmitSuccess : s.hwSubmitFailed)),
    );
    if (ok) Navigator.of(context).pop();
  }
}
