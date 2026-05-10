import 'package:flutter/material.dart';

import 'routing/router.dart';
import 'theme/brand.dart';

class JaikalkiApp extends StatelessWidget {
  const JaikalkiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Jaikalki School',
      debugShowCheckedModeBanner: false,
      theme: JaikalkiBrand.lightTheme(),
      routerConfig: appRouter,
    );
  }
}
