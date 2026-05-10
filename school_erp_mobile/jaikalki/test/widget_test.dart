import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:jaikalki/src/app.dart';
import 'package:jaikalki/src/core/service_locator.dart';

void main() {
  testWidgets('Boots into login page', (tester) async {
    registerDependencies();
    await tester.pumpWidget(const JaikalkiApp());
    await tester.pump();

    expect(find.text('Sign in'), findsOneWidget);
    // Subdomain + identifier + password = 3 fields.
    expect(find.byType(TextFormField), findsNWidgets(3));
  });
}
