/// 13 roles defined in SchoolERP_Architecture.md.
/// Auth + RBAC wiring lands in Phase 2.
enum UserRole {
  schoolAdmin,
  principal,
  vicePrincipal,
  coordinator,
  classTeacher,
  subjectTeacher,
  accountant,
  librarian,
  transportManager,
  hostelWarden,
  officeStaff,
  parent,
  student,
}

extension UserRoleLabel on UserRole {
  String get label {
    switch (this) {
      case UserRole.schoolAdmin:
        return 'School Admin';
      case UserRole.principal:
        return 'Principal';
      case UserRole.vicePrincipal:
        return 'Vice Principal';
      case UserRole.coordinator:
        return 'Coordinator';
      case UserRole.classTeacher:
        return 'Class Teacher';
      case UserRole.subjectTeacher:
        return 'Subject Teacher';
      case UserRole.accountant:
        return 'Accountant';
      case UserRole.librarian:
        return 'Librarian';
      case UserRole.transportManager:
        return 'Transport Manager';
      case UserRole.hostelWarden:
        return 'Hostel Warden';
      case UserRole.officeStaff:
        return 'Office Staff';
      case UserRole.parent:
        return 'Parent';
      case UserRole.student:
        return 'Student';
    }
  }
}
