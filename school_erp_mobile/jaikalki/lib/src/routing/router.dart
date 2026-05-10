import 'package:go_router/go_router.dart';

import '../features/auth/login_page.dart';
import '../features/dashboard/dashboard_page.dart';

final GoRouter appRouter = GoRouter(
  initialLocation: '/login',
  routes: [
    GoRoute(path: '/login', builder: (_, __) => const LoginPage()),
    GoRoute(path: '/dashboard', builder: (_, __) => const DashboardPage()),
  ],
);
