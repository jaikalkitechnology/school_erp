import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../api/principal_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
import 'principal_approvals_page.dart';
import 'principal_finance_page.dart';
import 'principal_staff_page.dart';
import 'principal_academics_page.dart';
import 'principal_discipline_page.dart';
import 'principal_transport_page.dart';

/// Home screen of the Principal shell. One condensed glance at:
/// today's attendance %, fees collected today/MTD, fleet status,
/// pending approvals, and discipline alerts.
class PrincipalDashboardPage extends StatefulWidget {
  const PrincipalDashboardPage({super.key});

  @override
  State<PrincipalDashboardPage> createState() => _PrincipalDashboardPageState();
}

class _PrincipalDashboardPageState extends State<PrincipalDashboardPage> {
  late Future<PrincipalDashboard?> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<PrincipalRepository>().dashboard();
  }

  Future<void> _refresh() async {
    setState(() {
      _future = locator<PrincipalRepository>().dashboard();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Today')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<PrincipalDashboard?>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            final d = snap.data;
            if (d == null) {
              return ListView(
                children: const [
                  SizedBox(height: 200),
                  Center(child: Text('Could not load dashboard.')),
                ],
              );
            }
            final inr = NumberFormat.simpleCurrency(locale: 'en_IN');
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              children: [
                _AttendanceCard(att: d.attendance),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(child: _FeesCard(fees: d.fees, inr: inr)),
                    const SizedBox(width: 12),
                    Expanded(child: _StaffCard(staff: d.staff)),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: _ApprovalsCard(
                        approvals: d.approvals,
                        onOpen: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => const PrincipalApprovalsPage(),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(child: _TransportCard(transport: d.transport)),
                  ],
                ),
                const SizedBox(height: 12),
                _AlertsCard(alerts: d.alerts),
                const SizedBox(height: 20),
                Text('Quick links',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          color: JaikalkiBrand.textSecondary,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1.1,
                        )),
                const SizedBox(height: 8),
                _QuickLinks(),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.title,
    required this.value,
    required this.icon,
    this.subtitle,
    this.color,
    this.onTap,
  });
  final String title;
  final String value;
  final String? subtitle;
  final IconData icon;
  final Color? color;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(icon, color: color ?? JaikalkiBrand.saffron, size: 18),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      title,
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: JaikalkiBrand.textSecondary,
                        letterSpacing: 1.1,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (onTap != null)
                    const Icon(Icons.chevron_right,
                        color: JaikalkiBrand.textSecondary, size: 18),
                ],
              ),
              const SizedBox(height: 10),
              Text(value,
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                  )),
              if (subtitle != null) ...[
                const SizedBox(height: 2),
                Text(
                  subtitle!,
                  style: const TextStyle(
                    fontSize: 11,
                    color: JaikalkiBrand.textSecondary,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _AttendanceCard extends StatelessWidget {
  const _AttendanceCard({required this.att});
  final AttendanceSummary att;

  @override
  Widget build(BuildContext context) {
    final ratio = att.studentsMarked == 0
        ? 0.0
        : att.studentsPresent / att.studentsMarked;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.fact_check_outlined,
                    color: JaikalkiBrand.saffron),
                const SizedBox(width: 8),
                const Text(
                  "Today's attendance",
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    color: JaikalkiBrand.textSecondary,
                    letterSpacing: 1.1,
                    fontSize: 11,
                  ),
                ),
                const Spacer(),
                Text('${att.percent.toStringAsFixed(1)}%',
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 18,
                      color: JaikalkiBrand.saffronDark,
                    )),
              ],
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: ratio.clamp(0.0, 1.0),
                minHeight: 10,
                backgroundColor: JaikalkiBrand.saffronPale,
                valueColor: const AlwaysStoppedAnimation<Color>(
                    JaikalkiBrand.saffron),
              ),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 16,
              runSpacing: 4,
              children: [
                _kvInline('Present', '${att.studentsPresent}'),
                _kvInline('Absent', '${att.studentsAbsent}'),
                _kvInline('Marked', '${att.studentsMarked}'),
                _kvInline('Total', '${att.totalStudents}'),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

Widget _kvInline(String k, String v) => Text.rich(
      TextSpan(
        children: [
          TextSpan(
            text: '$k ',
            style: const TextStyle(
              color: JaikalkiBrand.textSecondary,
              fontSize: 12,
            ),
          ),
          TextSpan(
            text: v,
            style: const TextStyle(
              fontWeight: FontWeight.w700,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );

class _FeesCard extends StatelessWidget {
  const _FeesCard({required this.fees, required this.inr});
  final FeesSummary fees;
  final NumberFormat inr;

  @override
  Widget build(BuildContext context) {
    return _StatCard(
      title: 'FEES TODAY',
      icon: Icons.payments_outlined,
      value: inr.format(fees.collectedToday),
      subtitle:
          'MTD ${inr.format(fees.collectedMtd)} · due ${inr.format(fees.outstandingTotal)}',
    );
  }
}

class _StaffCard extends StatelessWidget {
  const _StaffCard({required this.staff});
  final StaffSummary staff;
  @override
  Widget build(BuildContext context) {
    return _StatCard(
      title: 'STAFF',
      icon: Icons.badge_outlined,
      value: '${staff.total - staff.onLeaveToday} / ${staff.total}',
      subtitle: '${staff.onLeaveToday} on leave today',
    );
  }
}

class _ApprovalsCard extends StatelessWidget {
  const _ApprovalsCard({required this.approvals, required this.onOpen});
  final ApprovalsSummary approvals;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    return _StatCard(
      title: 'PENDING APPROVALS',
      icon: Icons.inbox_outlined,
      value: '${approvals.pendingTotal}',
      subtitle:
          '${approvals.pendingStudentLeaves} student · ${approvals.pendingStaffLeaves} staff',
      color: approvals.pendingTotal > 0
          ? JaikalkiBrand.saffronDark
          : JaikalkiBrand.saffron,
      onTap: onOpen,
    );
  }
}

class _TransportCard extends StatelessWidget {
  const _TransportCard({required this.transport});
  final TransportSummary transport;
  @override
  Widget build(BuildContext context) {
    return _StatCard(
      title: 'TRANSPORT',
      icon: Icons.directions_bus_filled,
      value: '${transport.tripsInProgress}',
      subtitle: 'trips on the road now',
    );
  }
}

class _AlertsCard extends StatelessWidget {
  const _AlertsCard({required this.alerts});
  final AlertsSummary alerts;

  @override
  Widget build(BuildContext context) {
    final entries = <_AlertEntry>[
      if (alerts.behaviourConcernsToday > 0)
        _AlertEntry(
          icon: Icons.warning_amber_outlined,
          title: 'Behaviour concerns today',
          value: '${alerts.behaviourConcernsToday}',
        ),
      if (alerts.overdueInvoices > 0)
        _AlertEntry(
          icon: Icons.receipt_long_outlined,
          title: 'Overdue invoices',
          value: '${alerts.overdueInvoices}',
        ),
    ];
    if (entries.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: const [
              Icon(Icons.check_circle_outline, color: Color(0xFF137333)),
              SizedBox(width: 10),
              Expanded(child: Text('No alerts today. Quiet day so far.')),
            ],
          ),
        ),
      );
    }
    return Card(
      color: const Color(0xFFFFF6E5),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
        child: Column(
          children: [
            for (final e in entries)
              ListTile(
                dense: true,
                leading: Icon(e.icon, color: JaikalkiBrand.saffronDark),
                title: Text(e.title),
                trailing: Text(
                  e.value,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 16,
                    color: JaikalkiBrand.saffronDarker,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _AlertEntry {
  const _AlertEntry({
    required this.icon,
    required this.title,
    required this.value,
  });
  final IconData icon;
  final String title;
  final String value;
}

class _QuickLinks extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final tiles = <_QuickTile>[
      _QuickTile(
        icon: Icons.fact_check_outlined,
        label: 'Academics',
        builder: (_) => const PrincipalAcademicsPage(),
      ),
      _QuickTile(
        icon: Icons.badge_outlined,
        label: 'Staff',
        builder: (_) => const PrincipalStaffPage(),
      ),
      _QuickTile(
        icon: Icons.account_balance_wallet_outlined,
        label: 'Finance',
        builder: (_) => const PrincipalFinancePage(),
      ),
      _QuickTile(
        icon: Icons.directions_bus_outlined,
        label: 'Transport',
        builder: (_) => const PrincipalTransportPage(),
      ),
      _QuickTile(
        icon: Icons.warning_amber_outlined,
        label: 'Discipline',
        builder: (_) => const PrincipalDisciplinePage(),
      ),
    ];
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        for (final t in tiles)
          SizedBox(
            width: (MediaQuery.of(context).size.width - 16 * 2 - 10 * 2) / 3,
            child: Card(
              child: InkWell(
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: t.builder),
                ),
                borderRadius: BorderRadius.circular(12),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    children: [
                      Icon(t.icon, color: JaikalkiBrand.saffron),
                      const SizedBox(height: 6),
                      Text(t.label,
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                          )),
                    ],
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _QuickTile {
  const _QuickTile({
    required this.icon,
    required this.label,
    required this.builder,
  });
  final IconData icon;
  final String label;
  final WidgetBuilder builder;
}
