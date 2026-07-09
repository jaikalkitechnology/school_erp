import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../api/operations_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Teacher's own payslip history. Each row expands to show the
/// full breakdown: basic, HRA, other, deductions, net.
class MyPayslipsPage extends StatefulWidget {
  const MyPayslipsPage({super.key});

  @override
  State<MyPayslipsPage> createState() => _MyPayslipsPageState();
}

class _MyPayslipsPageState extends State<MyPayslipsPage> {
  late Future<List<PayslipRow>> _future;
  final _inr = NumberFormat.simpleCurrency(locale: 'en_IN');

  @override
  void initState() {
    super.initState();
    _future = locator<OperationsRepository>().myPayslips();
  }

  Future<void> _refresh() async {
    setState(() {
      _future = locator<OperationsRepository>().myPayslips();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My payslips')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<PayslipRow>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            final rows = snap.data ?? const <PayslipRow>[];
            if (rows.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 160),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      "No payslips on file yet. Your first one will show here once payroll runs.",
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
                final p = rows[i];
                return Card(
                  child: ExpansionTile(
                    tilePadding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 4),
                    title: Row(
                      children: [
                        Text(
                          p.period,
                          style: const TextStyle(
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const Spacer(),
                        Text(
                          _inr.format(p.netPay),
                          style: const TextStyle(
                            fontWeight: FontWeight.w800,
                            fontSize: 16,
                            color: JaikalkiBrand.saffronDarker,
                          ),
                        ),
                      ],
                    ),
                    subtitle: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: p.status == 'paid'
                                ? const Color(0xFFE0F2E9)
                                : JaikalkiBrand.saffronPale,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            p.status.toUpperCase(),
                            style: TextStyle(
                              fontSize: 9,
                              fontWeight: FontWeight.w700,
                              letterSpacing: 1,
                              color: p.status == 'paid'
                                  ? const Color(0xFF137333)
                                  : JaikalkiBrand.saffronDarker,
                            ),
                          ),
                        ),
                        if (p.paidOn != null) ...[
                          const SizedBox(width: 8),
                          Text(
                            'Paid ${p.paidOn}',
                            style: const TextStyle(
                              fontSize: 11,
                              color: JaikalkiBrand.textSecondary,
                            ),
                          ),
                        ],
                      ],
                    ),
                    children: [
                      Padding(
                        padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
                        child: Column(
                          children: [
                            _row('Basic', p.basic),
                            _row('HRA', p.hra),
                            _row('Other earnings', p.otherEarnings),
                            const Divider(),
                            _row('Total deductions', -p.totalDeductions,
                                bold: false),
                            const Divider(),
                            _row('Net pay', p.netPay, bold: true),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }

  Widget _row(String label, double amount, {bool bold = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                color: bold ? JaikalkiBrand.saffronDarker : JaikalkiBrand.textSecondary,
                fontWeight: bold ? FontWeight.w800 : FontWeight.w500,
                fontSize: 13,
              ),
            ),
          ),
          Text(
            _inr.format(amount),
            style: TextStyle(
              fontWeight: bold ? FontWeight.w800 : FontWeight.w600,
              fontSize: bold ? 15 : 13,
              color: amount < 0 ? const Color(0xFFC00000) : null,
            ),
          ),
        ],
      ),
    );
  }
}
