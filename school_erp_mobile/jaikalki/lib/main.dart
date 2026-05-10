import 'package:flutter/material.dart';

import 'src/app.dart';
import 'src/core/auth_cubit.dart';
import 'src/core/service_locator.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  registerDependencies();
  // Try restoring an existing session before the first frame.
  await locator<AuthCubit>().bootstrap();
  runApp(const JaikalkiApp());
}
