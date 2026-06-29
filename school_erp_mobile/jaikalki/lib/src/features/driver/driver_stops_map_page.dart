import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';

import '../../api/driver_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Driver-side map of all the stops on their routes. The driver picks
/// a route from a chip row at the top and the map zooms to fit every
/// stop on that route. Each stop is a marker; tapping a marker shows
/// the stop name + scheduled arrival.
///
/// Useful when the driver wants to see the full route geometry on a
/// map (where is stop #4 vs stop #5, where's the next student going
/// to board) without leaving the app for Google Maps.
class DriverStopsMapPage extends StatefulWidget {
  const DriverStopsMapPage({super.key});

  @override
  State<DriverStopsMapPage> createState() => _DriverStopsMapPageState();
}

class _DriverStopsMapPageState extends State<DriverStopsMapPage> {
  late Future<List<DriverRoute>> _routesFuture;
  int? _activeRouteId;
  Future<List<TransportStopSimple>>? _stopsFuture;
  GoogleMapController? _mapController;

  @override
  void initState() {
    super.initState();
    _routesFuture = locator<DriverRepository>().routes();
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

  void _fitStops(List<TransportStopSimple> stops) {
    final geo = stops
        .where((s) => s.latitude != null && s.longitude != null)
        .toList();
    if (geo.isEmpty || _mapController == null) return;
    if (geo.length == 1) {
      _mapController!.animateCamera(CameraUpdate.newLatLngZoom(
        LatLng(geo.first.latitude!, geo.first.longitude!),
        15,
      ));
      return;
    }
    double south = geo.first.latitude!, north = geo.first.latitude!;
    double west = geo.first.longitude!, east = geo.first.longitude!;
    for (final s in geo) {
      south = s.latitude! < south ? s.latitude! : south;
      north = s.latitude! > north ? s.latitude! : north;
      west = s.longitude! < west ? s.longitude! : west;
      east = s.longitude! > east ? s.longitude! : east;
    }
    _mapController!.animateCamera(CameraUpdate.newLatLngBounds(
      LatLngBounds(
        southwest: LatLng(south, west),
        northeast: LatLng(north, east),
      ),
      48,
    ));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Route map')),
      body: FutureBuilder<List<DriverRoute>>(
        future: _routesFuture,
        builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          final routes = snap.data ?? const <DriverRoute>[];
          if (routes.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text(
                  'No routes assigned yet.\nAsk the school office.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: JaikalkiBrand.textSecondary),
                ),
              ),
            );
          }
          // Auto-select first route on first build.
          _activeRouteId ??= routes.first.id;
          _stopsFuture ??=
              locator<DriverRepository>().routeStops(_activeRouteId!);
          return Column(
            children: [
              SizedBox(
                height: 56,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(
                      horizontal: 16, vertical: 10),
                  itemCount: routes.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (_, i) {
                    final r = routes[i];
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
              const Divider(height: 1),
              Expanded(
                child: FutureBuilder<List<TransportStopSimple>>(
                  future: _stopsFuture,
                  builder: (context, stopSnap) {
                    if (stopSnap.connectionState != ConnectionState.done) {
                      return const Center(child: CircularProgressIndicator());
                    }
                    final stops = stopSnap.data ?? const <TransportStopSimple>[];
                    final geoStops = stops
                        .where((s) =>
                            s.latitude != null && s.longitude != null)
                        .toList();
                    if (geoStops.isEmpty) {
                      return const Center(
                        child: Padding(
                          padding: EdgeInsets.all(24),
                          child: Text(
                            'No stops with coordinates yet.\n'
                            'Ask the office to set lat/lng on the stops.',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                                color: JaikalkiBrand.textSecondary),
                          ),
                        ),
                      );
                    }
                    final markers = <Marker>{
                      for (final s in geoStops)
                        Marker(
                          markerId: MarkerId('stop_${s.id}'),
                          position: LatLng(s.latitude!, s.longitude!),
                          infoWindow: InfoWindow(
                            title: '${s.sequence}. ${s.name}',
                            snippet: s.scheduledArrival != null
                                ? 'Scheduled ${s.scheduledArrival}'
                                : null,
                          ),
                        ),
                    };
                    final polylines = <Polyline>{
                      Polyline(
                        polylineId: const PolylineId('route_line'),
                        color: JaikalkiBrand.saffron,
                        width: 4,
                        points: [
                          for (final s in geoStops)
                            LatLng(s.latitude!, s.longitude!),
                        ],
                      ),
                    };
                    return GoogleMap(
                      initialCameraPosition: CameraPosition(
                        target: LatLng(
                          geoStops.first.latitude!,
                          geoStops.first.longitude!,
                        ),
                        zoom: 13,
                      ),
                      markers: markers,
                      polylines: polylines,
                      myLocationEnabled: true,
                      myLocationButtonEnabled: true,
                      onMapCreated: (c) {
                        _mapController = c;
                        WidgetsBinding.instance.addPostFrameCallback((_) {
                          _fitStops(geoStops);
                        });
                      },
                    );
                  },
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
