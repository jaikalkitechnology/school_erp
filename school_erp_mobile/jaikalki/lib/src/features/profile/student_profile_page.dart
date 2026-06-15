import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:open_filex/open_filex.dart';
import 'package:path_provider/path_provider.dart';

import '../../api/parent_repository.dart';
import '../../core/children_cubit.dart';
import '../../core/service_locator.dart';
import '../../theme/brand.dart';
import '../../widgets/authed_photo.dart';
import 'id_card_preview_page.dart';

class StudentProfilePage extends StatefulWidget {
  const StudentProfilePage({super.key});

  @override
  State<StudentProfilePage> createState() => _StudentProfilePageState();
}

class _StudentProfilePageState extends State<StudentProfilePage> {
  Future<StudentProfile>? _future;
  int? _loadedFor;
  bool _downloading = false;

  void _reload(int studentId) {
    _loadedFor = studentId;
    _future = locator<ParentRepository>().profile(studentId);
  }

  @override
  Widget build(BuildContext context) {
    return BlocProvider.value(
      value: locator<ChildrenCubit>(),
      child: Builder(builder: _build),
    );
  }

  Widget _build(BuildContext context) {
    final children = context.watch<ChildrenCubit>().state;
    if (children is! ChildrenLoaded || children.selectedId == null) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text('Select a child to view profile.'),
        ),
      );
    }
    final selected = children.selectedId!;
    if (_loadedFor != selected) {
      _reload(selected);
    }
    return FutureBuilder<StudentProfile>(
      future: _future,
      builder: (context, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snap.hasError || snap.data == null) {
          return Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              'Could not load profile: ${snap.error ?? "unknown"}',
              style: const TextStyle(color: Color(0xFFD32F2F)),
            ),
          );
        }
        final p = snap.data!;
        return RefreshIndicator(
          onRefresh: () async => setState(() => _reload(selected)),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            children: [
              _HeaderCard(profile: p),
              const SizedBox(height: 12),
              _ActionRow(
                downloading: _downloading,
                onPreview: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => Scaffold(
                      appBar: AppBar(title: const Text('ID card')),
                      body: IdCardPreviewPage(profile: p),
                    ),
                  ),
                ),
                onDownload: () => _download(p),
              ),
              const SizedBox(height: 16),
              _Section(
                title: 'Student details',
                children: [
                  _Field('Admission no', p.admissionNumber),
                  if (p.rollNo != null) _Field('Roll no', p.rollNo!),
                  if (p.classLabel != null)
                    _Field('Class', _join([p.classLabel, p.sectionName], ' · ')),
                  if (p.dateOfBirth != null)
                    _Field('Date of birth', p.dateOfBirth!),
                  if (p.gender != null) _Field('Gender', p.gender!),
                  if (p.bloodGroup != null)
                    _Field('Blood group', p.bloodGroup!),
                  if (p.houseName != null) _Field('House', p.houseName!),
                  if (p.admissionDate != null)
                    _Field('Admitted on', p.admissionDate!),
                ],
              ),
              const SizedBox(height: 12),
              _Section(
                title: 'Contact',
                children: [
                  if (p.address != null && p.address!.isNotEmpty)
                    _Field('Address', p.address!, multiline: true),
                  if (p.phone != null) _Field('Phone', p.phone!),
                  if (p.email != null) _Field('Email', p.email!),
                  if (p.emergencyContactName != null)
                    _Field('Emergency contact', p.emergencyContactName!),
                  if (p.emergencyPhone != null)
                    _Field('Emergency phone', p.emergencyPhone!),
                ],
              ),
              const SizedBox(height: 12),
              _ParentsSection(profile: p),
              if ((p.allergies != null && p.allergies!.isNotEmpty) ||
                  (p.medicalConditions != null &&
                      p.medicalConditions!.isNotEmpty)) ...[
                const SizedBox(height: 12),
                _Section(
                  title: 'Medical',
                  children: [
                    if (p.allergies != null && p.allergies!.isNotEmpty)
                      _Field('Allergies', p.allergies!, multiline: true),
                    if (p.medicalConditions != null &&
                        p.medicalConditions!.isNotEmpty)
                      _Field('Conditions', p.medicalConditions!,
                          multiline: true),
                  ],
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  Future<void> _download(StudentProfile p) async {
    setState(() => _downloading = true);
    final messenger = ScaffoldMessenger.of(context);
    try {
      final dir = await getTemporaryDirectory();
      final safe = p.admissionNumber.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_');
      final localPath = '${dir.path}/id_card_$safe.pdf';
      await locator<ParentRepository>()
          .downloadIdCard(studentId: p.studentId, savePath: localPath);
      await OpenFilex.open(localPath);
    } catch (e) {
      messenger.showSnackBar(
        SnackBar(content: Text('Could not open ID card: $e')),
      );
    } finally {
      if (mounted) setState(() => _downloading = false);
    }
  }

  String _join(List<String?> parts, String sep) =>
      parts.where((s) => s != null && s.isNotEmpty).join(sep);
}

class _HeaderCard extends StatelessWidget {
  const _HeaderCard({required this.profile});
  final StudentProfile profile;

  String _initials(String name) {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts[0].isEmpty) return '?';
    if (parts.length == 1) return parts[0][0].toUpperCase();
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [JaikalkiBrand.indigoDark, Color(0xFF3A2A6B)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Container(
            width: 72, height: 72,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.white.withOpacity(0.18),
            ),
            clipBehavior: Clip.antiAlias,
            alignment: Alignment.center,
            child: AuthedPhoto(
              path: profile.photoUrl,
              placeholder: Text(
                _initials(profile.fullName),
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: Colors.white,
                ),
              ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(profile.fullName,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                    )),
                const SizedBox(height: 2),
                Text(
                  '${profile.admissionNumber} · ${profile.classLabel ?? ""} ${profile.sectionName ?? ""}'
                      .trim(),
                  style: TextStyle(
                    color: Colors.white.withOpacity(0.85),
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 6),
                Text(profile.schoolName,
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.7),
                      fontSize: 11,
                      fontStyle: FontStyle.italic,
                    )),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionRow extends StatelessWidget {
  const _ActionRow({
    required this.downloading,
    required this.onPreview,
    required this.onDownload,
  });

  final bool downloading;
  final VoidCallback onPreview;
  final VoidCallback onDownload;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: OutlinedButton.icon(
            onPressed: onPreview,
            icon: const Icon(Icons.badge_outlined),
            label: const Text('Preview ID card'),
            style: OutlinedButton.styleFrom(
              foregroundColor: JaikalkiBrand.indigoDark,
              side: const BorderSide(color: JaikalkiBrand.saffronPale),
              padding: const EdgeInsets.symmetric(vertical: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: ElevatedButton.icon(
            onPressed: downloading ? null : onDownload,
            icon: downloading
                ? const SizedBox(
                    width: 16, height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2, color: Colors.white,
                    ),
                  )
                : const Icon(Icons.download_outlined),
            label: const Text('Download PDF'),
            style: ElevatedButton.styleFrom(
              backgroundColor: JaikalkiBrand.saffron,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.children});
  final String title;
  final List<Widget> children;

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
          Text(title,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: JaikalkiBrand.indigoDark,
                letterSpacing: 0.4,
              )),
          const SizedBox(height: 8),
          ...children,
        ],
      ),
    );
  }
}

class _Field extends StatelessWidget {
  const _Field(this.label, this.value, {this.multiline = false});
  final String label;
  final String value;
  final bool multiline;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 110,
            child: Text(label,
                style: const TextStyle(
                  fontSize: 12,
                  color: JaikalkiBrand.textSecondary,
                )),
          ),
          Expanded(
            child: Text(value,
                maxLines: multiline ? 4 : 1,
                overflow: multiline
                    ? TextOverflow.ellipsis
                    : TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: JaikalkiBrand.indigoDark,
                )),
          ),
        ],
      ),
    );
  }
}

class _ParentsSection extends StatelessWidget {
  const _ParentsSection({required this.profile});
  final StudentProfile profile;

  @override
  Widget build(BuildContext context) {
    final structured = profile.parents;
    if (structured.isNotEmpty) {
      return _Section(
        title: 'Parents & guardians',
        children: structured
            .map((p) => Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(p.fullName,
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                                color: JaikalkiBrand.indigoDark,
                              )),
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 1),
                            decoration: BoxDecoration(
                              color: (p.isPrimary
                                      ? JaikalkiBrand.saffron
                                      : JaikalkiBrand.tealDark)
                                  .withOpacity(0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(p.relation,
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                  color: p.isPrimary
                                      ? JaikalkiBrand.saffron
                                      : JaikalkiBrand.tealDark,
                                )),
                          ),
                        ],
                      ),
                      if (p.phone != null)
                        Text('📞 ${p.phone}',
                            style: const TextStyle(
                              fontSize: 12,
                              color: JaikalkiBrand.textSecondary,
                            )),
                      if (p.email != null)
                        Text('✉️ ${p.email}',
                            style: const TextStyle(
                              fontSize: 12,
                              color: JaikalkiBrand.textSecondary,
                            )),
                    ],
                  ),
                ))
            .toList(),
      );
    }
    // Fall back to the denormalized fields from Student row.
    return _Section(
      title: 'Parents',
      children: [
        if (profile.fatherName != null) _Field('Father', profile.fatherName!),
        if (profile.motherName != null) _Field('Mother', profile.motherName!),
        if (profile.guardianName != null)
          _Field('Guardian', profile.guardianName!),
        if (profile.parentPhone != null) _Field('Phone', profile.parentPhone!),
        if (profile.parentEmail != null) _Field('Email', profile.parentEmail!),
      ],
    );
  }
}
