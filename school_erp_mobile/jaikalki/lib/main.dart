import 'package:flutter/material.dart';

import 'src/app.dart';
import 'src/core/service_locator.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  registerDependencies();
  runApp(const JaikalkiApp());
}
