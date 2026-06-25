import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../api/parent_repository.dart';
import '../../core/children_cubit.dart';
import '../../core/fees_cubit.dart';
import '../../core/service_locator.dart';
import '../../core/settings_cubit.dart';
import '../../theme/brand.dart';

/// Fees screen — fully redesigned to match the design spec:
///   1. Two cards side-by-side: Outstanding (with due date + last 3
///      payments mini chart), Paid (YTD + last 3 paid invoices).
///   2. Full-width "Make a Payment" CTA.
///   3. Tabs: History (filter chips + invoice list) / Analytics
///      (projected fees bar chart + Make a Payment).
class FeesPage extends StatefulWidget {
  const FeesPage({super.key});

  @override
  State<FeesPage> createState() => _FeesPageState();
}

class _FeesPageState extends State<FeesPage> {
  StreamSubscription<ChildrenState>? _childrenSub;
  int? _bootstrappedFor;

  void _loadForSelected() {
    final children = context.read<ChildrenCubit>().state;
    if (children is ChildrenLoaded && children.selectedId != null) {
      _bootstrappedFor = children.selectedId;
      context.read<FeesCubit>().load(children.selectedId!);
    }
  }

  void _maybeLoadFromState(ChildrenState s) {
    if (s is! ChildrenLoaded || s.selectedId == null) return;
    if (_bootstrappedFor == s.selectedId) return;
    _bootstrappedFor = s.selectedId;
    locator<FeesCubit>().load(s.selectedId!);
  }

  @override
  void initState() {
    super.initState();
    final children = locator<ChildrenCubit>();
    _maybeLoadFromState(children.state);
    _childrenSub = children.stream.listen(_maybeLoadFromState);
  }

  @override
  void dispose() {
    _childrenSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsCubit>().state;
    final s = settings.strings;

    return MultiBlocProvider(
      providers: [
        BlocProvider.value(value: locator<ChildrenCubit>()),
        BlocProvider.value(value: locator<FeesCubit>()),
      ],
      child: BlocListener<ChildrenCubit, ChildrenState>(
        listenWhen: (a, b) =>
            b is ChildrenLoaded &&
            b.selectedId != null &&
            (a is! ChildrenLoaded || a.selectedId != b.selectedId),
        listener: (context, state) => _loadForSelected(),
        child: Scaffold(
          appBar: AppBar(title: Text(s.tabFees)),
          body: BlocBuilder<FeesCubit, FeesState>(
            builder: (context, state) {
              return RefreshIndicator(
                onRefresh: () async {
                  final children = context.read<ChildrenCubit>().state;
                  if (children is ChildrenLoaded &&
                      children.selectedId != null) {
                    await context
                        .read<FeesCubit>()
                        .refresh(children.selectedId!);
                  }
                },
                child: state is FeesLoading
                    ? ListView(children: const [
                        SizedBox(height: 120),
                        Center(child: CircularProgressIndicator()),
                      ])
                    : state is FeesError
                        ? _Error(message: state.message)
                        : state is FeesLoaded
                            ? _FeesBody(view: state.view, s: s)
                            : const _EmptyOrLoading(),
              );
            },
          ),
        ),
      ),
    );
  }
}

// ---- Body -----------------------------------------------------------------

class _FeesBody extends StatefulWidget {
  const _FeesBody({required this.view, required this.s});
  final ChildFeeView view;
  final dynamic s;

  @override
  State<_FeesBody> createState() => _FeesBodyState();
}

enum _HistoryFilter { all, pending, paid }

class _FeesBodyState extends State<_FeesBody>
    with SingleTickerProviderStateMixin {
  late final TabController _tab = TabController(length: 2, vsync: this);
  _HistoryFilter _filter = _HistoryFilter.all;

  @override
  void dispose() {
    _tab.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      children: [
        _SummaryRow(view: widget.view),
        const SizedBox(height: 18),
        _PayCta(view: widget.view),
        const SizedBox(height: 18),
        _Tabs(controller: _tab),
        const SizedBox(height: 12),
        SizedBox(
          height: 720,
          child: TabBarView(
            controller: _tab,
            children: [
              _HistoryTab(
                view: widget.view,
                filter: _filter,
                onFilterChanged: (f) => setState(() => _filter = f),
                s: widget.s,
              ),
              _AnalyticsTab(view: widget.view, s: widget.s),
            ],
          ),
        ),
      ],
    );
  }
}

// ---- Summary cards (Outstanding + Paid) -----------------------------------

class _SummaryRow extends StatelessWidget {
  const _SummaryRow({required this.view});
  final ChildFeeView view;

  @override
  Widget build(BuildContext context) {
    final outstanding = view.totalDue - view.totalPaid;
    final unpaid =
        view.invoices.where((i) => !i.isPaid && i.balance > 0).toList()
          ..sort((a, b) => a.dueDate.compareTo(b.dueDate));
    final earliestDue =
        unpaid.isEmpty ? null : unpaid.first.dueDate;
    final paid = view.invoices.where((i) => i.isPaid).toList()
      ..sort((a, b) => b.dueDate.compareTo(a.dueDate));
    final lastPaid = paid.isEmpty ? null : paid.first;
    final last3Paid = paid.take(3).toList();
    final last3 = view.invoices.take(3).toList();
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: _OutstandingCard(
            amount: outstanding,
            earliestDue: earliestDue,
            last3: last3,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _PaidCard(
            paidYtd: view.totalPaid,
            lastPaid: lastPaid,
            last3Paid: last3Paid,
          ),
        ),
      ],
    );
  }
}

class _OutstandingCard extends StatelessWidget {
  const _OutstandingCard({
    required this.amount,
    required this.earliestDue,
    required this.last3,
  });
  final double amount;
  final String? earliestDue;
  final List<FeeInvoice> last3;

  @override
  Widget build(BuildContext context) {
    final tone = amount > 0 ? JaikalkiBrand.tealDark : JaikalkiBrand.teal;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: JaikalkiBrand.tealPale.withOpacity(0.35),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: tone.withOpacity(0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Outstanding',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: JaikalkiBrand.indigoDark,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '₹${_formatRupees(amount)}',
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              color: JaikalkiBrand.tealDark,
            ),
          ),
          const SizedBox(height: 4),
          if (earliestDue != null)
            Text(
              'Due by $earliestDue',
              style: const TextStyle(
                fontSize: 10,
                color: JaikalkiBrand.textSecondary,
                fontWeight: FontWeight.w600,
              ),
            )
          else
            const Text(
              'All clear',
              style: TextStyle(
                fontSize: 10,
                color: JaikalkiBrand.textSecondary,
                fontWeight: FontWeight.w600,
              ),
            ),
          const Divider(height: 18),
          Row(
            children: [
              const Icon(Icons.event_outlined,
                  size: 12, color: JaikalkiBrand.textSecondary),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  earliestDue == null ? 'No upcoming due' : 'Due by $earliestDue',
                  style: const TextStyle(
                    fontSize: 10,
                    color: JaikalkiBrand.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          const Text(
            'Last 3 payments',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: JaikalkiBrand.textSecondary,
            ),
          ),
          const SizedBox(height: 6),
          _MiniBarChart(invoices: last3),
        ],
      ),
    );
  }
}

class _PaidCard extends StatelessWidget {
  const _PaidCard({
    required this.paidYtd,
    required this.lastPaid,
    required this.last3Paid,
  });
  final double paidYtd;
  final FeeInvoice? lastPaid;
  final List<FeeInvoice> last3Paid;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: JaikalkiBrand.tealPale.withOpacity(0.55),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: JaikalkiBrand.tealDark.withOpacity(0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Paid',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: JaikalkiBrand.indigoDark,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '₹${_formatRupees(paidYtd)}',
            style: const TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w800,
              color: JaikalkiBrand.tealDark,
            ),
          ),
          const SizedBox(height: 2),
          const Text(
            'Total YTD',
            style: TextStyle(
              fontSize: 10,
              color: JaikalkiBrand.textSecondary,
              fontWeight: FontWeight.w600,
            ),
          ),
          const Divider(height: 18),
          if (lastPaid != null) ...[
            Text(
              'Last payment: ₹${_formatRupees(lastPaid!.totalAmount)}',
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: JaikalkiBrand.indigoDark,
              ),
            ),
            Text(
              '(${lastPaid!.dueDate})',
              style: const TextStyle(
                fontSize: 10,
                color: JaikalkiBrand.textSecondary,
              ),
            ),
            const SizedBox(height: 8),
          ],
          if (last3Paid.isNotEmpty) ...[
            const Text(
              'Last 3 paid invoices',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: JaikalkiBrand.textSecondary,
              ),
            ),
            const SizedBox(height: 4),
            for (final p in last3Paid)
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Text(
                  '${p.categoryName ?? p.invoiceNumber}: ₹${_formatRupees(p.totalAmount)} (${p.dueDate})',
                  style: const TextStyle(
                    fontSize: 10,
                    color: JaikalkiBrand.textSecondary,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
          ],
        ],
      ),
    );
  }
}

class _MiniBarChart extends StatelessWidget {
  const _MiniBarChart({required this.invoices});
  final List<FeeInvoice> invoices;

  Color _toneForCategory(String name) {
    final n = name.toLowerCase();
    if (n.contains('lab')) return JaikalkiBrand.tealDark;
    if (n.contains('event') || n.contains('special')) {
      return JaikalkiBrand.saffron;
    }
    return JaikalkiBrand.teal;
  }

  @override
  Widget build(BuildContext context) {
    if (invoices.isEmpty) {
      return Container(
        height: 50,
        alignment: Alignment.center,
        child: const Text(
          'No payments yet',
          style: TextStyle(fontSize: 10, color: JaikalkiBrand.textSecondary),
        ),
      );
    }
    final maxAmt = invoices
        .map((i) => i.totalAmount)
        .fold<double>(0, (a, b) => a > b ? a : b)
        .clamp(1.0, double.infinity);
    return SizedBox(
      height: 60,
      child: Column(
        children: [
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                for (final inv in invoices) ...[
                  Expanded(
                    child: FractionallySizedBox(
                      heightFactor: (inv.totalAmount / maxAmt).clamp(0.1, 1.0),
                      child: Container(
                        margin: const EdgeInsets.symmetric(horizontal: 2),
                        decoration: BoxDecoration(
                          color: _toneForCategory(inv.categoryName ?? ''),
                          borderRadius: const BorderRadius.vertical(
                            top: Radius.circular(4),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 4),
          Wrap(
            spacing: 6,
            runSpacing: 2,
            children: [
              _Legend(color: JaikalkiBrand.teal, label: 'Tuition'),
              _Legend(color: JaikalkiBrand.tealDark, label: 'Lab'),
              _Legend(color: JaikalkiBrand.saffron, label: 'Special Event'),
            ],
          ),
        ],
      ),
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend({required this.color, required this.label});
  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 6, height: 6,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 3),
        Text(
          label,
          style: const TextStyle(
            fontSize: 8,
            color: JaikalkiBrand.textSecondary,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

// ---- Make a Payment CTA ---------------------------------------------------

class _PayCta extends StatelessWidget {
  const _PayCta({required this.view});
  final ChildFeeView view;

  @override
  Widget build(BuildContext context) {
    final outstanding = view.totalDue - view.totalPaid;
    final enabled = outstanding > 0;
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: enabled ? () => _payFirstUnpaid(context) : null,
        icon: const Icon(Icons.account_balance_wallet_outlined),
        label: const Text(
          'Make a Payment',
          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
        ),
        style: ElevatedButton.styleFrom(
          backgroundColor: JaikalkiBrand.tealDark,
          foregroundColor: Colors.white,
          disabledBackgroundColor:
              JaikalkiBrand.tealPale.withOpacity(0.6),
          padding: const EdgeInsets.symmetric(vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(30),
          ),
        ),
      ),
    );
  }

  Future<void> _payFirstUnpaid(BuildContext context) async {
    final next = view.invoices.firstWhere(
      (i) => !i.isPaid && i.balance > 0,
      orElse: () => view.invoices.first,
    );
    final children = context.read<ChildrenCubit>().state;
    if (children is! ChildrenLoaded || children.selectedId == null) return;
    final s = context.read<SettingsCubit>().state.strings;
    try {
      await context.read<FeesCubit>().initiatePayment(
            invoiceId: next.id,
            studentId: children.selectedId!,
          );
    } catch (_) {}
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(s.paymentNotConfigured)),
    );
  }
}

// ---- Tabs -----------------------------------------------------------------

class _Tabs extends StatelessWidget {
  const _Tabs({required this.controller});
  final TabController controller;

  @override
  Widget build(BuildContext context) {
    return TabBar(
      controller: controller,
      labelColor: JaikalkiBrand.tealDark,
      unselectedLabelColor: JaikalkiBrand.textSecondary,
      indicatorColor: JaikalkiBrand.tealDark,
      indicatorWeight: 3,
      labelStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
      tabs: const [
        Tab(text: 'History'),
        Tab(text: 'Analytics'),
      ],
    );
  }
}

// ---- History tab ---------------------------------------------------------

class _HistoryTab extends StatelessWidget {
  const _HistoryTab({
    required this.view,
    required this.filter,
    required this.onFilterChanged,
    required this.s,
  });

  final ChildFeeView view;
  final _HistoryFilter filter;
  final void Function(_HistoryFilter) onFilterChanged;
  final dynamic s;

  List<FeeInvoice> _filtered() {
    switch (filter) {
      case _HistoryFilter.pending:
        return view.invoices.where((i) => !i.isPaid).toList();
      case _HistoryFilter.paid:
        return view.invoices.where((i) => i.isPaid).toList();
      case _HistoryFilter.all:
        return view.invoices;
    }
  }

  String _dateRange(List<FeeInvoice> rows) {
    if (rows.isEmpty) return '—';
    final dates = rows.map((r) => r.periodStart).where((d) => d.isNotEmpty).toList()
      ..sort();
    if (dates.isEmpty) return '—';
    final first = dates.first;
    final last = dates.last;
    return first == last ? first : '$first – $last';
  }

  @override
  Widget build(BuildContext context) {
    final rows = _filtered();
    final range = _dateRange(rows);
    return ListView(
      padding: EdgeInsets.zero,
      children: [
        Row(
          children: [
            _Chip(
              label: 'All',
              selected: filter == _HistoryFilter.all,
              onTap: () => onFilterChanged(_HistoryFilter.all),
            ),
            const SizedBox(width: 6),
            _Chip(
              label: 'Pending',
              selected: filter == _HistoryFilter.pending,
              onTap: () => onFilterChanged(_HistoryFilter.pending),
            ),
            const SizedBox(width: 6),
            _Chip(
              label: 'Paid',
              selected: filter == _HistoryFilter.paid,
              onTap: () => onFilterChanged(_HistoryFilter.paid),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            const Text(
              'Fee History',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: JaikalkiBrand.indigoDark,
              ),
            ),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: JaikalkiBrand.warmWhite,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: JaikalkiBrand.saffronPale),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    range,
                    style: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: JaikalkiBrand.indigoDark,
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Icon(Icons.event_outlined,
                      size: 14, color: JaikalkiBrand.textSecondary),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (rows.isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 32),
            child: Center(
              child: Text(
                s.feesNoInvoices,
                style: const TextStyle(color: JaikalkiBrand.textSecondary),
              ),
            ),
          )
        else
          ...rows.map(
            (inv) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _InvoiceRow(invoice: inv, s: s),
            ),
          ),
      ],
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({
    required this.label,
    required this.selected,
    required this.onTap,
  });
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: selected
              ? JaikalkiBrand.tealDark
              : JaikalkiBrand.warmWhite,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected
                ? JaikalkiBrand.tealDark
                : JaikalkiBrand.saffronPale,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: selected ? Colors.white : JaikalkiBrand.indigoDark,
            fontWeight: FontWeight.w700,
            fontSize: 13,
          ),
        ),
      ),
    );
  }
}

class _InvoiceRow extends StatelessWidget {
  const _InvoiceRow({required this.invoice, required this.s});
  final FeeInvoice invoice;
  final dynamic s;

  String _statusText(String status) {
    switch (status) {
      case 'paid':
        return '(Paid)';
      case 'pending':
        return '(Pending)';
      case 'partial':
        return '(Partial)';
      case 'overdue':
        return '(Overdue)';
      default:
        return '($status)';
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'paid':
        return JaikalkiBrand.teal;
      case 'overdue':
        return const Color(0xFFD32F2F);
      case 'partial':
        return JaikalkiBrand.marigold;
      default:
        return JaikalkiBrand.saffron;
    }
  }

  String _monthYear(String iso) {
    if (iso.isEmpty || iso.length < 7) return iso;
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
    ];
    final parts = iso.split('-');
    if (parts.length < 2) return iso;
    final m = int.tryParse(parts[1]);
    if (m == null || m < 1 || m > 12) return iso;
    return '${months[m - 1]} ${parts[0]}';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: const BoxDecoration(
        border: Border(
          bottom: BorderSide(color: JaikalkiBrand.saffronPale),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _monthYear(invoice.periodStart),
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: JaikalkiBrand.indigoDark,
                  ),
                ),
                const SizedBox(height: 2),
                Wrap(
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(
                      '${invoice.categoryName ?? "Fee"} - ₹${_formatRupees(invoice.totalAmount)} ',
                      style: const TextStyle(
                        fontSize: 14,
                        color: JaikalkiBrand.indigoDark,
                      ),
                    ),
                    Text(
                      _statusText(invoice.status),
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: _statusColor(invoice.status),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          InkWell(
            onTap: () => _downloadInvoice(context, invoice),
            borderRadius: BorderRadius.circular(8),
            child: const Column(
              children: [
                Icon(Icons.picture_as_pdf_outlined,
                    size: 22, color: JaikalkiBrand.tealDark),
                SizedBox(height: 2),
                Text(
                  'Download\nPDF',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w700,
                    color: JaikalkiBrand.tealDark,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _downloadInvoice(BuildContext context, FeeInvoice invoice) async {
    final children = context.read<ChildrenCubit>().state;
    if (children is! ChildrenLoaded || children.selectedId == null) return;
    final messenger = ScaffoldMessenger.of(context);
    try {
      final dir = await getTemporaryDirectory();
      final safe =
          invoice.invoiceNumber.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');
      final localPath = '${dir.path}/invoice_$safe.pdf';
      await locator<ParentRepository>().downloadInvoicePdf(
        studentId: children.selectedId!,
        invoiceId: invoice.id,
        savePath: localPath,
      );
      await OpenFilex.open(localPath);
    } catch (e) {
      messenger.showSnackBar(
        SnackBar(content: Text('Could not open invoice: $e')),
      );
    }
  }
}

// ---- Analytics tab -------------------------------------------------------

class _AnalyticsTab extends StatelessWidget {
  const _AnalyticsTab({required this.view, required this.s});
  final ChildFeeView view;
  final dynamic s;

  /// Bucket all UNPAID invoices into their period_start month and sum
  /// the balances. We take the next 3 calendar months from "now-ish"
  /// — really, the 3 closest pending months in the data set.
  List<MapEntry<String, double>> _projectedNextThree() {
    final pending =
        view.invoices.where((i) => !i.isPaid && i.balance > 0).toList();
    final byMonth = <String, double>{};
    for (final p in pending) {
      final key = p.periodStart.length >= 7
          ? p.periodStart.substring(0, 7)
          : p.periodStart;
      byMonth[key] = (byMonth[key] ?? 0) + p.balance;
    }
    final entries = byMonth.entries.toList()
      ..sort((a, b) => a.key.compareTo(b.key));
    return entries.take(3).toList();
  }

  String _shortMonth(String yyyymm) {
    if (yyyymm.length < 7) return yyyymm;
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
    ];
    final m = int.tryParse(yyyymm.substring(5, 7));
    if (m == null || m < 1 || m > 12) return yyyymm;
    return months[m - 1];
  }

  @override
  Widget build(BuildContext context) {
    final projected = _projectedNextThree();
    final maxAmt = projected
        .map((e) => e.value)
        .fold<double>(0, (a, b) => a > b ? a : b)
        .clamp(1.0, double.infinity);
    return ListView(
      padding: EdgeInsets.zero,
      children: [
        Row(
          children: [
            const Text(
              'Projected Fees',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: JaikalkiBrand.indigoDark,
              ),
            ),
            const SizedBox(width: 4),
            const Icon(Icons.info_outline,
                size: 14, color: JaikalkiBrand.textSecondary),
          ],
        ),
        const Text(
          'for next 3 months',
          style: TextStyle(
            fontSize: 11,
            color: JaikalkiBrand.textSecondary,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: JaikalkiBrand.warmWhite,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: JaikalkiBrand.saffronPale),
          ),
          height: 240,
          child: projected.isEmpty
              ? const Center(
                  child: Text(
                    'No projected fees in the upcoming months.',
                    style: TextStyle(
                      fontSize: 12,
                      color: JaikalkiBrand.textSecondary,
                    ),
                    textAlign: TextAlign.center,
                  ),
                )
              : Column(
                  children: [
                    Expanded(
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          for (final entry in projected)
                            Expanded(
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 8),
                                child: _BarColumn(
                                  label: _shortMonth(entry.key),
                                  amount: entry.value,
                                  heightFactor:
                                      (entry.value / maxAmt).clamp(0.05, 1.0),
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 6),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: const [
                        _Legend(color: JaikalkiBrand.tealDark, label: 'Pending'),
                      ],
                    ),
                  ],
                ),
        ),
        const SizedBox(height: 16),
        _PayCta(view: view),
      ],
    );
  }
}

class _BarColumn extends StatelessWidget {
  const _BarColumn({
    required this.label,
    required this.amount,
    required this.heightFactor,
  });
  final String label;
  final double amount;
  final double heightFactor;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        Container(
          padding:
              const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
          decoration: BoxDecoration(
            color: JaikalkiBrand.indigoDark,
            borderRadius: BorderRadius.circular(6),
          ),
          child: Text(
            '₹${_formatRupees(amount)}',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 9,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        const SizedBox(height: 4),
        Expanded(
          child: FractionallySizedBox(
            heightFactor: heightFactor,
            child: Container(
              width: 28,
              decoration: BoxDecoration(
                color: JaikalkiBrand.tealDark,
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(6),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(
            fontSize: 10,
            color: JaikalkiBrand.textSecondary,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

// ---- Helpers / fallbacks --------------------------------------------------

String _formatRupees(double v) {
  final s = v.toStringAsFixed(0);
  final reversed = s.split('').reversed.toList();
  final buf = StringBuffer();
  for (int i = 0; i < reversed.length; i++) {
    if (i == 3 || (i > 3 && (i - 3) % 2 == 0)) buf.write(',');
    buf.write(reversed[i]);
  }
  return buf.toString().split('').reversed.join();
}

class _Error extends StatelessWidget {
  const _Error({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const SizedBox(height: 40),
        const Icon(Icons.error_outline,
            color: Color(0xFFD32F2F), size: 36),
        const SizedBox(height: 8),
        const Center(
          child: Text(
            'Could not load fees',
            style: TextStyle(
              color: Color(0xFFD32F2F),
              fontWeight: FontWeight.w700,
              fontSize: 15,
            ),
          ),
        ),
        const SizedBox(height: 4),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: JaikalkiBrand.textSecondary, fontSize: 12,
            ),
          ),
        ),
        const SizedBox(height: 16),
        Center(
          child: OutlinedButton.icon(
            onPressed: () {
              final children = context.read<ChildrenCubit>().state;
              if (children is ChildrenLoaded &&
                  children.selectedId != null) {
                context.read<FeesCubit>().refresh(children.selectedId!);
              }
            },
            icon: const Icon(Icons.refresh),
            label: const Text('Retry'),
          ),
        ),
      ],
    );
  }
}

class _EmptyOrLoading extends StatelessWidget {
  const _EmptyOrLoading();

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<ChildrenCubit, ChildrenState>(
      builder: (context, c) {
        if (c is ChildrenLoaded && c.children.isEmpty) {
          return ListView(
            children: const [
              SizedBox(height: 80),
              Padding(
                padding: EdgeInsets.all(24),
                child: Center(
                  child: Text(
                    'No children linked to this account yet.\n'
                    'Ask the school admin to link your child.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: JaikalkiBrand.textSecondary),
                  ),
                ),
              ),
            ],
          );
        }
        if (c is ChildrenLoaded && c.selectedId == null) {
          return ListView(
            children: const [
              SizedBox(height: 80),
              Padding(
                padding: EdgeInsets.all(24),
                child: Center(
                  child: Text(
                    'Pick a child on the dashboard to view their fees.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: JaikalkiBrand.textSecondary),
                  ),
                ),
              ),
            ],
          );
        }
        return ListView(children: const [
          SizedBox(height: 120),
          Center(child: CircularProgressIndicator()),
        ]);
      },
    );
  }
}
