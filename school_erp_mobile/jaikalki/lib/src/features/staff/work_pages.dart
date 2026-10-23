import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../api/staff_work_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Work tab for the accountant / librarian / hostel warden, chosen from the
/// user's roles. Null when the roles have no work tab.
({String label, IconData icon, Widget page})? workTabFor(Set<String> roles) {
  if (roles.contains('accountant')) {
    return (label: 'Fees', icon: Icons.currency_rupee, page: const FeesWorkPage());
  }
  if (roles.contains('librarian')) {
    return (label: 'Library', icon: Icons.local_library_outlined, page: const LibraryWorkPage());
  }
  if (roles.contains('hostel_warden')) {
    return (label: 'Hostel', icon: Icons.bed_outlined, page: const HostelWorkPage());
  }
  return null;
}

final _rupees = NumberFormat.currency(locale: 'en_IN', symbol: '₹', decimalDigits: 0);
const _green = Color(0xFF0F766E);
const _red = Color(0xFFD32F2F);

StaffWorkRepository get _repo => locator<StaffWorkRepository>();

// ---- Accountant -------------------------------------------------------------

class FeesWorkPage extends StatefulWidget {
  const FeesWorkPage({super.key});

  @override
  State<FeesWorkPage> createState() => _FeesWorkPageState();
}

class _FeesWorkPageState extends State<FeesWorkPage> {
  late Future<FeesDay> _day = _repo.feesToday();

  Future<void> _refresh() async {
    setState(() => _day = _repo.feesToday());
    try {
      await _day;
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Fees')),
      body: _WorkView<FeesDay>(
        future: _day,
        onRefresh: _refresh,
        builder: (d) => [
          Row(children: [
            Expanded(child: _Stat(label: 'Collected today', value: _rupees.format(d.collectedToday), color: _green)),
            const SizedBox(width: 10),
            Expanded(child: _Stat(label: 'This month', value: _rupees.format(d.collectedMonth))),
          ]),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: _Stat(label: 'Pending', value: _rupees.format(d.pending), color: JaikalkiBrand.saffronDark)),
            const SizedBox(width: 10),
            Expanded(child: _Stat(label: 'Overdue', value: _rupees.format(d.overdue), color: _red)),
          ]),
          if (d.byMethodToday.isNotEmpty) ...[
            const SizedBox(height: 10),
            Wrap(spacing: 6, runSpacing: 6, children: [
              for (final e in d.byMethodToday.entries)
                Chip(
                  label: Text('${_method(e.key)} ${_rupees.format(e.value)}'),
                  visualDensity: VisualDensity.compact,
                  side: BorderSide.none,
                  backgroundColor: JaikalkiBrand.saffronPale,
                ),
            ]),
          ],
          const _Header('DEFAULTERS · MOST OVERDUE FIRST'),
          if (d.defaulters.isEmpty)
            const _Note(Icons.check_circle_outline, 'No overdue fees.', color: _green)
          else
            for (final r in d.defaulters)
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(r.name),
                subtitle: Text([
                  if (r.classLabel.isNotEmpty) r.classLabel,
                  'Adm ${r.admissionNumber}',
                  '${r.invoicesOverdue} invoice${r.invoicesOverdue == 1 ? '' : 's'}',
                ].join(' · ')),
                trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text(_rupees.format(r.amountOverdue),
                      style: t.titleSmall?.copyWith(color: _red, fontWeight: FontWeight.w700)),
                  if (r.parentPhone != null)
                    IconButton(
                      tooltip: 'Call parent',
                      icon: const Icon(Icons.call_outlined, color: JaikalkiBrand.saffron),
                      onPressed: () => launchUrl(Uri(scheme: 'tel', path: r.parentPhone)),
                    ),
                ]),
              ),
        ],
      ),
    );
  }
}

// ---- Librarian --------------------------------------------------------------

class LibraryWorkPage extends StatefulWidget {
  const LibraryWorkPage({super.key});

  @override
  State<LibraryWorkPage> createState() => _LibraryWorkPageState();
}

class _LibraryWorkPageState extends State<LibraryWorkPage> {
  late Future<LibraryDay> _day = _repo.libraryToday();
  final _barcode = TextEditingController();
  bool _returning = false;

  @override
  void dispose() {
    _barcode.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    setState(() => _day = _repo.libraryToday());
    try {
      await _day;
    } catch (_) {}
  }

  Future<void> _return() async {
    final code = _barcode.text.trim();
    if (code.isEmpty) return;
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _returning = true);
    try {
      final r = await _repo.returnByBarcode(code);
      _barcode.clear();
      messenger.showSnackBar(SnackBar(
        content: Text(r.fine > 0 ? 'Returned "${r.title}" · fine ${_rupees.format(r.fine)}' : 'Returned "${r.title}"'),
      ));
      await _refresh();
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _returning = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Library')),
      body: _WorkView<LibraryDay>(
        future: _day,
        onRefresh: _refresh,
        builder: (d) => [
          Row(children: [
            Expanded(child: _Stat(label: 'Issued today', value: '${d.issuedToday}')),
            const SizedBox(width: 10),
            Expanded(child: _Stat(label: 'Returned today', value: '${d.returnedToday}', color: _green)),
            const SizedBox(width: 10),
            Expanded(child: _Stat(label: 'On loan', value: '${d.onLoan}')),
          ]),
          const _Header('RETURN A BOOK'),
          Row(children: [
            Expanded(
              child: TextField(
                controller: _barcode,
                textInputAction: TextInputAction.done,
                onSubmitted: (_) => _return(),
                decoration: const InputDecoration(
                  labelText: 'Copy barcode',
                  prefixIcon: Icon(Icons.qr_code_2),
                ),
              ),
            ),
            const SizedBox(width: 8),
            FilledButton(
              style: FilledButton.styleFrom(minimumSize: const Size(96, 52)),
              onPressed: _returning ? null : _return,
              child: Text(_returning ? '…' : 'Return'),
            ),
          ]),
          _Header('OVERDUE (${d.overdue.length})'),
          if (d.overdue.isEmpty)
            const _Note(Icons.check_circle_outline, 'Nothing overdue.', color: _green)
          else
            for (final o in d.overdue)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.menu_book_outlined, color: JaikalkiBrand.saffron),
                title: Text(o.title),
                subtitle: Text('${o.borrower} · ${o.barcode}'),
                trailing: Text('${o.daysOverdue} day${o.daysOverdue == 1 ? '' : 's'} late',
                    style: const TextStyle(color: _red, fontWeight: FontWeight.w600)),
              ),
          _Header('RESERVATIONS WAITING (${d.reservations.length})'),
          if (d.reservations.isEmpty)
            const _Note(Icons.inbox_outlined, 'No reservations waiting.')
          else
            for (final r in d.reservations)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Icon(r.status == 'ready' ? Icons.bookmark_added_outlined : Icons.bookmark_border,
                    color: r.status == 'ready' ? _green : JaikalkiBrand.saffron),
                title: Text(r.title),
                subtitle: Text(r.borrower),
                trailing: Text(r.status == 'ready' ? 'Ready to collect' : 'Waiting for a copy',
                    style: TextStyle(color: r.status == 'ready' ? _green : JaikalkiBrand.textSecondary)),
              ),
        ],
      ),
    );
  }
}

// ---- Hostel warden ----------------------------------------------------------

class HostelWorkPage extends StatefulWidget {
  const HostelWorkPage({super.key});

  @override
  State<HostelWorkPage> createState() => _HostelWorkPageState();
}

class _HostelWorkPageState extends State<HostelWorkPage> {
  late Future<HostelDay> _day = _repo.hostelToday();

  Future<void> _refresh() async {
    setState(() => _day = _repo.hostelToday());
    try {
      await _day;
    } catch (_) {}
  }

  Future<void> _act(Future<void> Function() action, String done) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await action();
      messenger.showSnackBar(SnackBar(content: Text(done)));
      await _refresh();
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Hostel')),
      body: _WorkView<HostelDay>(
        future: _day,
        onRefresh: _refresh,
        builder: (d) => [
          Row(children: [
            Expanded(child: _Stat(label: 'Occupied', value: '${d.occupied}/${d.capacity}')),
            const SizedBox(width: 10),
            Expanded(child: _Stat(label: 'Free beds', value: '${d.available}', color: _green)),
            const SizedBox(width: 10),
            Expanded(child: _Stat(label: 'Away on leave', value: '${d.awayOnLeave}', color: JaikalkiBrand.saffronDark)),
          ]),
          _Header('LEAVE REQUESTS (${d.pendingLeaves.length})'),
          if (d.pendingLeaves.isEmpty)
            const _Note(Icons.check_circle_outline, 'No leave requests waiting.', color: _green)
          else
            for (final l in d.pendingLeaves)
              Card(
                margin: const EdgeInsets.only(bottom: 10),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(l.classLabel.isEmpty ? l.studentName : '${l.studentName} · ${l.classLabel}', style: t.titleMedium),
                    const SizedBox(height: 2),
                    Text('${_ymd(l.fromDate)} → ${_ymd(l.toDate)}', style: t.bodyMedium),
                    Text(l.reason, style: t.bodyMedium),
                    if (l.contactPhone != null) Text('Contact: ${l.contactPhone}', style: t.bodySmall),
                    Row(mainAxisAlignment: MainAxisAlignment.end, children: [
                      TextButton(
                        onPressed: () => _act(() => _repo.decideHostelLeave(l.id, 'rejected'), 'Leave rejected.'),
                        style: TextButton.styleFrom(foregroundColor: _red),
                        child: const Text('Reject'),
                      ),
                      const SizedBox(width: 8),
                      FilledButton(
                        style: FilledButton.styleFrom(minimumSize: const Size(96, 40)),
                        onPressed: () => _act(() => _repo.decideHostelLeave(l.id, 'approved'), 'Leave approved.'),
                        child: const Text('Approve'),
                      ),
                    ]),
                  ]),
                ),
              ),
          _Header('VISITORS IN NOW (${d.visitorsIn.length})'),
          if (d.visitorsIn.isEmpty)
            const _Note(Icons.inbox_outlined, 'No visitors checked in.')
          else
            for (final v in d.visitorsIn)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.badge_outlined, color: JaikalkiBrand.saffron),
                title: Text(v.relation == null ? v.visitorName : '${v.visitorName} (${v.relation})'),
                subtitle: Text([
                  'Visiting ${v.studentName}',
                  if (v.inAt != null) 'in at ${DateFormat('h:mm a').format(v.inAt!)}',
                ].join(' · ')),
                trailing: OutlinedButton(
                  style: OutlinedButton.styleFrom(minimumSize: const Size(96, 36)),
                  onPressed: () => _act(() => _repo.checkOutVisitor(v.id), '${v.visitorName} checked out.'),
                  child: const Text('Check out'),
                ),
              ),
        ],
      ),
    );
  }
}

// ---- Shared bits -------------------------------------------------------------

/// FutureBuilder + pull-to-refresh; an error card with Retry instead of an
/// empty page when loading fails.
class _WorkView<T> extends StatelessWidget {
  const _WorkView({required this.future, required this.onRefresh, required this.builder});

  final Future<T> future;
  final Future<void> Function() onRefresh;
  final List<Widget> Function(T data) builder;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<T>(
      future: future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        final children = snap.hasError
            ? [
                Card(
                  color: Theme.of(context).colorScheme.errorContainer,
                  child: ListTile(
                    title: const Text("Couldn't load"),
                    subtitle: Text('${snap.error}'),
                    trailing: TextButton(onPressed: onRefresh, child: const Text('Retry')),
                  ),
                ),
              ]
            : builder(snap.data as T);
        return RefreshIndicator(
          onRefresh: onRefresh,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: children,
          ),
        );
      },
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.label, required this.value, this.color = JaikalkiBrand.indigoDark});

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label.toUpperCase(), style: t.labelSmall?.copyWith(color: JaikalkiBrand.textSecondary)),
        const SizedBox(height: 6),
        FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Text(value, style: t.titleLarge?.copyWith(color: color, fontWeight: FontWeight.w700)),
        ),
      ]),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header(this.text);
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 22, bottom: 4),
        child: Text(text,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(color: JaikalkiBrand.saffronDark)),
      );
}

class _Note extends StatelessWidget {
  const _Note(this.icon, this.text, {this.color = JaikalkiBrand.textSecondary});
  final IconData icon;
  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => ListTile(
        contentPadding: EdgeInsets.zero,
        leading: Icon(icon, color: color),
        title: Text(text),
      );
}

/// Payment method code → label ("upi" → "UPI", "cash" → "Cash").
String _method(String code) {
  const acronyms = {'upi', 'neft', 'rtgs', 'imps', 'dd'};
  if (acronyms.contains(code.toLowerCase())) return code.toUpperCase();
  return code.isEmpty ? code : '${code[0].toUpperCase()}${code.substring(1)}';
}

String _ymd(String s) {
  final d = DateTime.tryParse(s);
  return d == null ? s : DateFormat('d MMM').format(d);
}
