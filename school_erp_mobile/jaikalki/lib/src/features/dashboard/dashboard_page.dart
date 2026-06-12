import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../api/auth_repository.dart';
import '../../api/parent_repository.dart';
import '../../core/auth_cubit.dart';
import '../../core/children_cubit.dart';
import '../../core/service_locator.dart';
import '../../core/settings_cubit.dart';
import '../../theme/brand.dart';
import '../profile/id_card_preview_page.dart';
import '../profile/student_profile_page.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  @override
  void initState() {
    super.initState();
    // Fire-and-forget: ChildrenCubit handles the empty case for non-parent users.
    final cubit = locator<ChildrenCubit>();
    if (cubit.state is ChildrenInitial) {
      cubit.load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return BlocProvider.value(
      value: locator<ChildrenCubit>(),
      child: BlocBuilder<AuthCubit, AuthState>(
        builder: (context, authState) {
          final user = authState is AuthAuthenticated ? authState.user : null;
          final isParent = (user?.roles ?? const []).contains('parent');
          final greeting = user?.fullName.split(' ').first ?? 'there';
          final s = context.watch<SettingsCubit>().state.strings;

          return Scaffold(
            appBar: AppBar(title: Text(s.today)),
            body: ListView(
              padding: const EdgeInsets.all(20),
              children: [
                _Header(user: user, greeting: greeting),
                if (isParent) ...[
                  const SizedBox(height: 16),
                  const _ChildSwitcher(),
                  const SizedBox(height: 16),
                  const _ChildDashboardCard(),
                  const SizedBox(height: 16),
                  const _IdCardTile(),
                  const SizedBox(height: 16),
                  const _AttendanceCard(),
                ] else ...[
                  const SizedBox(height: 16),
                  _StaffStats(),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.user, required this.greeting});
  final AuthUser? user;
  final String greeting;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final s = context.watch<SettingsCubit>().state.strings;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${user?.tenantSubdomain ?? "JAIKALKI"} · ${user?.primaryRole?.toUpperCase() ?? "MOBILE"}',
            style: t.labelSmall?.copyWith(color: JaikalkiBrand.saffronDark),
          ),
          const SizedBox(height: 8),
          Text('${s.namaste}, $greeting', style: t.displayMedium),
          const SizedBox(height: 6),
          Text(user?.schoolName ?? s.yourSchool, style: t.bodyMedium),
        ],
      ),
    );
  }
}

class _ChildSwitcher extends StatelessWidget {
  const _ChildSwitcher();

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return BlocBuilder<ChildrenCubit, ChildrenState>(
      builder: (context, state) {
        if (state is ChildrenLoading || state is ChildrenInitial) {
          return const SizedBox(height: 100, child: Center(child: CircularProgressIndicator()));
        }
        if (state is ChildrenError) {
          return Text(state.message, style: t.bodyMedium);
        }
        if (state is ChildrenLoaded) {
          if (state.children.isEmpty) {
            return Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: JaikalkiBrand.warmWhite,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: JaikalkiBrand.saffronPale),
              ),
              child: Text(
                'No children linked to this account yet. Ask your school admin to link them.',
                style: t.bodyMedium,
              ),
            );
          }
          return SizedBox(
            height: 96,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: state.children.length,
              separatorBuilder: (_, __) => const SizedBox(width: 12),
              itemBuilder: (context, index) {
                final c = state.children[index];
                final selected = state.selectedId == c.studentId;
                return GestureDetector(
                  onTap: () => context.read<ChildrenCubit>().select(c.studentId),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 180),
                    width: 220,
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: selected ? JaikalkiBrand.saffron : JaikalkiBrand.warmWhite,
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(
                        color: selected ? JaikalkiBrand.saffron : JaikalkiBrand.saffronPale,
                      ),
                    ),
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 28,
                          backgroundColor: selected ? JaikalkiBrand.warmWhite : JaikalkiBrand.saffronPale,
                          child: Text(
                            c.fullName.isNotEmpty ? c.fullName.characters.first : '?',
                            style: TextStyle(
                              color: selected ? JaikalkiBrand.saffronDark : JaikalkiBrand.indigoDark,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                c.fullName,
                                style: t.titleMedium?.copyWith(
                                  color: selected ? JaikalkiBrand.warmWhite : JaikalkiBrand.indigoDark,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                              const SizedBox(height: 2),
                              Text(
                                c.classLabel ?? c.admissionNumber,
                                style: t.bodyMedium?.copyWith(
                                  fontSize: 12,
                                  color: selected
                                      ? JaikalkiBrand.marigoldPale
                                      : JaikalkiBrand.textSecondary,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          );
        }
        return const SizedBox.shrink();
      },
    );
  }
}

class _ChildDashboardCard extends StatelessWidget {
  const _ChildDashboardCard();

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return BlocBuilder<ChildrenCubit, ChildrenState>(
      builder: (context, state) {
        if (state is! ChildrenLoaded || state.children.isEmpty) return const SizedBox.shrink();
        if (state.dashboardLoading) {
          return const SizedBox(height: 80, child: Center(child: CircularProgressIndicator()));
        }
        final dash = state.dashboard;
        if (dash == null) return const SizedBox.shrink();
        final tiles = [
          _Tile(
            label: 'Fees due',
            value: '₹${dash.feeDueAmount.toStringAsFixed(0)}',
            hint: dash.feeDueAmount > 0 ? 'Tap fees to pay' : 'All clear',
            tone: dash.feeDueAmount > 0
                ? JaikalkiBrand.saffron
                : JaikalkiBrand.tealDark,
          ),
          _Tile(
            label: 'Today',
            value: (dash.todayAttendance ?? '—').replaceAll('_', ' '),
            hint: 'Attendance',
          ),
          _Tile(label: 'Pending leaves', value: dash.pendingLeaves.toString(), hint: 'Approvals'),
          _Tile(label: 'Documents', value: dash.documentsCount.toString(), hint: 'On record'),
        ];
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(dash.fullName, style: t.titleLarge),
            const SizedBox(height: 4),
            Text(
              '${dash.classLabel ?? "—"} · ${dash.admissionNumber}',
              style: t.bodyMedium,
            ),
            const SizedBox(height: 12),
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 2,
              childAspectRatio: 1.6,
              mainAxisSpacing: 12,
              crossAxisSpacing: 12,
              children: tiles,
            ),
          ],
        );
      },
    );
  }
}

class _StaffStats extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: JaikalkiBrand.warmWhite,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: JaikalkiBrand.saffronPale),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('PHASE 8 · TODAY',
              style: t.labelSmall?.copyWith(color: JaikalkiBrand.saffronDark)),
          const SizedBox(height: 6),
          Text('Welcome back', style: t.titleLarge),
          const SizedBox(height: 6),
          Text(
            'Staff dashboards (attendance, classes, fee desk) light up phase by phase. '
            'Use the school admin web for the full feature set today.',
            style: t.bodyMedium,
          ),
        ],
      ),
    );
  }
}

class _AttendanceCard extends StatefulWidget {
  const _AttendanceCard();

  @override
  State<_AttendanceCard> createState() => _AttendanceCardState();
}

class _AttendanceCardState extends State<_AttendanceCard> {
  int? _loadedFor;
  Future<List<AttendanceRow>>? _future;

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<ChildrenCubit, ChildrenState>(
      builder: (context, state) {
        if (state is! ChildrenLoaded || state.selectedId == null) {
          return const SizedBox.shrink();
        }
        final id = state.selectedId!;
        if (_loadedFor != id) {
          _loadedFor = id;
          _future = context.read<ChildrenCubit>().attendance(id);
        }
        final t = Theme.of(context).textTheme;
        return Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: JaikalkiBrand.warmWhite,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: JaikalkiBrand.saffronPale),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('ATTENDANCE',
                  style: t.labelSmall?.copyWith(color: JaikalkiBrand.saffronDark)),
              const SizedBox(height: 8),
              FutureBuilder<List<AttendanceRow>>(
                future: _future,
                builder: (context, snap) {
                  if (snap.connectionState != ConnectionState.done) {
                    return const SizedBox(
                      height: 40,
                      child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
                    );
                  }
                  final rows = snap.data ?? const [];
                  if (rows.isEmpty) {
                    return Text(
                      'No attendance recorded yet.',
                      style: t.bodyMedium,
                    );
                  }
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: rows.take(8).map((r) {
                      final tone = _toneFor(r.status);
                      return Container(
                        margin: const EdgeInsets.only(bottom: 6),
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        decoration: BoxDecoration(
                          color: tone.bg,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Row(
                          children: [
                            Text(r.date,
                                style: t.bodyMedium?.copyWith(
                                  fontFamily: 'monospace',
                                  color: tone.fg,
                                )),
                            const Spacer(),
                            Text(r.status.replaceAll('_', ' ').toUpperCase(),
                                style: t.labelSmall?.copyWith(color: tone.fg)),
                          ],
                        ),
                      );
                    }).toList(),
                  );
                },
              ),
            ],
          ),
        );
      },
    );
  }
}

class _StatusTone {
  const _StatusTone(this.bg, this.fg);
  final Color bg;
  final Color fg;
}

_StatusTone _toneFor(String status) {
  switch (status) {
    case 'present':
      return const _StatusTone(JaikalkiBrand.tealPale, JaikalkiBrand.tealDark);
    case 'absent':
      return const _StatusTone(JaikalkiBrand.saffronPale, JaikalkiBrand.saffronDarker);
    case 'late':
      return const _StatusTone(JaikalkiBrand.marigoldPale, JaikalkiBrand.indigoDark);
    case 'half_day':
      return const _StatusTone(JaikalkiBrand.marigoldPale, JaikalkiBrand.indigoDark);
    default:
      return const _StatusTone(JaikalkiBrand.ivory, JaikalkiBrand.textSecondary);
  }
}


class _Tile extends StatelessWidget {
  const _Tile({
    required this.label,
    required this.value,
    required this.hint,
    this.tone,
  });
  final String label;
  final String value;
  final String hint;
  final Color? tone;

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Theme.of(context).colorScheme.outline),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label.toUpperCase(),
              style: t.labelSmall?.copyWith(color: JaikalkiBrand.saffronDark)),
          const SizedBox(height: 6),
          Text(
            value,
            style: t.displayMedium?.copyWith(
              fontSize: 26,
              color: tone,
            ),
          ),
          const Spacer(),
          Text(hint, style: t.bodyMedium?.copyWith(fontSize: 11)),
        ],
      ),
    );
  }
}

/// Front-page quick access to the selected child's ID card. Lazy-loads
/// the profile so we don't make the dashboard wait on a request that
/// only matters when the user actually has a child selected.
class _IdCardTile extends StatefulWidget {
  const _IdCardTile();

  @override
  State<_IdCardTile> createState() => _IdCardTileState();
}

class _IdCardTileState extends State<_IdCardTile> {
  Future<StudentProfile>? _future;
  int? _loadedFor;

  void _loadFor(int studentId) {
    _loadedFor = studentId;
    _future = locator<ParentRepository>().profile(studentId);
  }

  String _initials(String name) {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts[0].isEmpty) return '?';
    if (parts.length == 1) return parts[0][0].toUpperCase();
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    final children = context.watch<ChildrenCubit>().state;
    if (children is! ChildrenLoaded || children.selectedId == null) {
      return const SizedBox.shrink();
    }
    final selected = children.selectedId!;
    if (_loadedFor != selected) {
      _loadFor(selected);
    }
    return FutureBuilder<StudentProfile>(
      future: _future,
      builder: (context, snap) {
        final profile = snap.data;
        return Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: profile == null
                ? null
                : () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => Scaffold(
                          appBar: AppBar(title: const Text('ID card')),
                          body: IdCardPreviewPage(profile: profile),
                        ),
                      ),
                    ),
            child: Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [JaikalkiBrand.indigoDark, Color(0xFF3A2A6B)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: JaikalkiBrand.indigoDark.withOpacity(0.18),
                    blurRadius: 12, offset: const Offset(0, 6),
                  ),
                ],
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 28,
                    backgroundColor: Colors.white.withOpacity(0.18),
                    foregroundColor: Colors.white,
                    child: Text(
                      profile != null ? _initials(profile.fullName) : '··',
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w700),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          profile?.fullName ?? 'Student ID card',
                          maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 14, fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          profile == null
                              ? 'Tap to view'
                              : '${profile.admissionNumber} · ${[
                                  profile.classLabel, profile.sectionName
                                ].where((s) => s != null && s!.isNotEmpty).join(" / ")}',
                          maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.85),
                            fontSize: 11,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      const Icon(Icons.badge_outlined,
                          color: Colors.white, size: 22),
                      const SizedBox(height: 4),
                      InkWell(
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => Scaffold(
                              appBar: AppBar(title: const Text('Student profile')),
                              body: const StudentProfilePage(),
                            ),
                          ),
                        ),
                        child: Text(
                          'PROFILE',
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.85),
                            fontSize: 9,
                            letterSpacing: 1.2,
                            fontWeight: FontWeight.w700,
                            decoration: TextDecoration.underline,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
