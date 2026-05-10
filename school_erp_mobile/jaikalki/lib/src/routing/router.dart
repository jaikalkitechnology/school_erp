import 'package:go_router/go_router.dart';

import '../core/auth_cubit.dart';
import '../core/service_locator.dart';
import '../core/settings_cubit.dart';
import '../features/auth/login_page.dart';
import '../features/shell/home_shell.dart';
import '../features/splash/onboarding_page.dart';
import '../features/splash/splash_page.dart';

GoRouter buildRouter() {
  return GoRouter(
    initialLocation: '/',
    redirect: (context, state) {
      final loc = state.matchedLocation;
      // Splash always renders to compute its own next step.
      if (loc == '/' || loc == '/onboarding') return null;

      final settings = locator<SettingsCubit>().state;
      if (!settings.onboarded && loc != '/login') return '/onboarding';

      final auth = locator<AuthCubit>().state;
      final authed = auth is AuthAuthenticated;
      if (!authed && loc != '/login') return '/login';
      if (authed && loc == '/login') return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/', builder: (_, __) => const SplashPage()),
      GoRoute(path: '/onboarding', builder: (_, __) => const OnboardingPage()),
      GoRoute(path: '/login', builder: (_, __) => const LoginPage()),
      GoRoute(path: '/home', builder: (_, __) => const HomeShell()),
      GoRoute(path: '/dashboard', redirect: (_, __) => '/home'),
    ],
  );
}
