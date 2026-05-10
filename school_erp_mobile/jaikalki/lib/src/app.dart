import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'core/auth_cubit.dart';
import 'core/error_bus.dart';
import 'core/service_locator.dart';
import 'core/settings_cubit.dart';
import 'i18n/strings.dart';
import 'routing/router.dart';
import 'theme/brand.dart';

class JaikalkiApp extends StatelessWidget {
  const JaikalkiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiBlocProvider(
      providers: [
        BlocProvider.value(value: locator<AuthCubit>()),
        BlocProvider.value(value: locator<SettingsCubit>()),
      ],
      child: BlocBuilder<SettingsCubit, SettingsState>(
        builder: (context, settings) {
          // Rebuild the router whenever auth/settings change so redirect
          // logic re-runs cleanly.
          final router = buildRouter();
          return MaterialApp.router(
            title: 'Jaikalki School',
            debugShowCheckedModeBanner: false,
            theme: JaikalkiBrand.lightTheme(),
            darkTheme: JaikalkiBrand.darkTheme(),
            themeMode: settings.themeMode,
            locale: Locale(settings.language.code),
            supportedLocales: AppLanguage.values
                .map((l) => Locale(l.code))
                .toList(growable: false),
            routerConfig: router,
            builder: (context, child) =>
                GlobalErrorListener(child: child ?? const SizedBox.shrink()),
          );
        },
      ),
    );
  }
}
