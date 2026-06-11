import 'dart:async';

import 'package:flutter/material.dart';

import '../../api/parent_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Read-only browse of the school library catalog. Search is debounced
/// client-side so we don't hammer the backend on every keystroke; the
/// list re-fetches after 350ms of typing-quiet.
class LibraryCatalogPage extends StatefulWidget {
  const LibraryCatalogPage({super.key});

  @override
  State<LibraryCatalogPage> createState() => _LibraryCatalogPageState();
}

class _LibraryCatalogPageState extends State<LibraryCatalogPage> {
  final _controller = TextEditingController();
  Timer? _debounce;
  String _query = '';
  Future<List<LibraryBookSummary>>? _future;

  @override
  void initState() {
    super.initState();
    _future = locator<ParentRepository>().libraryCatalog();
  }

  @override
  void dispose() {
    _controller.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  void _onChanged(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () {
      if (!mounted) return;
      setState(() {
        _query = v.trim();
        _future = locator<ParentRepository>().libraryCatalog(q: _query);
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: TextField(
            controller: _controller,
            onChanged: _onChanged,
            decoration: InputDecoration(
              hintText: 'Search title, author, ISBN',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _query.isEmpty
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _controller.clear();
                        _onChanged('');
                      },
                    ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ),
        ),
        Expanded(
          child: FutureBuilder<List<LibraryBookSummary>>(
            future: _future,
            builder: (context, snap) {
              if (snap.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              final books = snap.data ?? const <LibraryBookSummary>[];
              if (books.isEmpty) {
                return Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Text(
                      _query.isEmpty
                          ? 'No books in the catalog yet.'
                          : 'No books match "$_query".',
                      style: const TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                );
              }
              return RefreshIndicator(
                onRefresh: () async {
                  setState(() {
                    _future = locator<ParentRepository>()
                        .libraryCatalog(q: _query);
                  });
                  await _future;
                },
                child: ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                  itemCount: books.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) => _BookCard(book: books[i]),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _BookCard extends StatelessWidget {
  const _BookCard({required this.book});
  final LibraryBookSummary book;

  @override
  Widget build(BuildContext context) {
    final tone = book.hasStock ? JaikalkiBrand.teal : JaikalkiBrand.textSecondary;
    return Card(
      elevation: 0,
      color: JaikalkiBrand.warmWhite,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: const BorderSide(color: JaikalkiBrand.saffronPale),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 44, height: 60,
              decoration: BoxDecoration(
                color: JaikalkiBrand.saffronPale,
                borderRadius: BorderRadius.circular(6),
              ),
              child: const Icon(Icons.menu_book_outlined,
                  color: JaikalkiBrand.saffron),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(book.title,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        color: JaikalkiBrand.indigoDark,
                      ),
                      maxLines: 2, overflow: TextOverflow.ellipsis),
                  if (book.author != null && book.author!.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text('by ${book.author!}',
                          style: const TextStyle(
                            fontSize: 12,
                            color: JaikalkiBrand.textSecondary,
                          )),
                    ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 6, runSpacing: 4,
                    children: [
                      if (book.category != null && book.category!.isNotEmpty)
                        _chip(book.category!, JaikalkiBrand.marigold),
                      if (book.language != null && book.language!.isNotEmpty)
                        _chip(book.language!, JaikalkiBrand.indigoDark),
                      _chip(
                        book.hasStock
                            ? '${book.availableCopies}/${book.totalCopies} available'
                            : 'All copies issued',
                        tone,
                      ),
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
