// Failure paths on a device against the real server: wrong token -> clear message in Settings; oversized file ->
// message; server stopped mid-ask (scripts/app_integration.sh stops it when the ask arrives) -> retry message.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:kanakku/core/api_client.dart';
import 'package:kanakku/main.dart' as app;
import 'package:kanakku/state/settings.dart';

import 'common.dart';

const loanQ = 'A finance company is offering me a loan of 1,00,000 at 12% flat for 24 months. Should I take it?';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('failure paths', (tester) async {
    await freshInstall();
    await app.main();
    await waitFor(tester, find.text("Hello, I'm Alfii"));
    await tapAndSettle(tester, find.text('Start'));
    await tapAndSettle(tester, find.text('Skip all'));
    await waitFor(tester, find.text('Hold and talk'));

    log('Wrong token -> Test connection says so');
    await tapAndSettle(tester, find.byTooltip('Settings'));
    final tokenField = find.byType(TextField).at(1);
    await typeInto(tester, tokenField, 'wrong-token');
    await tapAndSettle(tester, find.text('Save and test connection'));
    await waitFor(tester, find.textContaining('access token is missing or wrong'), timeout: const Duration(seconds: 30));
    // a second enterText on the same field does not replace the text on a device; set it like a paste would
    tester.widget<TextField>(tokenField).controller!.text = SettingsProvider.defaultToken;
    await tester.pump(const Duration(milliseconds: 300));
    await tapAndSettle(tester, find.text('Save and test connection'));
    await waitFor(tester, find.textContaining('Connected'), timeout: const Duration(seconds: 30));
    expect(find.textContaining('Provider: local'), findsOneWidget);
    await back(tester);

    log('Oversized photo -> clear message');
    pickResult = (how, field) =>
        Upload(field, 'big_photo.png', [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, ...List.filled(9 * 1024 * 1024, 0)], 'image/png');
    await tapAndSettle(tester, find.byTooltip('Show a paper or photo'));
    await tapAndSettle(tester, find.text('Take a photo'));
    await typeInto(tester, find.byType(TextField).first, 'Is this offer good?');
    await tapAndSettle(tester, find.byTooltip('Send'));
    await waitFor(tester, find.textContaining('over the 8 MB limit'), timeout: const Duration(seconds: 60));
    expect(find.text('Retry'), findsOneWidget);
    await back(tester);
    await waitFor(tester, find.text('Hold and talk'));

    log('Server stopped mid-ask -> retry message, no crash (the runner stops the server when this ask arrives)');
    await typeInto(tester, find.byType(TextField).first, loanQ);
    await tapAndSettle(tester, find.byTooltip('Send'));
    await waitFor(tester, find.text('Checking'));
    await waitFor(
        tester,
        find.byWidgetPredicate((w) =>
            w is Text &&
            (w.data ?? '').contains('connection dropped') ||
            w is Text && (w.data ?? '').contains("can't reach the server")),
        timeout: const Duration(seconds: 200));
    expect(find.text('Retry'), findsOneWidget);
    expect(tester.takeException(), isNull);
    log('FAILURE PATHS PASSED');
  });
}
