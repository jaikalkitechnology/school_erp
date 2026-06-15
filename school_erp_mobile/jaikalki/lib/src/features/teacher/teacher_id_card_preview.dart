import 'package:flutter/material.dart';

import '../../api/teacher_repository.dart';
import '../../theme/brand.dart';

/// In-app teacher ID card — visual mirror of the reportlab PDF that
/// /v1/teacher/me/id-card.pdf renders. Photo + logo are stubbed with
/// initials/letter here; rendering the actual uploaded photo needs an
/// authed-fetch wrapper around CachedNetworkImage that we don't have
/// in this app yet.
class TeacherIdCardPreview extends StatelessWidget {
  const TeacherIdCardPreview({
    required this.profile,
    required this.schoolName,
    super.key,
  });

  final TeacherProfile profile;
  final String schoolName;

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
          aspectRatio: 86 / 54,
          child: Container(
            decoration: BoxDecoration(
              color: const Color(0xFFFFF7E6),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: JaikalkiBrand.indigoDark, width: 1.5),
              boxShadow: [
                BoxShadow(
                  color: JaikalkiBrand.indigoDark.withOpacity(0.15),
                  blurRadius: 12, offset: const Offset(0, 6),
                ),
              ],
            ),
            child: Column(
              children: [
                Container(
                  height: 36,
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  decoration: const BoxDecoration(
                    color: JaikalkiBrand.tealDark,
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
                          (schoolName.isNotEmpty ? schoolName[0] : '?').toUpperCase(),
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
                              schoolName,
                              maxLines: 1, overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                color: Colors.white, fontSize: 12,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const Text(
                              'TEACHER IDENTITY CARD',
                              style: TextStyle(
                                color: Colors.white70, fontSize: 8,
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
                              _row('EMPLOYEE NO.', profile.employeeNo),
                              _row('DESIGNATION', profile.designation ?? '—'),
                              _row('PHONE', profile.phone ?? '—'),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
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
                    profile.email ?? '',
                    maxLines: 1, overflow: TextOverflow.ellipsis,
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
              maxLines: 1, overflow: TextOverflow.ellipsis,
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
