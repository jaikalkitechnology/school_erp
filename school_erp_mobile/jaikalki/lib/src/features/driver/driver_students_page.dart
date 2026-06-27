import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../api/driver_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// "Students" tab for the driver shell. Lists every student on every
/// route the driver is assigned to, with parent contact, pickup +
/// drop stops, emergency phone, and a "Not coming today" indicator.
/// Tap a row to expand and see the full coordination card.
class DriverStudentsPage extends StatefulWidget {
  const DriverStudentsPage({super.key});

  @override
  State<DriverStudentsPage> createState() => _DriverStudentsPageState();
}

class _DriverStudentsPageState extends State<DriverStudentsPage> {
  late Future<List<DriverStudent>> _future;
  String _query = '';

  @override
  void initState() {
    super.initState();
    _future = locator<DriverRepository>().students();
  }

  Future<void> _refresh() async {
    setState(() => _future = locator<DriverRepository>().students());
    await _future;
  }

  List<DriverStudent> _filter(List<DriverStudent> all) {
    if (_query.trim().isEmpty) return all;
    final q = _query.toLowerCase();
    return all
        .where((s) =>
            s.studentName.toLowerCase().contains(q) ||
            (s.parentPhone ?? '').contains(q) ||
            (s.routeName ?? '').toLowerCase().contains(q) ||
            (s.pickupStopName ?? '').toLowerCase().contains(q))
        .toList();
  }

  Map<String, List<DriverStudent>> _groupByRoute(List<DriverStudent> rows) {
    final out = <String, List<DriverStudent>>{};
    for (final s in rows) {
      final key = s.routeName ?? 'Route #${s.routeId}';
      out.putIfAbsent(key, () => []).add(s);
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Students')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<DriverStudent>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(child: CircularProgressIndicator()),
              ]);
            }
            final all = snap.data ?? const <DriverStudent>[];
            if (all.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 80),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No students allocated to your routes yet.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                ),
              ]);
            }
            final filtered = _filter(all);
            final grouped = _groupByRoute(filtered);
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
              children: [
                TextField(
                  decoration: InputDecoration(
                    hintText: 'Search by name, phone, route, stop…',
                    prefixIcon: const Icon(Icons.search),
                    filled: true,
                    fillColor: JaikalkiBrand.warmWhite,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                      borderSide:
                          const BorderSide(color: JaikalkiBrand.saffronPale),
                    ),
                  ),
                  onChanged: (v) => setState(() => _query = v),
                ),
                const SizedBox(height: 12),
                for (final entry in grouped.entries) ...[
                  Padding(
                    padding: const EdgeInsets.fromLTRB(4, 8, 4, 6),
                    child: Row(
                      children: [
                        Text(
                          entry.key.toUpperCase(),
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 1.0,
                            color: JaikalkiBrand.textSecondary,
                          ),
                        ),
                        const SizedBox(width: 6),
                        Text(
                          '· ${entry.value.length}',
                          style: const TextStyle(
                            fontSize: 11,
                            color: JaikalkiBrand.textSecondary,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                  for (final s in entry.value) ...[
                    _StudentCard(student: s),
                    const SizedBox(height: 8),
                  ],
                ],
              ],
            );
          },
        ),
      ),
    );
  }
}

class _StudentCard extends StatelessWidget {
  const _StudentCard({required this.student});
  final DriverStudent student;

  Future<void> _call(BuildContext context, String? phone) async {
    if (phone == null || phone.isEmpty) return;
    final uri = Uri(scheme: 'tel', path: phone);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    } else if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not dial $phone')),
      );
    }
  }

  Future<void> _sms(BuildContext context, String? phone) async {
    if (phone == null || phone.isEmpty) return;
    final uri = Uri(scheme: 'sms', path: phone);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  String _initials(String n) {
    final parts = n.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts[0].isEmpty) return '?';
    if (parts.length == 1) return parts[0][0].toUpperCase();
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    final hasMedical = (student.medicalConditions?.isNotEmpty ?? false) ||
        (student.allergies?.isNotEmpty ?? false);
    return Container(
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: student.skippedToday
              ? Colors.grey.shade400
              : JaikalkiBrand.saffronPale,
        ),
      ),
      child: ExpansionTile(
        tilePadding:
            const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        shape: const Border(),
        leading: CircleAvatar(
          backgroundColor: student.skippedToday
              ? Colors.grey.shade300
              : JaikalkiBrand.tealPale,
          foregroundColor: JaikalkiBrand.tealDark,
          child: Text(
            _initials(student.studentName),
            style: const TextStyle(fontWeight: FontWeight.w800),
          ),
        ),
        title: Text(
          student.studentName,
          style: TextStyle(
            fontWeight: FontWeight.w800,
            color: student.skippedToday
                ? JaikalkiBrand.textSecondary
                : JaikalkiBrand.indigoDark,
            decoration:
                student.skippedToday ? TextDecoration.lineThrough : null,
          ),
        ),
        subtitle: Text(
          [
            if (student.admissionNumber != null) student.admissionNumber!,
            if (student.rollNo != null) 'Roll ${student.rollNo}',
            if (student.pickupStopName != null)
              'Pick: ${student.pickupStopName}',
          ].where((s) => s.isNotEmpty).join(' · '),
          style: const TextStyle(
            fontSize: 11,
            color: JaikalkiBrand.textSecondary,
          ),
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (student.skippedToday)
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Text(
                  'NOT COMING',
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF555555),
                    letterSpacing: 0.4,
                  ),
                ),
              ),
            const Icon(Icons.expand_more,
                color: JaikalkiBrand.textSecondary),
          ],
        ),
        childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
        children: [
          _row('Pickup stop', student.pickupStopName),
          _row('Drop stop', student.dropStopName),
          _row('Address', student.address),
          if (hasMedical) ...[
            const SizedBox(height: 4),
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0xFFFEEFE5),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'MEDICAL',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.4,
                      color: Color(0xFFB23C1E),
                    ),
                  ),
                  if (student.allergies?.isNotEmpty ?? false)
                    Text('Allergies: ${student.allergies}',
                        style: const TextStyle(fontSize: 12)),
                  if (student.medicalConditions?.isNotEmpty ?? false)
                    Text('Conditions: ${student.medicalConditions}',
                        style: const TextStyle(fontSize: 12)),
                ],
              ),
            ),
          ],
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: student.parentPhone == null
                      ? null
                      : () => _call(context, student.parentPhone),
                  icon: const Icon(Icons.call_outlined),
                  label: Text(
                    student.parentPhone ?? 'No parent number',
                    overflow: TextOverflow.ellipsis,
                  ),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: JaikalkiBrand.tealDark,
                    side: const BorderSide(color: JaikalkiBrand.tealPale),
                  ),
                ),
              ),
              const SizedBox(width: 6),
              IconButton(
                onPressed: student.parentPhone == null
                    ? null
                    : () => _sms(context, student.parentPhone),
                icon: const Icon(Icons.sms_outlined),
                color: JaikalkiBrand.indigoDark,
              ),
            ],
          ),
          if ((student.emergencyPhone ?? '').isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: OutlinedButton.icon(
                onPressed: () => _call(context, student.emergencyPhone),
                icon: const Icon(Icons.medical_information_outlined),
                label: Text('Emergency · ${student.emergencyPhone}'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFFB23C1E),
                  side: const BorderSide(color: Color(0xFFFEC9B0)),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _row(String label, String? value) {
    if (value == null || value.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 90,
            child: Text(
              label,
              style: const TextStyle(
                fontSize: 11,
                color: JaikalkiBrand.textSecondary,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                fontSize: 12,
                color: JaikalkiBrand.indigoDark,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
