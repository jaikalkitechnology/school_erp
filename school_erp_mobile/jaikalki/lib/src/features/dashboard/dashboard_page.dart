import 'package:flutter/material.dart';

import '../../api/api_client.dart';
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
    _health = locator<ApiClient>().health().catchError((_) => <String, dynamic>{
          'status': 'unreachable',
          'database': '?',
          'redis': '?',
        });
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Today'),
        actions: [
          IconButton(onPressed: () {}, icon: const Icon(Icons.notifications_outlined)),
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
                Text('PHASE 0 · FOUNDATION',
                    style: t.labelSmall?.copyWith(color: JaikalkiBrand.saffronDark)),
                const SizedBox(height: 8),
                Text('Welcome to Jaikalki', style: t.displayMedium),
                const SizedBox(height: 6),
                Text(
                  'Your role-aware home screen lights up as later phases land. For now this is the design system live on device.',
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
