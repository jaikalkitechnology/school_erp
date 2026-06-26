import 'dart:async';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';

import '../../api/driver_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Driver mini-app baked into the existing Flutter binary. Reachable
/// from More → Driver for users holding the ``transport_manager`` (or
/// ``school_admin`` / ``principal`` / ``vice_principal`` / ``coordinator``)
/// role on the backend.
///
/// Flow:
///   1. Pick a route from the list.
///   2. Tap "Start trip" → server creates the Trip row + fires the
///      transport.bus_departed push to every parent on that route.
///   3. While the trip is live a Timer.periodic(30s) takes a foreground
///      GPS reading via `geolocator` and POSTs it to
///      /trips/{id}/ping. The geofence push hook on the backend
///      converts those into approaching / arrived events.
///   4. Tap "End trip" → server closes the trip; phase = completed.
///
/// Background ping (when the driver locks their phone) requires a
/// native foreground service which isn't shipped yet. For now the
/// driver should keep the app foregrounded for the duration of the
/// trip — same as Uber/Ola's first iterations.
class DriverPage extends StatefulWidget {
  const DriverPage({super.key});

  @override
  State<DriverPage> createState() => _DriverPageState();
}

class _DriverPageState extends State<DriverPage> {
  late Future<List<DriverRoute>> _routes;
  DriverRoute? _selectedRoute;
  DriverTrip? _activeTrip;
  Timer? _pingTimer;
  String? _lastError;
  bool _starting = false;
  bool _completing = false;
  Position? _lastPosition;

  @override
  void initState() {
    super.initState();
    _routes = locator<DriverRepository>().routes();
  }

  @override
  void dispose() {
    _pingTimer?.cancel();
    super.dispose();
  }

  Future<void> _reload() async {
    setState(() {
      _routes = locator<DriverRepository>().routes();
    });
    await _routes;
  }

  String _today() {
    final d = DateTime.now();
    return '${d.year.toString().padLeft(4, "0")}-${d.month.toString().padLeft(2, "0")}-${d.day.toString().padLeft(2, "0")}';
  }

  Future<bool> _ensureLocationPermission() async {
    final enabled = await Geolocator.isLocationServiceEnabled();
    if (!enabled) {
      setState(() => _lastError = 'Turn on phone location to start a trip.');
      return false;
    }
    var perm = await Geolocator.checkPermission();
    if (perm == LocationPermission.denied) {
      perm = await Geolocator.requestPermission();
    }
    if (perm == LocationPermission.denied ||
        perm == LocationPermission.deniedForever) {
      setState(() => _lastError =
          'Location permission denied — bus tracking needs it.');
      return false;
    }
    return true;
  }

  Future<void> _startTrip(DriverRoute route) async {
    if (!await _ensureLocationPermission()) return;
    setState(() {
      _starting = true;
      _lastError = null;
      _selectedRoute = route;
    });
    try {
      final trip = await locator<DriverRepository>().startTrip(
        routeId: route.id,
        tripDate: _today(),
      );
      setState(() => _activeTrip = trip);
      _ping(); // fire a first ping immediately
      _pingTimer = Timer.periodic(
        const Duration(seconds: 30), (_) => _ping(),
      );
    } catch (e) {
      setState(() => _lastError = 'Could not start trip: $e');
    } finally {
      if (mounted) setState(() => _starting = false);
    }
  }

  Future<void> _ping() async {
    final trip = _activeTrip;
    if (trip == null) return;
    try {
      final pos = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 8),
        ),
      );
      _lastPosition = pos;
      await locator<DriverRepository>().pingTrip(
        tripId: trip.id,
        lat: pos.latitude,
        lng: pos.longitude,
        speedKph: pos.speed * 3.6, // m/s → km/h
      );
      if (mounted) setState(() => _lastError = null);
    } catch (e) {
      if (mounted) {
        setState(() => _lastError = 'Last ping failed: $e');
      }
    }
  }

  Future<void> _endTrip() async {
    final trip = _activeTrip;
    if (trip == null) return;
    setState(() => _completing = true);
    _pingTimer?.cancel();
    _pingTimer = null;
    try {
      await locator<DriverRepository>().completeTrip(tripId: trip.id);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Trip completed.')),
      );
      setState(() {
        _activeTrip = null;
        _selectedRoute = null;
      });
    } catch (e) {
      setState(() => _lastError = 'Could not complete trip: $e');
    } finally {
      if (mounted) setState(() => _completing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Driver')),
      body: RefreshIndicator(
        onRefresh: _reload,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
          children: [
            if (_activeTrip != null)
              _LiveTripCard(
                trip: _activeTrip!,
                position: _lastPosition,
                onEnd: _completing ? null : _endTrip,
                completing: _completing,
              )
            else
              FutureBuilder<List<DriverRoute>>(
                future: _routes,
                builder: (context, snap) {
                  if (snap.connectionState != ConnectionState.done) {
                    return const Padding(
                      padding: EdgeInsets.symmetric(vertical: 40),
                      child: Center(child: CircularProgressIndicator()),
                    );
                  }
                  final routes = snap.data ?? const <DriverRoute>[];
                  if (routes.isEmpty) {
                    return const Padding(
                      padding: EdgeInsets.symmetric(vertical: 40),
                      child: Center(
                        child: Text(
                          "No routes assigned.\n"
                          "Speak to the school office to be linked to a route.",
                          textAlign: TextAlign.center,
                          style: TextStyle(color: JaikalkiBrand.textSecondary),
                        ),
                      ),
                    );
                  }
                  return Column(
                    children: [
                      for (final r in routes) ...[
                        _RouteRow(
                          route: r,
                          starting:
                              _starting && _selectedRoute?.id == r.id,
                          onStart: _starting ? null : () => _startTrip(r),
                        ),
                        const SizedBox(height: 10),
                      ],
                    ],
                  );
                },
              ),
            if (_lastError != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFFEE5DA),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFD32F2F)),
                ),
                child: Text(
                  _lastError!,
                  style: const TextStyle(
                    fontSize: 12,
                    color: Color(0xFFD32F2F),
                  ),
                ),
              ),
            ],
            const SizedBox(height: 16),
            const Text(
              'Keep the app foregrounded for the entire trip — pings stop '
              'when the phone is locked. A native background service '
              'lands in a later update.',
              style: TextStyle(
                fontSize: 11,
                color: JaikalkiBrand.textSecondary,
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RouteRow extends StatelessWidget {
  const _RouteRow({
    required this.route,
    required this.starting,
    required this.onStart,
  });
  final DriverRoute route;
  final bool starting;
  final VoidCallback? onStart;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      child: Row(
        children: [
          Container(
            width: 44, height: 44,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: JaikalkiBrand.tealPale,
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.directions_bus_outlined,
                color: JaikalkiBrand.tealDark),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${route.code} · ${route.name}',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: JaikalkiBrand.indigoDark,
                  ),
                ),
                Text(
                  '${route.studentCount} students · ${route.stopCount} stops',
                  style: const TextStyle(
                    fontSize: 11,
                    color: JaikalkiBrand.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          ElevatedButton(
            onPressed: onStart,
            style: ElevatedButton.styleFrom(
              backgroundColor: JaikalkiBrand.tealDark,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(
                  horizontal: 14, vertical: 8),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
            child: starting
                ? const SizedBox(
                    width: 14, height: 14,
                    child: CircularProgressIndicator(
                      strokeWidth: 2, color: Colors.white,
                    ),
                  )
                : const Text('Start',
                    style: TextStyle(fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
  }
}

class _LiveTripCard extends StatelessWidget {
  const _LiveTripCard({
    required this.trip,
    required this.position,
    required this.onEnd,
    required this.completing,
  });
  final DriverTrip trip;
  final Position? position;
  final VoidCallback? onEnd;
  final bool completing;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [JaikalkiBrand.tealDark, Color(0xFF0B5C57)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.22),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text(
                  'TRIP LIVE',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.8,
                  ),
                ),
              ),
              const Spacer(),
              const Text(
                'Pinging every 30s',
                style: TextStyle(
                  color: Colors.white70,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Trip #${trip.id}',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            (trip.direction ?? 'pickup').toUpperCase(),
            style: TextStyle(
              color: Colors.white.withOpacity(0.85),
              fontSize: 12,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.5,
            ),
          ),
          if (position != null) ...[
            const SizedBox(height: 10),
            Row(
              children: [
                const Icon(Icons.my_location_outlined,
                    size: 14, color: Colors.white70),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    'Last ping: ${position!.latitude.toStringAsFixed(5)}, ${position!.longitude.toStringAsFixed(5)} '
                    '· ${(position!.speed * 3.6).toStringAsFixed(0)} km/h',
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 11,
                    ),
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: onEnd,
              icon: completing
                  ? const SizedBox(
                      width: 14, height: 14,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: JaikalkiBrand.tealDark,
                      ),
                    )
                  : const Icon(Icons.flag_outlined),
              label: const Text('End trip'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: JaikalkiBrand.tealDark,
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
