import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../api/operations_repository.dart';
import '../../core/children_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Parent-facing certificate register — every bonafide, TC,
/// character etc. issued for the currently-selected child.
/// Tap opens the rendered snapshot.
class ChildCertificatesPage extends StatelessWidget {
  const ChildCertificatesPage({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider.value(
      value: locator<ChildrenCubit>(),
      child: Scaffold(
        appBar: AppBar(title: const Text('Certificates')),
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
  late Future<List<CertificateRow>> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<OperationsRepository>().childCertificates(widget.studentId);
  }

  @override
  void didUpdateWidget(covariant _Feed old) {
    super.didUpdateWidget(old);
    if (old.studentId != widget.studentId) {
      _future = locator<OperationsRepository>().childCertificates(widget.studentId);
    }
  }

  Future<void> _refresh() async {
    setState(() {
      _future = locator<OperationsRepository>().childCertificates(widget.studentId);
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<List<CertificateRow>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final rows = snap.data ?? const <CertificateRow>[];
          if (rows.isEmpty) {
            return ListView(children: const [
              SizedBox(height: 160),
              Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Text(
                    'No certificates issued yet.',
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
                child: ListTile(
                  leading: const Icon(Icons.workspace_premium_outlined,
                      color: JaikalkiBrand.saffron),
                  title: Text(
                    r.templateCode.toUpperCase().replaceAll('_', ' '),
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  subtitle: Text(
                    'Ref ${r.referenceNo} · Issued ${r.issuedOn}',
                    style: const TextStyle(fontSize: 12),
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => _CertificateViewer(row: r),
                    ),
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

class _CertificateViewer extends StatelessWidget {
  const _CertificateViewer({required this.row});
  final CertificateRow row;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(row.referenceNo)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: JaikalkiBrand.saffronPale),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                row.forName,
                style: const TextStyle(
                  fontWeight: FontWeight.w700,
                  fontSize: 18,
                ),
              ),
              const SizedBox(height: 12),
              // Render HTML-ish content as plain text. A full HTML
              // renderer (flutter_html) is overkill for our
              // handful of certificate templates and adds a big
              // dep — stripping tags client-side is enough.
              Text(
                _stripHtml(row.renderedBody),
                style: const TextStyle(fontSize: 14, height: 1.6),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

String _stripHtml(String html) {
  return html
      .replaceAll(RegExp(r'<br\s*/?>', caseSensitive: false), '\n')
      .replaceAll(RegExp(r'<[^>]+>'), '')
      .replaceAll('&nbsp;', ' ')
      .replaceAll('&amp;', '&')
      .trim();
}
