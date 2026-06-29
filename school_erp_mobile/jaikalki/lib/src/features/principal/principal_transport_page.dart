import 'package:flutter/material.dart';

import '../../api/principal_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Fleet glance for the principal — quick counts of scheduled,
/// in-progress, completed and cancelled trips for today.
class PrincipalTransportPage extends StatefulWidget {
  const PrincipalTransportPage({super.key});

  @override
  State<PrincipalTransportPage> createState() => _PrincipalTransportPageState();
}

class _PrincipalTransportPageState extends State<PrincipalTransportPage> {
  late Future<FleetStatus?> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<PrincipalRepository>().fleetStatus();
  }

  Future<void> _refresh() async {
    setState(() {
      _future = locator<PrincipalRepository>().fleetStatus();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Transport')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<FleetStatus?>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            final s = snap.data;
            if (s == null) {
              return const Center(child: Text('Could not load fleet status.'));
            }
            return ListView(
              padding: const EdgeInsets.all(12),
              children: [
                Text('Today · ${s.date}',
                    style: const TextStyle(
                      color: JaikalkiBrand.textSecondary,
                      fontSize: 12,
                    )),
                const SizedBox(height: 8),
                _Tile(
                  icon: Icons.directions_bus_filled,
                  label: 'In progress',
                  value: s.inProgress,
                  color: const Color(0xFF137333),
                ),
                _Tile(
                  icon: Icons.event_outlined,
                  label: 'Scheduled',
                  value: s.scheduled,
                  color: JaikalkiBrand.saffronDark,
                ),
                _Tile(
                  icon: Icons.check_circle_outline,
                  label: 'Completed',
                  value: s.completed,
                  color: JaikalkiBrand.textSecondary,
                ),
                _Tile(
                  icon: Icons.cancel_outlined,
                  label: 'Cancelled',
                  value: s.cancelled,
                  color: const Color(0xFFC00000),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _Tile extends StatelessWidget {
  const _Tile({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });
  final IconData icon;
  final String label;
  final int value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Icon(icon, color: color),
        title: Text(label),
        trailing: Text(
          '$value',
          style: TextStyle(
            fontWeight: FontWeight.w800,
            fontSize: 22,
            color: color,
          ),
        ),
      ),
    );
  }
}
