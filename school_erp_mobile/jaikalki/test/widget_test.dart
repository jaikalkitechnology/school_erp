import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';

import 'package:jaikalki/src/app.dart';
import 'package:jaikalki/src/core/service_locator.dart';
import 'package:jaikalki/src/core/settings_cubit.dart';

void main() {
  late Directory hiveDir;

  setUp(() async {
    hiveDir = await Directory.systemTemp.createTemp('jaikalki_test_');
    Hive.init(hiveDir.path);
    if (locator.isRegistered<SettingsCubit>()) {
      await locator.unregister<SettingsCubit>();
    }
    registerDependencies();
    await locator<SettingsCubit>().bootstrap();
  });

  tearDown(() async {
    await Hive.deleteFromDisk();
    await hiveDir.delete(recursive: true);
  });

  testWidgets('Boots into splash and routes to onboarding on first launch', (tester) async {
    await tester.pumpWidget(const JaikalkiApp());
    await tester.pump(const Duration(milliseconds: 600));
    await tester.pumpAndSettle();
    expect(find.textContaining('Skip', findRichText: false), findsOneWidget);
  });
}
