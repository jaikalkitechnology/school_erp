import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../api/principal_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Finance snapshot — by-class collection table, top defaulters, and
/// a last-30-days collection sparkline.
class PrincipalFinancePage extends StatefulWidget {
  const PrincipalFinancePage({super.key});

  @override
  State<PrincipalFinancePage> createState() => _PrincipalFinancePageState();
}

class _PrincipalFinancePageState extends State<PrincipalFinancePage> {
  late Future<FinanceSnapshot?> _future;
  final _inr = NumberFormat.simpleCurrency(locale: 'en_IN');

  @override
  void initState() {
    super.initState();
    _future = locator<PrincipalRepository>().financeSnapshot();
  }

  Future<void> _refresh() async {
    setState(() {
      _future = locator<PrincipalRepository>().financeSnapshot();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Finance')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<FinanceSnapshot?>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            final s = snap.data;
            if (s == null) {
              return const Center(child: Text('Could not load finance.'));
            }
            return ListView(
              padding: const EdgeInsets.all(12),
              children: [
                _SeriesCard(points: s.dailyCollection, inr: _inr),
                const SizedBox(height: 12),
                _SectionTitle('Collection by class'),
                if (s.byClass.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(12),
                    child: Text('No fee invoices yet.'),
                  )
                else
                  Card(
                    child: Column(
                      children: [
                        for (final c in s.byClass) ...[
                          ListTile(
                            dense: true,
                            title: Text(c.name,
                                style: const TextStyle(
                                    fontWeight: FontWeight.w700)),
                            subtitle: Text(
                              'Billed ${_inr.format(c.billed)} · '
                              'Outstanding ${_inr.format(c.outstanding)}',
                              style: const TextStyle(fontSize: 11),
                            ),
                            trailing: Text(
                              _inr.format(c.collected),
                              style: const TextStyle(
                                fontWeight: FontWeight.w800,
                                color: JaikalkiBrand.saffronDarker,
                              ),
                            ),
                          ),
                          if (c != s.byClass.last) const Divider(height: 1),
                        ],
                      ],
                    ),
                  ),
                const SizedBox(height: 12),
                _SectionTitle('Top defaulters'),
                if (s.topDefaulters.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(12),
                    child: Text('No defaulters — every fee is on time.'),
                  )
                else
                  Card(
                    child: Column(
                      children: [
                        for (final d in s.topDefaulters) ...[
                          ListTile(
                            dense: true,
                            leading: CircleAvatar(
                              backgroundColor: const Color(0xFFFFE5E5),
                              foregroundColor: const Color(0xFFC00000),
                              child: Text(
                                d.fullName.isEmpty
                                    ? '?'
                                    : d.fullName.characters.first
                                        .toUpperCase(),
                              ),
                            ),
                            title: Text(d.fullName),
                            subtitle: Text(d.admissionNumber ?? '',
                                style: const TextStyle(fontSize: 11)),
                            trailing: Text(
                              _inr.format(d.amountDue),
                              style: const TextStyle(
                                  fontWeight: FontWeight.w800,
                                  color: Color(0xFFC00000)),
                            ),
                          ),
                          if (d != s.topDefaulters.last)
                            const Divider(height: 1),
                        ],
                      ],
                    ),
                  ),
                const SizedBox(height: 24),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);
  final String text;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 4, 4, 8),
      child: Text(text,
          style: const TextStyle(
            fontWeight: FontWeight.w800,
            letterSpacing: 1.1,
            color: JaikalkiBrand.textSecondary,
            fontSize: 11,
          )),
    );
  }
}

class _SeriesCard extends StatelessWidget {
  const _SeriesCard({required this.points, required this.inr});
  final List<DailyCollectionPoint> points;
  final NumberFormat inr;

  @override
  Widget build(BuildContext context) {
    final total = points.fold<double>(0, (a, b) => a + b.amount);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Collection · last 30 days',
                style: TextStyle(
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.1,
                  color: JaikalkiBrand.textSecondary,
                  fontSize: 11,
                )),
            const SizedBox(height: 4),
            Text(inr.format(total),
                style: const TextStyle(
                    fontWeight: FontWeight.w800, fontSize: 22)),
            const SizedBox(height: 12),
            SizedBox(
              height: 140,
              child: points.length < 2
                  ? const Center(
                      child: Text('Not enough data to plot.',
                          style: TextStyle(
                              color: JaikalkiBrand.textSecondary)),
                    )
                  : LineChart(
                      LineChartData(
                        gridData: const FlGridData(show: false),
                        titlesData: const FlTitlesData(show: false),
                        borderData: FlBorderData(show: false),
                        lineBarsData: [
                          LineChartBarData(
                            isCurved: true,
                            color: JaikalkiBrand.saffron,
                            barWidth: 3,
                            dotData: const FlDotData(show: false),
                            belowBarData: BarAreaData(
                              show: true,
                              color: JaikalkiBrand.saffronPale,
                            ),
                            spots: [
                              for (var i = 0; i < points.length; i++)
                                FlSpot(i.toDouble(), points[i].amount),
                            ],
                          ),
                        ],
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
