import 'package:flutter_test/flutter_test.dart';

import 'package:bittu_agentic_ai/app.dart';

void main() {
  testWidgets('Bittu app boot smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const BittuAgenticApp());
    expect(find.text('BITTU HEIST DEFENSE ARENA'), findsOneWidget);
  });
}
