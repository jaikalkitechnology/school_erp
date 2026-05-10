import 'package:go_router/go_router.dart';

import '../core/auth_cubit.dart';
import '../core/service_locator.dart';
import '../features/auth/login_page.dart';
import '../features/dashboard/dashboard_page.dart';

GoRouter buildRouter() {
  return GoRouter(
    initialLocation: '/login',
    redirect: (context, state) {
      final auth = locator<AuthCubit>().state;
      final loggingIn = state.matchedLocation == '/login';
      if (auth is AuthAuthenticated && loggingIn) return '/dashboard';
      if (auth is! AuthAuthenticated && !loggingIn) return '/login';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginPage()),
      GoRoute(path: '/dashboard', builder: (_, __) => const DashboardPage()),
    ],
  );
}
