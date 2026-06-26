import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../api/parent_repository.dart';
import '../../core/children_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Phase 18 — parent-facing bus tracking screen.
///
/// Three states the page can be in for the selected child:
///   1. **No allocation** — the school hasn't assigned them to a route.
///   2. **Allocated, no live trip** — show route / bus / driver / stops
///      and a "Next trip will appear here" pill.
///   3. **Allocated + trip in_progress** — show last GPS ping, ETA
///      minutes to next stop, and a Refresh button. Polls every 30 s
///      while the page is visible so the parent gets near-real-time
///      updates without us building a websocket yet.
class TransportPage extends StatefulWidget {
  const TransportPage({super.key});

  @override
  State<TransportPage> createState() => _TransportPageState();
}

class _TransportPageState extends State<TransportPage>
    with WidgetsBindingObserver {
  StreamSubscription<ChildrenState>? _childrenSub;
  Future<ChildTransport>? _future;
  int? _loadedFor;
  Timer? _poll;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    final cubit = locator<ChildrenCubit>();
    _maybeLoadFromState(cubit.state);
    _childrenSub = cubit.stream.listen(_maybeLoadFromState);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _childrenSub?.cancel();
    _poll?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Pause polling when the app is backgrounded — no point chewing
    // battery + cell data for a screen the parent can't see.
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.inactive) {
      _poll?.cancel();
    } else if (state == AppLifecycleState.resumed) {
      _restartPollIfNeeded();
    }
  }

  void _maybeLoadFromState(ChildrenState s) {
    if (s is! ChildrenLoaded || s.selectedId == null) return;
    if (_loadedFor == s.selectedId) return;
    _loadedFor = s.selectedId;
    _load(s.selectedId!);
  }

  void _load(int studentId) {
    setState(() {
      _future = locator<ParentRepository>().transport(studentId);
    });
    _future!.then((_) => _restartPollIfNeeded()).catchError((_) {});
  }

  Future<void> _refresh() async {
    final s = locator<ChildrenCubit>().state;
    if (s is ChildrenLoaded && s.selectedId != null) {
      _load(s.selectedId!);
      await _future;
    }
  }

  /// Restart the 30-second poll if the latest data shows a live trip.
  /// Idle when there's no trip in progress so we don't drain battery.
  void _restartPollIfNeeded() {
    _poll?.cancel();
    _future?.then((data) {
      if (!mounted) return;
      if (data.todayTrip?.isLive == true) {
        _poll = Timer.periodic(const Duration(seconds: 30), (_) {
          final s = locator<ChildrenCubit>().state;
          if (s is ChildrenLoaded && s.selectedId != null && mounted) {
            _load(s.selectedId!);
          }
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Transport')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: _future == null
            ? const _PickChildHint()
            : FutureBuilder<ChildTransport>(
                future: _future,
                builder: (context, snap) {
                  if (snap.connectionState != ConnectionState.done) {
                    return ListView(children: const [
                      SizedBox(height: 120),
                      Center(child: CircularProgressIndicator()),
                    ]);
                  }
                  if (snap.hasError) {
                    return ListView(children: [
                      const SizedBox(height: 40),
                      Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Text(
                            'Could not load transport: ${snap.error}',
                            textAlign: TextAlign.center,
                            style: const TextStyle(color: Color(0xFFD32F2F)),
                          ),
                        ),
                      ),
                    ]);
                  }
                  final data = snap.data!;
                  if (!data.isAllocated) {
                    return const _NotAllocated();
                  }
                  return _AllocatedView(data: data);
                },
              ),
      ),
    );
  }
}

class _PickChildHint extends StatelessWidget {
  const _PickChildHint();
  @override
  Widget build(BuildContext context) => ListView(children: const [
        SizedBox(height: 80),
        Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text(
              "Pick a child on the dashboard to see their transport.",
              textAlign: TextAlign.center,
              style: TextStyle(color: JaikalkiBrand.textSecondary),
            ),
          ),
        ),
      ]);
}

class _NotAllocated extends StatelessWidget {
  const _NotAllocated();
  @override
  Widget build(BuildContext context) => ListView(children: const [
        SizedBox(height: 60),
        Icon(Icons.directions_bus_outlined,
            size: 56, color: JaikalkiBrand.textSecondary),
        SizedBox(height: 12),
        Center(
          child: Padding(
            padding: EdgeInsets.symmetric(horizontal: 32),
            child: Text(
              "Your child isn't on the school bus yet.\n"
              "Speak to the office to assign a route and stop.",
              textAlign: TextAlign.center,
              style: TextStyle(color: JaikalkiBrand.textSecondary),
            ),
          ),
        ),
      ]);
}

class _AllocatedView extends StatefulWidget {
  const _AllocatedView({required this.data});
  final ChildTransport data;

  @override
  State<_AllocatedView> createState() => _AllocatedViewState();
}

class _AllocatedViewState extends State<_AllocatedView> {
  bool _skipping = false;

  String _today() {
    final d = DateTime.now();
    return '${d.year.toString().padLeft(4, "0")}-${d.month.toString().padLeft(2, "0")}-${d.day.toString().padLeft(2, "0")}';
  }

  Future<void> _toggleNotComingToday() async {
    final children = locator<ChildrenCubit>().state;
    if (children is! ChildrenLoaded || children.selectedId == null) return;
    setState(() => _skipping = true);
    try {
      await locator<ParentRepository>().skipTransport(
        studentId: children.selectedId!,
        skipDate: _today(),
        direction: widget.data.todayTrip?.direction ?? 'pickup',
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Driver notified. Bus will skip your stop today."),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Couldn't update: $e")),
      );
    } finally {
      if (mounted) setState(() => _skipping = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
      children: [
        _RouteHeaderCard(data: widget.data),
        const SizedBox(height: 14),
        _TripStatusCard(trip: widget.data.todayTrip),
        const SizedBox(height: 14),
        _StopsCard(pickup: widget.data.pickupStop, drop: widget.data.dropStop),
        const SizedBox(height: 14),
        _DriverCard(name: widget.data.driverName, phone: widget.data.driverPhone),
        const SizedBox(height: 14),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: _skipping ? null : _toggleNotComingToday,
            icon: _skipping
                ? const SizedBox(
                    width: 16, height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.cancel_schedule_send_outlined),
            label: const Text("Not coming today"),
            style: OutlinedButton.styleFrom(
              foregroundColor: JaikalkiBrand.saffronDark,
              side: const BorderSide(color: JaikalkiBrand.saffronPale),
              padding: const EdgeInsets.symmetric(vertical: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
          ),
        ),
        if (widget.data.feePerMonth != null && widget.data.feePerMonth! > 0) ...[
          const SizedBox(height: 14),
          _FeeCard(amount: widget.data.feePerMonth!),
        ],
      ],
    );
  }
}

class _RouteHeaderCard extends StatelessWidget {
  const _RouteHeaderCard({required this.data});
  final ChildTransport data;

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
      child: Row(
        children: [
          Container(
            width: 48, height: 48,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.18),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.directions_bus_outlined,
                color: Colors.white, size: 26),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  data.routeName ?? 'Route',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                if (data.busRegistration != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    'Bus ${data.busRegistration}',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.85),
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TripStatusCard extends StatelessWidget {
  const _TripStatusCard({required this.trip});
  final TransportTrip? trip;

  String _phaseLabel(String phase) {
    switch (phase) {
      case 'in_progress':
        return 'ON THE WAY';
      case 'scheduled':
        return 'SCHEDULED';
      case 'completed':
        return 'COMPLETED';
      case 'cancelled':
        return 'CANCELLED';
      default:
        return phase.toUpperCase();
    }
  }

  Color _phaseTone(String phase) {
    switch (phase) {
      case 'in_progress':
        return JaikalkiBrand.tealDark;
      case 'completed':
        return JaikalkiBrand.teal;
      case 'cancelled':
        return const Color(0xFFD32F2F);
      default:
        return JaikalkiBrand.marigold;
    }
  }

  String _formatTimePart(String? iso) {
    if (iso == null || iso.isEmpty) return '—';
    try {
      final dt = DateTime.parse(iso).toLocal();
      final h = dt.hour.toString().padLeft(2, '0');
      final m = dt.minute.toString().padLeft(2, '0');
      return '$h:$m';
    } catch (_) {
      return iso;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (trip == null) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: JaikalkiBrand.warmWhite,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: JaikalkiBrand.saffronPale),
        ),
        child: Row(
          children: const [
            Icon(Icons.schedule_outlined,
                color: JaikalkiBrand.textSecondary),
            SizedBox(width: 10),
            Expanded(
              child: Text(
                "No trip running right now.\n"
                "We'll show live progress here once the bus starts.",
                style: TextStyle(
                  fontSize: 12,
                  color: JaikalkiBrand.textSecondary,
                  height: 1.4,
                ),
              ),
            ),
          ],
        ),
      );
    }
    final t = trip!;
    final tone = _phaseTone(t.phase);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: tone.withOpacity(0.4), width: 1.4),
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
                  color: tone.withOpacity(0.18),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  _phaseLabel(t.phase),
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    color: tone,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
              const Spacer(),
              if (t.direction != null)
                Text(
                  t.direction!.toUpperCase(),
                  style: const TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    color: JaikalkiBrand.textSecondary,
                    letterSpacing: 0.5,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              const Icon(Icons.play_circle_outlined,
                  size: 14, color: JaikalkiBrand.textSecondary),
              const SizedBox(width: 4),
              Text(
                'Started ${_formatTimePart(t.startedAt)}',
                style: const TextStyle(
                  fontSize: 12,
                  color: JaikalkiBrand.textSecondary,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(width: 12),
              if (t.completedAt != null) ...[
                const Icon(Icons.flag_outlined,
                    size: 14, color: JaikalkiBrand.textSecondary),
                const SizedBox(width: 4),
                Text(
                  'Ended ${_formatTimePart(t.completedAt)}',
                  style: const TextStyle(
                    fontSize: 12,
                    color: JaikalkiBrand.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ],
          ),
          if (t.isLive) ...[
            const Divider(height: 18),
            if (t.nextStop != null)
              Row(
                children: [
                  const Icon(Icons.flag_circle_outlined,
                      color: JaikalkiBrand.tealDark, size: 18),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      'Next stop: ${t.nextStop!.name}',
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: JaikalkiBrand.indigoDark,
                      ),
                    ),
                  ),
                  if (t.etaMinutes != null)
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: JaikalkiBrand.tealPale,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        '~${t.etaMinutes} min',
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                          color: JaikalkiBrand.tealDark,
                        ),
                      ),
                    ),
                ],
              ),
            const SizedBox(height: 6),
            Row(
              children: [
                const Icon(Icons.speed_outlined,
                    size: 14, color: JaikalkiBrand.textSecondary),
                const SizedBox(width: 4),
                Text(
                  t.lastSpeedKph != null
                      ? '${t.lastSpeedKph!.toStringAsFixed(0)} km/h'
                      : 'Speed —',
                  style: const TextStyle(
                    fontSize: 12,
                    color: JaikalkiBrand.textSecondary,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(width: 12),
                const Icon(Icons.my_location_outlined,
                    size: 14, color: JaikalkiBrand.textSecondary),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    t.lastLat != null && t.lastLng != null
                        ? '${t.lastLat!.toStringAsFixed(4)}, ${t.lastLng!.toStringAsFixed(4)}'
                        : 'Awaiting first GPS ping…',
                    style: const TextStyle(
                      fontSize: 11,
                      color: JaikalkiBrand.textSecondary,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            if (t.lastLat != null && t.lastLng != null) ...[
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: () => _openMaps(t.lastLat!, t.lastLng!),
                icon: const Icon(Icons.map_outlined),
                label: const Text('Open in Maps'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: JaikalkiBrand.tealDark,
                  side: const BorderSide(color: JaikalkiBrand.tealPale),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }

  Future<void> _openMaps(double lat, double lng) async {
    final uri = Uri.parse('https://maps.google.com/?q=$lat,$lng');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}

class _StopsCard extends StatelessWidget {
  const _StopsCard({required this.pickup, required this.drop});
  final TransportStop? pickup;
  final TransportStop? drop;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'STOPS',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.2,
              color: JaikalkiBrand.textSecondary,
            ),
          ),
          const SizedBox(height: 10),
          _StopRow(
            icon: Icons.trip_origin,
            iconColor: JaikalkiBrand.saffron,
            label: 'Pickup',
            stop: pickup,
          ),
          const SizedBox(height: 8),
          _StopRow(
            icon: Icons.place_outlined,
            iconColor: JaikalkiBrand.tealDark,
            label: 'Drop',
            stop: drop,
          ),
        ],
      ),
    );
  }
}

class _StopRow extends StatelessWidget {
  const _StopRow({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.stop,
  });
  final IconData icon;
  final Color iconColor;
  final String label;
  final TransportStop? stop;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: iconColor, size: 20),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: JaikalkiBrand.textSecondary,
                  letterSpacing: 0.5,
                ),
              ),
              Text(
                stop?.name ?? 'Not set',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: stop == null
                      ? JaikalkiBrand.textSecondary
                      : JaikalkiBrand.indigoDark,
                ),
              ),
              if (stop?.scheduledArrival != null)
                Text(
                  'Scheduled ${stop!.scheduledArrival}',
                  style: const TextStyle(
                    fontSize: 11,
                    color: JaikalkiBrand.textSecondary,
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _DriverCard extends StatelessWidget {
  const _DriverCard({required this.name, required this.phone});
  final String? name;
  final String? phone;

  Future<void> _call(BuildContext context) async {
    if (phone == null || phone!.isEmpty) return;
    final uri = Uri(scheme: 'tel', path: phone);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    } else if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not dial $phone')),
      );
    }
  }

  Future<void> _sms(BuildContext context) async {
    if (phone == null || phone!.isEmpty) return;
    final uri = Uri(scheme: 'sms', path: phone);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    } else if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not open SMS for $phone')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'DRIVER',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w800,
              letterSpacing: 1.2,
              color: JaikalkiBrand.textSecondary,
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              CircleAvatar(
                backgroundColor: JaikalkiBrand.indigoDark,
                foregroundColor: Colors.white,
                child: Text(
                  (name?.isNotEmpty == true)
                      ? name![0].toUpperCase()
                      : '?',
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name ?? 'Not assigned',
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        color: JaikalkiBrand.indigoDark,
                      ),
                    ),
                    if (phone != null && phone!.isNotEmpty)
                      Text(
                        phone!,
                        style: const TextStyle(
                          fontSize: 12,
                          color: JaikalkiBrand.textSecondary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
          if (phone != null && phone!.isNotEmpty) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () => _call(context),
                    icon: const Icon(Icons.call_outlined),
                    label: const Text('Call'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: JaikalkiBrand.tealDark,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _sms(context),
                    icon: const Icon(Icons.sms_outlined),
                    label: const Text('SMS'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: JaikalkiBrand.indigoDark,
                      side: const BorderSide(color: JaikalkiBrand.saffronPale),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _FeeCard extends StatelessWidget {
  const _FeeCard({required this.amount});
  final double amount;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: JaikalkiBrand.marigoldPale.withOpacity(0.4),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: JaikalkiBrand.marigold.withOpacity(0.4)),
      ),
      child: Row(
        children: [
          const Icon(Icons.account_balance_wallet_outlined,
              color: JaikalkiBrand.indigoDark),
          const SizedBox(width: 10),
          const Expanded(
            child: Text(
              'Transport fee',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: JaikalkiBrand.indigoDark,
              ),
            ),
          ),
          Text(
            '₹${amount.toStringAsFixed(0)} / mo',
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w800,
              color: JaikalkiBrand.indigoDark,
            ),
          ),
        ],
      ),
    );
  }
}
