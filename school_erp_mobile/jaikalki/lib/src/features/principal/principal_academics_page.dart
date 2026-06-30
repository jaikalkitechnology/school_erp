import 'package:flutter/material.dart';

import '../../api/principal_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Per-class attendance breakdown for the chosen day. Reuses the
/// dashboard endpoint behind the scenes — but here the principal can
/// drill in by class to find weak spots.
class PrincipalAcademicsPage extends StatefulWidget {
  const PrincipalAcademicsPage({super.key});

  @override
  State<PrincipalAcademicsPage> createState() => _PrincipalAcademicsPageState();
}

class _PrincipalAcademicsPageState extends State<PrincipalAcademicsPage> {
  DateTime _on = DateTime.now();
  late Future<AttendanceByClass?> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<PrincipalRepository>().attendanceByClass(on: _on);
  }

  Future<void> _refresh() async {
    setState(() {
      _future = locator<PrincipalRepository>().attendanceByClass(on: _on);
    });
    await _future;
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _on,
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now(),
    );
    if (picked != null) {
      setState(() => _on = picked);
      _refresh();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Academics'),
        actions: [
          IconButton(
            icon: const Icon(Icons.calendar_today_outlined),
            onPressed: _pickDate,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<AttendanceByClass?>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            final data = snap.data;
            if (data == null || data.classes.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 200),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No classes have marked attendance for this date.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                ),
              ]);
            }
            return ListView(
              padding: const EdgeInsets.all(12),
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(4, 0, 4, 8),
                  child: Text(
                    'Showing ${data.date}',
                    style: const TextStyle(
                      color: JaikalkiBrand.textSecondary,
                      fontSize: 12,
                    ),
                  ),
                ),
                ...data.classes.map((c) => _ClassRow(c: c)),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _ClassRow extends StatelessWidget {
  const _ClassRow({required this.c});
  final ClassAttendanceRow c;

  @override
  Widget build(BuildContext context) {
    final ratio = c.marked == 0 ? 0.0 : c.present / c.marked;
    final pctColor = c.percent >= 90
        ? const Color(0xFF137333)
        : c.percent >= 75
            ? JaikalkiBrand.saffronDark
            : const Color(0xFFC00000);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(c.name,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                      )),
                ),
                Text('${c.percent.toStringAsFixed(1)}%',
                    style: TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 16,
                      color: pctColor,
                    )),
              ],
            ),
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: ratio.clamp(0.0, 1.0),
                minHeight: 6,
                backgroundColor: JaikalkiBrand.saffronPale,
                valueColor: AlwaysStoppedAnimation<Color>(pctColor),
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Present ${c.present} / marked ${c.marked} / total ${c.totalStudents}',
              style: const TextStyle(
                fontSize: 12,
                color: JaikalkiBrand.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
