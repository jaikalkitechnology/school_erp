import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'core/auth_cubit.dart';
import 'core/service_locator.dart';
import 'routing/router.dart';
import 'theme/brand.dart';

class JaikalkiApp extends StatelessWidget {
  const JaikalkiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider.value(
      value: locator<AuthCubit>(),
      child: BlocBuilder<AuthCubit, AuthState>(
        builder: (context, state) {
          // Rebuild the router on auth changes so the redirect picks up.
          final router = buildRouter();
          return MaterialApp.router(
            title: 'Jaikalki School',
            debugShowCheckedModeBanner: false,
            theme: JaikalkiBrand.lightTheme(),
            routerConfig: router,
          );
        },
      ),
    );
  }
}
