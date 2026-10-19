import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../api/driver_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Drop map — shows where each student gets dropped, the route path to
/// follow, and the driver's live position, all on one map. Pick a route
/// from the chips; tap a student (marker or the list) to centre on their
/// drop point and get turn-by-turn directions.
///
/// In-app map draws the ordered stop path (the line the bus follows) plus
/// a marker per student at their drop point; precise turn-by-turn is handed
/// off to the device's Maps app so the driver gets real road guidance.
class DriverDropMapPage extends StatefulWidget {
  const DriverDropMapPage({super.key});

  @override
  State<DriverDropMapPage> createState() => _DriverDropMapPageState();
}

class _DriverDropMapPageState extends State<DriverDropMapPage> {
  late Future<List<DriverStudent>> _studentsFuture;
  List<DriverRoute> _routes = const [];
  int? _activeRouteId;
  Future<List<TransportStopSimple>>? _stopsFuture;
  GoogleMapController? _mapController;

  @override
  void initState() {
    super.initState();
    _studentsFuture = _load();
  }

  Future<List<DriverStudent>> _load() async {
    final repo = locator<DriverRepository>();
    final students = await repo.students();
    _routes = await repo.routes();
    // Default to the first route that actually has students with a drop pin.
    _activeRouteId ??= _routes.isNotEmpty ? _routes.first.id : null;
    if (_activeRouteId != null) {
      _stopsFuture = repo.routeStops(_activeRouteId!);
    }
    return students;
  }

  @override
  void dispose() {
    _mapController?.dispose();
    super.dispose();
  }

  void _selectRoute(int routeId) {
    setState(() {
      _activeRouteId = routeId;
      _stopsFuture = locator<DriverRepository>().routeStops(routeId);
    });
  }

  /// A student's map point: drop coords first, else pickup coords.
  LatLng? _pointFor(DriverStudent s) {
    if (s.dropLat != null && s.dropLng != null) {
      return LatLng(s.dropLat!, s.dropLng!);
    }
    if (s.pickupLat != null && s.pickupLng != null) {
      return LatLng(s.pickupLat!, s.pickupLng!);
    }
    return null;
  }

  Future<void> _navigate(DriverStudent s) async {
    final p = _pointFor(s);
    Uri uri;
    if (p != null) {
      uri = Uri.parse(
        'https://www.google.com/maps/dir/?api=1'
        '&destination=${p.latitude},${p.longitude}&travelmode=driving',
      );
    } else if ((s.address ?? '').trim().isNotEmpty) {
      uri = Uri.parse(
        'https://www.google.com/maps/dir/?api=1'
        '&destination=${Uri.encodeComponent(s.address!.trim())}&travelmode=driving',
      );
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No drop location set for this student.')),
        );
      }
      return;
    }
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  Future<void> _centreOn(DriverStudent s) async {
    final p = _pointFor(s);
    if (p == null || _mapController == null) return;
    await _mapController!.animateCamera(CameraUpdate.newLatLngZoom(p, 16));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Drop map')),
      body: FutureBuilder<List<DriverStudent>>(
        future: _studentsFuture,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final all = snap.data ?? const <DriverStudent>[];
          final students = _activeRouteId == null
              ? all
              : all.where((s) => s.routeId == _activeRouteId).toList();
          final located = students.where((s) => _pointFor(s) != null).toList();

          if (all.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text(
                  'No students allocated to your routes yet.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: JaikalkiBrand.textSecondary),
                ),
              ),
            );
          }

          return Column(
            children: [
              if (_routes.length > 1)
                SizedBox(
                  height: 54,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    itemCount: _routes.length,
                    separatorBuilder: (_, __) => const SizedBox(width: 8),
                    itemBuilder: (_, i) {
                      final r = _routes[i];
                      final selected = r.id == _activeRouteId;
                      return ChoiceChip(
                        label: Text('${r.code} · ${r.name}'),
                        selected: selected,
                        onSelected: (_) => _selectRoute(r.id),
                        selectedColor: JaikalkiBrand.saffronPale,
                        labelStyle: TextStyle(
                          color: selected
                              ? JaikalkiBrand.saffronDarker
                              : JaikalkiBrand.textSecondary,
                          fontWeight: FontWeight.w600,
                        ),
                      );
                    },
                  ),
                ),
              Expanded(
                flex: 3,
                child: _MapArea(
                  located: located,
                  pointFor: _pointFor,
                  stopsFuture: _stopsFuture,
                  onMapCreated: (c) => _mapController = c,
                  onTapStudent: _navigate,
                ),
              ),
              // Bottom list — tapping a student centres the map + offers nav.
              Expanded(
                flex: 2,
                child: _StudentDropList(
                  students: students,
                  hasPoint: (s) => _pointFor(s) != null,
                  onCentre: _centreOn,
                  onNavigate: _navigate,
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _MapArea extends StatelessWidget {
  const _MapArea({
    required this.located,
    required this.pointFor,
    required this.stopsFuture,
    required this.onMapCreated,
    required this.onTapStudent,
  });

  final List<DriverStudent> located;
  final LatLng? Function(DriverStudent) pointFor;
  final Future<List<TransportStopSimple>>? stopsFuture;
  final void Function(GoogleMapController) onMapCreated;
  final Future<void> Function(DriverStudent) onTapStudent;

  @override
  Widget build(BuildContext context) {
    if (located.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            'No drop pins for this route yet.\n'
            'Ask the office to set lat/lng on the stops.',
            textAlign: TextAlign.center,
            style: TextStyle(color: JaikalkiBrand.textSecondary),
          ),
        ),
      );
    }

    final markers = <Marker>{
      for (final s in located)
        Marker(
          markerId: MarkerId('stu_${s.studentId}'),
          position: pointFor(s)!,
          infoWindow: InfoWindow(
            title: s.studentName,
            snippet: s.dropStopName != null
                ? 'Drop: ${s.dropStopName} · tap for directions'
                : 'Tap for directions',
            onTap: () => onTapStudent(s),
          ),
        ),
    };

    return FutureBuilder<List<TransportStopSimple>>(
      future: stopsFuture,
      builder: (context, stopSnap) {
        final stops = (stopSnap.data ?? const <TransportStopSimple>[])
            .where((s) => s.latitude != null && s.longitude != null)
            .toList()
          ..sort((a, b) => a.sequence.compareTo(b.sequence));
        final polylines = <Polyline>{
          if (stops.length > 1)
            Polyline(
              polylineId: const PolylineId('route_path'),
              color: JaikalkiBrand.saffron,
              width: 4,
              points: [for (final s in stops) LatLng(s.latitude!, s.longitude!)],
            ),
        };
        final first = pointFor(located.first)!;
        return GoogleMap(
          initialCameraPosition: CameraPosition(target: first, zoom: 13),
          markers: markers,
          polylines: polylines,
          myLocationEnabled: true,
          myLocationButtonEnabled: true,
          onMapCreated: onMapCreated,
        );
      },
    );
  }
}

class _StudentDropList extends StatelessWidget {
  const _StudentDropList({
    required this.students,
    required this.hasPoint,
    required this.onCentre,
    required this.onNavigate,
  });

  final List<DriverStudent> students;
  final bool Function(DriverStudent) hasPoint;
  final Future<void> Function(DriverStudent) onCentre;
  final Future<void> Function(DriverStudent) onNavigate;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: JaikalkiBrand.saffronPale)),
      ),
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 16),
        itemCount: students.length,
        separatorBuilder: (_, __) => const SizedBox(height: 6),
        itemBuilder: (_, i) {
          final s = students[i];
          final located = hasPoint(s);
          return Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: JaikalkiBrand.warmWhite,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: JaikalkiBrand.saffronPale),
            ),
            child: Row(
              children: [
                Icon(
                  located ? Icons.place : Icons.location_off_outlined,
                  size: 18,
                  color: located ? JaikalkiBrand.tealDark : JaikalkiBrand.textSecondary,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        s.studentName,
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          color: JaikalkiBrand.indigoDark,
                        ),
                      ),
                      Text(
                        s.dropStopName != null
                            ? 'Drop: ${s.dropStopName}'
                            : (s.address ?? 'No drop location set'),
                        style: const TextStyle(
                          fontSize: 11,
                          color: JaikalkiBrand.textSecondary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                if (located)
                  IconButton(
                    tooltip: 'Centre on map',
                    icon: const Icon(Icons.my_location, size: 18),
                    color: JaikalkiBrand.indigoDark,
                    onPressed: () => onCentre(s),
                  ),
                IconButton(
                  tooltip: 'Directions',
                  icon: const Icon(Icons.navigation, size: 18),
                  color: JaikalkiBrand.tealDark,
                  onPressed: () => onNavigate(s),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
