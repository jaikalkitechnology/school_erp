import 'dart:async';

import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:hive_flutter/hive_flutter.dart';

import 'src/app.dart';
import 'src/core/auth_cubit.dart';
import 'src/core/push_service.dart';
import 'src/core/service_locator.dart';
import 'src/core/settings_cubit.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Hive.initFlutter();
  // Firebase is needed for push. We swallow init failures so the app keeps
  // booting on a build that doesn't yet have google-services.json wired
  // (e.g. iOS first run before GoogleService-Info.plist lands).
  try {
    await Firebase.initializeApp();
  } catch (e, st) {
    debugPrint('Firebase.initializeApp failed: $e\n$st');
  }
  registerDependencies();
  await locator<SettingsCubit>().bootstrap();
  await locator<AuthCubit>().bootstrap();
  // Kick off FCM token registration in the background; we don't block
  // startup on it.
  unawaited(PushService.instance.start());
  runApp(const JaikalkiApp());
}

