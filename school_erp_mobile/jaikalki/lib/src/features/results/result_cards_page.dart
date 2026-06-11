import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../api/parent_repository.dart';
import '../../core/children_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Lists every published report card for the selected child, one per exam
/// (≈ one per term/semester). Tap a row to download + open the PDF that
/// was generated when the school admin published the card.
class ResultCardsPage extends StatefulWidget {
  const ResultCardsPage({super.key});

  @override
  State<ResultCardsPage> createState() => _ResultCardsPageState();
}

class _ResultCardsPageState extends State<ResultCardsPage> {
  Future<List<ResultCardRow>>? _future;
  int? _loadedFor;
  int? _downloadingId;

  void _reloadFor(int studentId) {
    _loadedFor = studentId;
    _future = locator<ParentRepository>().resultCards(studentId);
  }

  @override
  Widget build(BuildContext context) {
    final children = context.watch<ChildrenCubit>().state;
    if (children is! ChildrenLoaded || children.selectedId == null) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text('Select a child to view result cards.'),
        ),
      );
    }
    final selected = children.selectedId!;
    if (_loadedFor != selected) {
      _reloadFor(selected);
    }
    return FutureBuilder<List<ResultCardRow>>(
      future: _future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snap.data ?? const <ResultCardRow>[];
        if (rows.isEmpty) {
          return RefreshIndicator(
            onRefresh: () async => setState(() => _reloadFor(selected)),
            child: ListView(
              children: const [
                SizedBox(height: 80),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No result cards published yet.',
                      style: TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                ),
              ],
            ),
          );
        }
        return RefreshIndicator(
          onRefresh: () async => setState(() => _reloadFor(selected)),
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            itemCount: rows.length,
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemBuilder: (_, i) => _ResultCard(
              row: rows[i],
              isDownloading: _downloadingId == rows[i].reportCardId,
              onTap: () => _download(rows[i]),
            ),
          ),
        );
      },
    );
  }

  Future<void> _download(ResultCardRow row) async {
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _downloadingId = row.reportCardId);
    try {
      final dir = await getTemporaryDirectory();
      final localPath = '${dir.path}/result_card_${row.reportCardId}.pdf';
      await locator<ParentRepository>().downloadResultCard(
        cardId: row.reportCardId,
        savePath: localPath,
      );
      await OpenFilex.open(localPath);
    } catch (e) {
      messenger.showSnackBar(
        SnackBar(content: Text('Could not open result card: $e')),
      );
    } finally {
      if (mounted) setState(() => _downloadingId = null);
    }
  }
}

class _ResultCard extends StatelessWidget {
  const _ResultCard({
    required this.row,
    required this.isDownloading,
    required this.onTap,
  });

  final ResultCardRow row;
  final bool isDownloading;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final hasPct = row.percentage != null;
    return Card(
      elevation: 0,
      color: JaikalkiBrand.warmWhite,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: JaikalkiBrand.saffronPale),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: isDownloading ? null : onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: JaikalkiBrand.saffronPale,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Icon(Icons.picture_as_pdf_outlined,
                    color: JaikalkiBrand.saffron),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      row.examName.isEmpty ? 'Exam #${row.examId}' : row.examName,
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                        color: JaikalkiBrand.indigoDark,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Wrap(
                      spacing: 8,
                      runSpacing: 4,
                      children: [
                        if (hasPct)
                          _chip('${row.percentage!.toStringAsFixed(1)}%',
                              JaikalkiBrand.teal),
                        if (row.overallGrade != null)
                          _chip('Grade ${row.overallGrade}',
                              JaikalkiBrand.marigold),
                        if (row.rankInSection != null)
                          _chip('Rank ${row.rankInSection}',
                              JaikalkiBrand.indigoDark),
                      ],
                    ),
                    if (row.publishedAt != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                          'Published ${row.publishedAt!.split("T").first}',
                          style: const TextStyle(
                            fontSize: 11,
                            color: JaikalkiBrand.textSecondary,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              if (isDownloading)
                const SizedBox(
                  width: 20, height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              else
                const Icon(Icons.download_outlined,
                    color: JaikalkiBrand.indigoDark),
            ],
          ),
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
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: tone,
            )),
      );
}
