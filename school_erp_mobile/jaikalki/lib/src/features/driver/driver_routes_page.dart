import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../api/driver_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// "Routes" tab for the driver shell. Lists every route the driver is
/// assigned to with its bus reg, student count, stop count, and a
/// tappable stop sequence (lat/lng deep-links to Google Maps).
class DriverRoutesPage extends StatefulWidget {
  const DriverRoutesPage({super.key});

  @override
  State<DriverRoutesPage> createState() => _DriverRoutesPageState();
}

class _DriverRoutesPageState extends State<DriverRoutesPage> {
  late Future<List<DriverRoute>> _future;
  int? _expandedRouteId;
  Future<List<TransportStopSimple>>? _stopsFuture;

  @override
  void initState() {
    super.initState();
    _future = locator<DriverRepository>().routes();
  }

  Future<void> _refresh() async {
    setState(() {
      _future = locator<DriverRepository>().routes();
      _expandedRouteId = null;
      _stopsFuture = null;
    });
    await _future;
  }

  void _toggle(int routeId) {
    setState(() {
      if (_expandedRouteId == routeId) {
        _expandedRouteId = null;
        _stopsFuture = null;
      } else {
        _expandedRouteId = routeId;
        _stopsFuture = locator<DriverRepository>().routeStops(routeId);
      }
    });
  }

  Future<void> _openInMaps(double lat, double lng) async {
    final uri = Uri.parse('https://maps.google.com/?q=$lat,$lng');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Routes')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<DriverRoute>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return ListView(children: const [
                SizedBox(height: 120),
                Center(child: CircularProgressIndicator()),
              ]);
            }
            final routes = snap.data ?? const <DriverRoute>[];
            if (routes.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 80),
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'No routes assigned yet.\nAsk the school office.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: JaikalkiBrand.textSecondary),
                    ),
                  ),
                ),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              itemCount: routes.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) {
                final r = routes[i];
                final expanded = _expandedRouteId == r.id;
                return _RouteCard(
                  route: r,
                  expanded: expanded,
                  onTap: () => _toggle(r.id),
                  stopsFuture: expanded ? _stopsFuture : null,
                  onOpenMaps: _openInMaps,
                );
              },
            );
          },
        ),
      ),
    );
  }
}

class _RouteCard extends StatelessWidget {
  const _RouteCard({
    required this.route,
    required this.expanded,
    required this.onTap,
    required this.stopsFuture,
    required this.onOpenMaps,
  });

  final DriverRoute route;
  final bool expanded;
  final VoidCallback onTap;
  final Future<List<TransportStopSimple>>? stopsFuture;
  final void Function(double lat, double lng) onOpenMaps;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      child: Column(
        children: [
          ListTile(
            onTap: onTap,
            leading: Container(
              width: 44, height: 44,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: JaikalkiBrand.tealPale,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.directions_bus_outlined,
                  color: JaikalkiBrand.tealDark),
            ),
            title: Text(
              '${route.code} · ${route.name}',
              style: const TextStyle(
                fontWeight: FontWeight.w800,
                color: JaikalkiBrand.indigoDark,
              ),
            ),
            subtitle: Text(
              '${route.studentCount} students · ${route.stopCount} stops',
              style: const TextStyle(
                fontSize: 11,
                color: JaikalkiBrand.textSecondary,
                fontWeight: FontWeight.w600,
              ),
            ),
            trailing: Icon(
              expanded ? Icons.expand_less : Icons.expand_more,
              color: JaikalkiBrand.textSecondary,
            ),
          ),
          if (expanded)
            FutureBuilder<List<TransportStopSimple>>(
              future: stopsFuture,
              builder: (context, snap) {
                if (snap.connectionState != ConnectionState.done) {
                  return const Padding(
                    padding: EdgeInsets.symmetric(vertical: 16),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                final stops = snap.data ?? const <TransportStopSimple>[];
                if (stops.isEmpty) {
                  return const Padding(
                    padding: EdgeInsets.symmetric(vertical: 12),
                    child: Text(
                      'No stops configured for this route yet.',
                      style: TextStyle(
                        fontSize: 12,
                        color: JaikalkiBrand.textSecondary,
                      ),
                    ),
                  );
                }
                return Padding(
                  padding: const EdgeInsets.fromLTRB(8, 0, 8, 12),
                  child: Column(
                    children: [
                      for (final s in stops)
                        ListTile(
                          dense: true,
                          leading: CircleAvatar(
                            backgroundColor:
                                JaikalkiBrand.saffronPale,
                            foregroundColor: JaikalkiBrand.saffronDark,
                            radius: 14,
                            child: Text(
                              '${s.sequence}',
                              style: const TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 12),
                            ),
                          ),
                          title: Text(s.name,
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                color: JaikalkiBrand.indigoDark,
                              )),
                          subtitle: s.scheduledArrival != null
                              ? Text('Scheduled ${s.scheduledArrival}',
                                  style: const TextStyle(
                                    fontSize: 11,
                                    color: JaikalkiBrand.textSecondary,
                                  ))
                              : null,
                          trailing: s.latitude != null && s.longitude != null
                              ? IconButton(
                                  onPressed: () =>
                                      onOpenMaps(s.latitude!, s.longitude!),
                                  icon: const Icon(Icons.map_outlined),
                                  color: JaikalkiBrand.tealDark,
                                  tooltip: 'Open in Maps',
                                )
                              : null,
                        ),
                    ],
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}
