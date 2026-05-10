import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../api/api_client.dart';
import '../../core/auth_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  late final Future<Map<String, dynamic>> _health;

  @override
  void initState() {
    super.initState();
    _health = locator<ApiClient>().health().catchError(
          (_) => <String, dynamic>{
            'status': 'unreachable',
            'database': '?',
            'redis': '?',
          },
        );
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return BlocProvider.value(
      value: locator<AuthCubit>(),
      child: BlocConsumer<AuthCubit, AuthState>(
        listenWhen: (prev, curr) => curr is AuthInitial && prev is AuthAuthenticated,
        listener: (context, state) {
          if (state is AuthInitial) {
            context.go('/login');
          }
        },
        builder: (context, state) {
          final user = state is AuthAuthenticated ? state.user : null;
          final greeting = user?.fullName.split(' ').first ?? 'there';
          return Scaffold(
            appBar: AppBar(
              title: const Text('Today'),
              actions: [
                IconButton(
                  onPressed: () => context.read<AuthCubit>().logout(),
                  icon: const Icon(Icons.logout),
                  tooltip: 'Sign out',
                ),
              ],
            ),
            body: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: JaikalkiBrand.warmWhite,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: JaikalkiBrand.saffronPale),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${user?.tenantSubdomain ?? "JAIKALKI"} · ${user?.primaryRole?.toUpperCase() ?? "MOBILE"}',
                        style: t.labelSmall?.copyWith(color: JaikalkiBrand.saffronDark),
                      ),
                      const SizedBox(height: 8),
                      Text('Namaste, $greeting', style: t.displayMedium),
                      const SizedBox(height: 6),
                      Text(
                        user == null
                            ? 'Loading your school account…'
                            : (user.schoolName ?? 'Your school'),
                        style: t.bodyMedium,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                _SectionTitle('At a glance'),
                const SizedBox(height: 8),
                Row(
                  children: const [
                    Expanded(child: _StatCard(label: 'Attendance', value: '—', hint: 'Phase 9')),
                    SizedBox(width: 12),
                    Expanded(child: _StatCard(label: 'Homework', value: '—', hint: 'Phase 14')),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: const [
                    Expanded(child: _StatCard(label: 'Fees due', value: '—', hint: 'Phase 11')),
                    SizedBox(width: 12),
                    Expanded(child: _StatCard(label: 'Bus ETA', value: '—', hint: 'Phase 18')),
                  ],
                ),
                const SizedBox(height: 24),
                _SectionTitle('Backend connectivity'),
                const SizedBox(height: 8),
                FutureBuilder<Map<String, dynamic>>(
                  future: _health,
                  builder: (context, snapshot) {
                    final data = snapshot.data ?? <String, dynamic>{'status': 'loading'};
                    return Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: JaikalkiBrand.indigoDark,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Text(
                        data.entries.map((e) => '${e.key}: ${e.value}').join('\n'),
                        style: const TextStyle(
                          color: JaikalkiBrand.marigoldPale,
                          fontFamily: 'monospace',
                          fontSize: 12,
                          height: 1.6,
                        ),
                      ),
                    );
                  },
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);
  final String text;
  @override
  Widget build(BuildContext context) {
    return Text(text, style: Theme.of(context).textTheme.titleLarge);
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.label, required this.value, required this.hint});
  final String label;
  final String value;
  final String hint;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label.toUpperCase(),
              style: t.labelSmall?.copyWith(color: JaikalkiBrand.saffronDark)),
          const SizedBox(height: 6),
          Text(value, style: t.displayMedium?.copyWith(fontSize: 28)),
          const SizedBox(height: 4),
          Text('Lands in $hint', style: t.bodyMedium?.copyWith(fontSize: 12)),
        ],
      ),
    );
  }
}
