import 'package:flutter/material.dart';
import 'package:hive_flutter/hive_flutter.dart';

import 'src/app.dart';
import 'src/core/auth_cubit.dart';
import 'src/core/service_locator.dart';
import 'src/core/settings_cubit.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Hive.initFlutter();
  registerDependencies();
  await locator<SettingsCubit>().bootstrap();
  await locator<AuthCubit>().bootstrap();
  runApp(const JaikalkiApp());
}
