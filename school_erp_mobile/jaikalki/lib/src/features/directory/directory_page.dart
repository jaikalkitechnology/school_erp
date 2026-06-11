import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../api/parent_repository.dart';
import '../../core/children_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Lists the class teacher + each subject teacher attached to the
/// selected child's section. Phone/email are *not* shown — the Teacher
/// model has no visibility flag yet, so the backend deliberately omits
/// them. Adding contact info is a separate, opt-in feature.
class DirectoryPage extends StatefulWidget {
  const DirectoryPage({super.key});

  @override
  State<DirectoryPage> createState() => _DirectoryPageState();
}

class _DirectoryPageState extends State<DirectoryPage> {
  Future<List<DirectoryEntry>>? _future;
  int? _loadedFor;

  void _reload(int studentId) {
    _loadedFor = studentId;
    _future = locator<ParentRepository>().directory(studentId);
  }

  @override
  Widget build(BuildContext context) {
    final children = context.watch<ChildrenCubit>().state;
    if (children is! ChildrenLoaded || children.selectedId == null) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text('Select a child to see their teachers.'),
        ),
      );
    }
    final selected = children.selectedId!;
    if (_loadedFor != selected) {
      _reload(selected);
    }
    return FutureBuilder<List<DirectoryEntry>>(
      future: _future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? const <DirectoryEntry>[];
        if (rows.isEmpty) {
          return RefreshIndicator(
            onRefresh: () async => setState(() => _reload(selected)),
            child: ListView(
              children: const [
                SizedBox(height: 80),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No teachers assigned to your child\'s section yet.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                ),
              ],
            ),
          );
        }
        // Class teacher first, then alphabetical by name.
        final sorted = [...rows]..sort((a, b) {
            if (a.isClassTeacher != b.isClassTeacher) {
              return a.isClassTeacher ? -1 : 1;
            }
            return a.fullName.toLowerCase().compareTo(b.fullName.toLowerCase());
          });
        return RefreshIndicator(
          onRefresh: () async => setState(() => _reload(selected)),
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            itemCount: sorted.length,
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemBuilder: (_, i) => _EntryCard(entry: sorted[i]),
          ),
        );
      },
    );
  }
}

class _EntryCard extends StatelessWidget {
  const _EntryCard({required this.entry});
  final DirectoryEntry entry;

  String _initials(String name) {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts[0].isEmpty) return '?';
    if (parts.length == 1) return parts[0][0].toUpperCase();
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    final accent =
        entry.isClassTeacher ? JaikalkiBrand.saffron : JaikalkiBrand.indigoDark;
    return Card(
      elevation: 0,
      color: JaikalkiBrand.warmWhite,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: BorderSide(color: accent.withOpacity(0.3)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            CircleAvatar(
              radius: 24,
              backgroundColor: accent.withOpacity(0.15),
              foregroundColor: accent,
              child: entry.photoUrl != null && entry.photoUrl!.isNotEmpty
                  ? null
                  : Text(_initials(entry.fullName),
                      style: const TextStyle(fontWeight: FontWeight.w700)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(entry.fullName,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        color: JaikalkiBrand.indigoDark,
                      )),
                  if (entry.designation != null && entry.designation!.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(entry.designation!,
                          style: const TextStyle(
                            fontSize: 12,
                            color: JaikalkiBrand.textSecondary,
                          )),
                    ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 6, runSpacing: 4,
                    children: [
                      if (entry.isClassTeacher)
                        _chip('Class teacher', JaikalkiBrand.saffron),
                      if (entry.subjectName != null &&
                          entry.subjectName!.isNotEmpty)
                        _chip(entry.subjectName!, JaikalkiBrand.teal),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _chip(String text, Color tone) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: tone.withOpacity(0.15),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(text,
            style: TextStyle(
              fontSize: 11, fontWeight: FontWeight.w700, color: tone,
            )),
      );
}
