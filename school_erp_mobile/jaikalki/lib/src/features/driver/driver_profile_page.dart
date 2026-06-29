import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../api/driver_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Full profile of the logged-in transport_manager: their account
/// details (name, phone, email, roles) + the Driver row they're
/// linked to (license, status) + every route and bus they cover.
///
/// Shown from the More tab on the transport shell.
class DriverProfilePage extends StatefulWidget {
  const DriverProfilePage({super.key});

  @override
  State<DriverProfilePage> createState() => _DriverProfilePageState();
}

class _DriverProfilePageState extends State<DriverProfilePage> {
  late Future<DriverProfile?> _future;

  @override
  void initState() {
    super.initState();
    _future = locator<DriverRepository>().driverMe();
  }

  Future<void> _refresh() async {
    setState(() {
      _future = locator<DriverRepository>().driverMe();
    });
    await _future;
  }

  Future<void> _call(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My profile')),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<DriverProfile?>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            final profile = snap.data;
            if (profile == null) {
              return ListView(
                children: const [
                  SizedBox(height: 200),
                  Center(child: Text('Could not load your profile.')),
                ],
              );
            }
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _AccountCard(profile: profile, onCall: _call),
                const SizedBox(height: 16),
                if (profile.driver != null) ...[
                  _DriverRowCard(driver: profile.driver!),
                  const SizedBox(height: 16),
                ],
                _AssignmentsCard(
                  routes: profile.assignedRoutes,
                  buses: profile.assignedBuses,
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _AccountCard extends StatelessWidget {
  const _AccountCard({required this.profile, required this.onCall});
  final DriverProfile profile;
  final ValueChanged<String> onCall;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                CircleAvatar(
                  radius: 32,
                  backgroundColor: JaikalkiBrand.saffronPale,
                  child: Text(
                    profile.fullName.isEmpty
                        ? '?'
                        : profile.fullName.characters.first.toUpperCase(),
                    style: theme.textTheme.headlineSmall?.copyWith(
                      color: JaikalkiBrand.saffronDark,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        profile.fullName,
                        style: theme.textTheme.titleLarge,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        children: [
                          for (final role in profile.roles)
                            Chip(
                              label: Text(role),
                              visualDensity: VisualDensity.compact,
                              materialTapTargetSize:
                                  MaterialTapTargetSize.shrinkWrap,
                              backgroundColor: JaikalkiBrand.saffronPale,
                              labelStyle: const TextStyle(
                                color: JaikalkiBrand.saffronDarker,
                                fontWeight: FontWeight.w600,
                                fontSize: 11,
                              ),
                              side: BorderSide.none,
                            ),
                          if (!profile.isActive)
                            const Chip(
                              label: Text('inactive'),
                              visualDensity: VisualDensity.compact,
                              materialTapTargetSize:
                                  MaterialTapTargetSize.shrinkWrap,
                              backgroundColor: Color(0xFFFFE5E5),
                              labelStyle: TextStyle(
                                color: Color(0xFFC00000),
                                fontWeight: FontWeight.w600,
                                fontSize: 11,
                              ),
                              side: BorderSide.none,
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const Divider(height: 32),
            _kv(context, Icons.phone_outlined, 'Phone', profile.phone,
                trailing: (profile.phone != null && profile.phone!.isNotEmpty)
                    ? IconButton(
                        icon: const Icon(Icons.call,
                            color: JaikalkiBrand.saffron),
                        onPressed: () => onCall(profile.phone!),
                      )
                    : null),
            _kv(context, Icons.mail_outline, 'Email', profile.email),
            _kv(context, Icons.badge_outlined, 'User ID', '#${profile.userId}'),
          ],
        ),
      ),
    );
  }
}

class _DriverRowCard extends StatelessWidget {
  const _DriverRowCard({required this.driver});
  final DriverRowProfile driver;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.local_taxi_outlined,
                    color: JaikalkiBrand.saffron),
                const SizedBox(width: 8),
                Text('Driver record',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    )),
                const Spacer(),
                if (driver.status != null)
                  Chip(
                    label: Text(driver.status!),
                    visualDensity: VisualDensity.compact,
                    materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    backgroundColor: driver.status == 'active'
                        ? const Color(0xFFE6F4EA)
                        : const Color(0xFFFFE5E5),
                    labelStyle: TextStyle(
                      color: driver.status == 'active'
                          ? const Color(0xFF137333)
                          : const Color(0xFFC00000),
                      fontWeight: FontWeight.w600,
                      fontSize: 11,
                    ),
                    side: BorderSide.none,
                  ),
              ],
            ),
            const Divider(height: 24),
            _kv(context, Icons.fingerprint, 'License', driver.licenseNumber),
            _kv(context, Icons.event_outlined, 'License expires',
                driver.licenseExpiry),
            _kv(context, Icons.phone_iphone_outlined, 'On-record phone',
                driver.phone),
            _kv(context, Icons.numbers, 'Driver ID', '#${driver.id}'),
          ],
        ),
      ),
    );
  }
}

class _AssignmentsCard extends StatelessWidget {
  const _AssignmentsCard({required this.routes, required this.buses});
  final List<DriverAssignedRoute> routes;
  final List<String> buses;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.directions_bus_filled,
                    color: JaikalkiBrand.saffron),
                const SizedBox(width: 8),
                Text('Assignments',
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    )),
              ],
            ),
            const Divider(height: 24),
            Text('Buses (${buses.length})',
                style: theme.textTheme.labelLarge?.copyWith(
                  color: JaikalkiBrand.textSecondary,
                )),
            const SizedBox(height: 6),
            if (buses.isEmpty)
              const Text('No buses assigned yet.')
            else
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: [
                  for (final reg in buses)
                    Chip(
                      label: Text(reg),
                      avatar: const Icon(Icons.directions_bus,
                          size: 16, color: JaikalkiBrand.saffronDark),
                      backgroundColor: JaikalkiBrand.saffronPale,
                      side: BorderSide.none,
                    ),
                ],
              ),
            const SizedBox(height: 16),
            Text('Routes (${routes.length})',
                style: theme.textTheme.labelLarge?.copyWith(
                  color: JaikalkiBrand.textSecondary,
                )),
            const SizedBox(height: 6),
            if (routes.isEmpty)
              const Text('No routes assigned yet.')
            else
              ...routes.map(
                (r) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  dense: true,
                  leading: const Icon(Icons.alt_route,
                      color: JaikalkiBrand.saffron),
                  title: Text(r.name),
                  subtitle: Text([
                    r.code,
                    if (r.busRegistration != null) 'Bus ${r.busRegistration}',
                  ].join(' • ')),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

Widget _kv(BuildContext context, IconData icon, String label, String? value,
    {Widget? trailing}) {
  final theme = Theme.of(context);
  return Padding(
    padding: const EdgeInsets.symmetric(vertical: 6),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 18, color: JaikalkiBrand.textSecondary),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label,
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: JaikalkiBrand.textSecondary,
                  )),
              const SizedBox(height: 2),
              Text(
                (value == null || value.isEmpty) ? '—' : value,
                style: theme.textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        if (trailing != null) trailing,
      ],
    ),
  );
}
