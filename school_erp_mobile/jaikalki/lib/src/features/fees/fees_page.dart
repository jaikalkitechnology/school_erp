import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../api/parent_repository.dart';
import '../../core/children_cubit.dart';
import '../../core/fees_cubit.dart';
import '../../core/service_locator.dart';
import '../../core/settings_cubit.dart';
import '../../theme/brand.dart';

/// Phase 11 — invoice list + roll-up + pay-now stub.
class FeesPage extends StatefulWidget {
  const FeesPage({super.key});

  @override
  State<FeesPage> createState() => _FeesPageState();
}

class _FeesPageState extends State<FeesPage> {
  void _loadForSelected() {
    final children = context.read<ChildrenCubit>().state;
    if (children is ChildrenLoaded && children.selectedId != null) {
      context.read<FeesCubit>().load(children.selectedId!);
    }
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadForSelected());
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
                    ? const Center(child: CircularProgressIndicator())
                    : state is FeesError
                        ? _Error(message: state.message)
                        : state is FeesLoaded
                            ? _FeesBody(view: state.view, s: s)
                            : const SizedBox.shrink(),
              );
            },
          ),
        ),
      ),
    );
  }
}

class _FeesBody extends StatelessWidget {
  const _FeesBody({required this.view, required this.s});

  final ChildFeeView view;
  final dynamic s;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      children: [
        _SummaryRow(view: view, s: s),
        const SizedBox(height: 16),
        if (view.invoices.isEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 32),
            child: Center(
              child: Text(
                s.feesNoInvoices,
                style: const TextStyle(color: JaikalkiBrand.textSecondary),
              ),
            ),
          )
        else
          ...view.invoices.map(
            (inv) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _InvoiceCard(invoice: inv, s: s),
            ),
          ),
      ],
    );
  }
}

class _SummaryRow extends StatelessWidget {
  const _SummaryRow({required this.view, required this.s});

  final ChildFeeView view;
  final dynamic s;

  @override
  Widget build(BuildContext context) {
    final outstanding = view.totalDue - view.totalPaid;
    return Row(
      children: [
        Expanded(
          child: _SummaryTile(
            label: s.feesOutstanding,
            amount: outstanding,
            tone: outstanding > 0
                ? JaikalkiBrand.saffron
                : JaikalkiBrand.teal,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _SummaryTile(
            label: s.feesPaid,
            amount: view.totalPaid,
            tone: JaikalkiBrand.tealDark,
          ),
        ),
      ],
    );
  }
}

class _SummaryTile extends StatelessWidget {
  const _SummaryTile({required this.label, required this.amount, required this.tone});

  final String label;
  final double amount;
  final Color tone;

  String _formatRupees(double v) {
    final s = v.toStringAsFixed(0);
    // Indian-style 1,23,456 grouping.
    final reversed = s.split('').reversed.toList();
    final buf = StringBuffer();
    for (int i = 0; i < reversed.length; i++) {
      if (i == 3 || (i > 3 && (i - 3) % 2 == 0)) buf.write(',');
      buf.write(reversed[i]);
    }
    return buf.toString().split('').reversed.join();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: tone.withOpacity(0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: tone.withOpacity(0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.5,
                color: JaikalkiBrand.textSecondary,
              )),
          const SizedBox(height: 6),
          Text('₹${_formatRupees(amount)}',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: tone,
              )),
        ],
      ),
    );
  }
}

class _InvoiceCard extends StatelessWidget {
  const _InvoiceCard({required this.invoice, required this.s});

  final FeeInvoice invoice;
  final dynamic s;

  Color _statusColor(String status) {
    switch (status) {
      case 'paid':
        return JaikalkiBrand.teal;
      case 'partial':
        return JaikalkiBrand.marigold;
      case 'overdue':
        return const Color(0xFFD32F2F);
      case 'cancelled':
        return Colors.grey;
      default:
        return JaikalkiBrand.saffron;
    }
  }

  @override
  Widget build(BuildContext context) {
    final tone = _statusColor(invoice.status);
    return Card(
      elevation: 0,
      color: JaikalkiBrand.warmWhite,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: JaikalkiBrand.saffronPale),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(invoice.categoryName ?? invoice.invoiceNumber,
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            color: JaikalkiBrand.indigoDark,
                          )),
                      const SizedBox(height: 2),
                      Text(
                        '${invoice.periodStart} → ${invoice.periodEnd}',
                        style: const TextStyle(
                          fontSize: 11,
                          color: JaikalkiBrand.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: tone.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(invoice.status,
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: tone,
                      )),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${s.feesDueOn} ${invoice.dueDate}',
                        style: const TextStyle(
                          fontSize: 11,
                          color: JaikalkiBrand.textSecondary,
                        )),
                    const SizedBox(height: 2),
                    Text('₹${invoice.totalAmount.toStringAsFixed(0)}',
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          color: JaikalkiBrand.indigoDark,
                        )),
                  ],
                ),
                if (!invoice.isPaid)
                  ElevatedButton(
                    onPressed: () => _pay(context, invoice),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: JaikalkiBrand.saffron,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: Text(s.feesPayNow),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _pay(BuildContext context, FeeInvoice invoice) async {
    final s = context.read<SettingsCubit>().state.strings;
    final children = context.read<ChildrenCubit>().state;
    if (children is! ChildrenLoaded || children.selectedId == null) return;
    // Backend creates an order_id. Razorpay SDK launch lands when a merchant
    // account is provisioned (Phase 11 deferred — see PHASE_PROGRESS.md).
    try {
      await context.read<FeesCubit>().initiatePayment(
            invoiceId: invoice.id,
            studentId: children.selectedId!,
          );
    } catch (_) {
      // Even if the order request itself succeeds, until the gateway is
      // live there's no SDK to hand off to. Tell the parent why.
    }
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(s.paymentNotConfigured)),
    );
  }
}

class _Error extends StatelessWidget {
  const _Error({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Text(message, style: const TextStyle(color: Color(0xFFD32F2F))),
    );
  }
}
