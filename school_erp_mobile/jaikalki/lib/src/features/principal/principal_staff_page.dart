import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../api/principal_repository.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';

/// Staff directory — searchable, with a leave indicator for anyone
/// out today and one-tap call.
class PrincipalStaffPage extends StatefulWidget {
  const PrincipalStaffPage({super.key});

  @override
  State<PrincipalStaffPage> createState() => _PrincipalStaffPageState();
}

class _PrincipalStaffPageState extends State<PrincipalStaffPage> {
  late Future<List<StaffRow>> _future;
  final _searchCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _future = locator<PrincipalRepository>().staff();
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    setState(() {
      _future = locator<PrincipalRepository>().staff();
    });
    await _future;
  }

  Future<void> _call(String? phone) async {
    if (phone == null || phone.isEmpty) return;
    final uri = Uri(scheme: 'tel', path: phone);
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  bool _matches(StaffRow s, String q) {
    if (q.isEmpty) return true;
    final hay = '${s.fullName} ${s.phone ?? ''} ${s.email ?? ''} '
        '${s.roles.join(' ')}'
        .toLowerCase();
    return hay.contains(q.toLowerCase());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Staff'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(60),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 4, 12, 10),
            child: TextField(
              controller: _searchCtrl,
              onChanged: (_) => setState(() {}),
              decoration: InputDecoration(
                isDense: true,
                hintText: 'Search staff or role',
                prefixIcon: const Icon(Icons.search),
                filled: true,
                fillColor: Colors.white,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<StaffRow>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            final all = snap.data ?? const <StaffRow>[];
            final q = _searchCtrl.text.trim();
            final rows = all.where((s) => _matches(s, q)).toList();
            if (rows.isEmpty) {
              return ListView(children: const [
                SizedBox(height: 200),
                Center(child: Text('No matching staff.')),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: rows.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (_, i) {
                final s = rows[i];
                return ListTile(
                  leading: CircleAvatar(
                    backgroundColor: s.onLeaveToday
                        ? const Color(0xFFFFE5E5)
                        : JaikalkiBrand.saffronPale,
                    foregroundColor: s.onLeaveToday
                        ? const Color(0xFFC00000)
                        : JaikalkiBrand.saffronDarker,
                    child: Text(
                      s.fullName.isEmpty
                          ? '?'
                          : s.fullName.characters.first.toUpperCase(),
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
                  title: Text(s.fullName,
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(s.roles.join(' · '),
                          style: const TextStyle(
                              fontSize: 11,
                              color: JaikalkiBrand.textSecondary)),
                      if (s.onLeaveToday)
                        Text(
                          'On ${s.leaveKind ?? "leave"} '
                          'until ${s.leaveEnd ?? ""}',
                          style: const TextStyle(
                            fontSize: 11,
                            color: Color(0xFFC00000),
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                    ],
                  ),
                  trailing: (s.phone != null && s.phone!.isNotEmpty)
                      ? IconButton(
                          icon: const Icon(Icons.call,
                              color: JaikalkiBrand.saffron),
                          onPressed: () => _call(s.phone),
                        )
                      : null,
                );
              },
            );
          },
        ),
      ),
    );
  }
}
