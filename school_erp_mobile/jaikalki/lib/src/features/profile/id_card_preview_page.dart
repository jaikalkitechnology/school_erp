import 'package:flutter/material.dart';

import '../../api/parent_repository.dart';
import '../../theme/brand.dart';

/// Flutter-rendered preview of the student ID card. Mirrors the
/// reportlab layout the backend ships in the PDF — same blocks, same
/// order — so what parents see in-app matches what prints. Photo +
/// logo would need /v1/uploads auth, so they're stubbed with initials
/// + the school's first letter for now.
class IdCardPreviewPage extends StatelessWidget {
  const IdCardPreviewPage({required this.profile, super.key});

  final StudentProfile profile;

  String _initials(String name) {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts[0].isEmpty) return '?';
    if (parts.length == 1) return parts[0][0].toUpperCase();
    return '${parts.first[0]}${parts.last[0]}'.toUpperCase();
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: AspectRatio(
          // Standard credit-card-ish 86×54 mm.
          aspectRatio: 86 / 54,
          child: Container(
            decoration: BoxDecoration(
              color: const Color(0xFFFFF7E6),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: JaikalkiBrand.indigoDark, width: 1.5),
              boxShadow: [
                BoxShadow(
                  color: JaikalkiBrand.indigoDark.withOpacity(0.15),
                  blurRadius: 12,
                  offset: const Offset(0, 6),
                ),
              ],
            ),
            child: Column(
              children: [
                // Top band: school name.
                Container(
                  height: 36,
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  decoration: const BoxDecoration(
                    color: JaikalkiBrand.indigoDark,
                    borderRadius: BorderRadius.only(
                      topLeft: Radius.circular(14),
                      topRight: Radius.circular(14),
                    ),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 28, height: 28,
                        decoration: BoxDecoration(
                          color: Colors.white.withOpacity(0.18),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        alignment: Alignment.center,
                        child: Text(
                          (profile.schoolName.isNotEmpty
                                  ? profile.schoolName[0]
                                  : '?')
                              .toUpperCase(),
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              profile.schoolName,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const Text(
                              'STUDENT IDENTITY CARD',
                              style: TextStyle(
                                color: Colors.white70,
                                fontSize: 8,
                                letterSpacing: 1.0,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(10),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 70, height: 90,
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: JaikalkiBrand.indigoDark, width: 1,
                            ),
                          ),
                          alignment: Alignment.center,
                          child: Text(
                            _initials(profile.fullName),
                            style: const TextStyle(
                              fontSize: 26,
                              fontWeight: FontWeight.w700,
                              color: JaikalkiBrand.indigoDark,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _row('NAME', profile.fullName),
                              _row('ADM. NO.', profile.admissionNumber),
                              _row(
                                'CLASS · SECTION',
                                [profile.classLabel, profile.sectionName]
                                    .where((s) => s != null && s.isNotEmpty)
                                    .join(' / '),
                              ),
                              _row(
                                'DOB · BLOOD',
                                '${profile.dateOfBirth ?? "—"}   ${profile.bloodGroup ?? "—"}',
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                // Footer strip.
                Container(
                  height: 22,
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  decoration: const BoxDecoration(
                    color: Color(0xFFFFE4B8),
                    borderRadius: BorderRadius.only(
                      bottomLeft: Radius.circular(14),
                      bottomRight: Radius.circular(14),
                    ),
                  ),
                  alignment: Alignment.centerLeft,
                  child: Text(
                    _footer(),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 9,
                      color: JaikalkiBrand.indigoDark,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _footer() {
    final parts = <String>[];
    final parent = profile.parentPhone ?? profile.emergencyPhone;
    if (parent != null && parent.isNotEmpty) parts.add('Parent: $parent');
    if (profile.schoolPhone != null && profile.schoolPhone!.isNotEmpty) {
      parts.add('School: ${profile.schoolPhone}');
    }
    return parts.join('  ·  ');
  }

  Widget _row(String label, String value) => Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label,
                style: const TextStyle(
                  fontSize: 7,
                  color: JaikalkiBrand.textSecondary,
                  letterSpacing: 0.6,
                )),
            Text(
              value.isEmpty ? '—' : value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: JaikalkiBrand.indigoDark,
              ),
            ),
          ],
        ),
      );
}
