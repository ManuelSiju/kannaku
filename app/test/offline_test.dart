import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kanakku/app.dart';
import 'package:kanakku/state/cases.dart';
import 'package:kanakku/state/settings.dart';
import 'package:kanakku/theme.dart';
import 'package:kanakku/widgets/common.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Settings without plugins: the defaults, plus a fake HTTP client.
class FakeSettings extends SettingsProvider {
  FakeSettings(http.Client client) {
    httpClient = client;
    deviceId = 'test-device';
  }
}

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({}));

  test('the network dying during an ask gives a retry message, not a crash', () async {
    var calls = 0;
    final client = MockClient((req) async {
      calls++;
      if (req.method == 'POST') {
        return http.Response(jsonEncode({'case_id': 5, 'status': 'running'}), 202);
      }
      throw const SocketException('Network is unreachable');
    });
    final cases = CaseProvider(FakeSettings(client));
    final entry = await cases.ask(AskRequest(text: 'Is this loan ok?'));
    expect(entry.status, AskStatus.failed);
    expect(entry.error, contains('Retry'));
    expect(entry.caseId, 5);
    expect(calls, greaterThanOrEqualTo(2));
  });

  test('a question that never reached the server is queued for later', () async {
    final client = MockClient((req) async => throw const SocketException('offline'));
    final cases = CaseProvider(FakeSettings(client));
    final entry = await cases.ask(AskRequest(text: 'Is this loan ok?'));
    expect(entry.status, AskStatus.queued);
    final prefs = await SharedPreferences.getInstance();
    expect(prefs.getStringList('ask_queue'), hasLength(1));
  });

  test('retry reuses the idempotency key and gets the answer', () async {
    final keys = <String?>[];
    var online = false;
    final client = MockClient((req) async {
      if (!online) throw const SocketException('offline');
      if (req.method == 'POST') {
        keys.add(req.headers['Idempotency-Key']);
        return http.Response(jsonEncode({'case_id': 9, 'status': 'running'}), 202);
      }
      if (req.url.path.endsWith('/events')) {
        return http.Response('event: done\ndata: {"type":"done"}\n\n', 200);
      }
      return http.Response(
        jsonEncode({
          'result': {
            'case_id': 9,
            'verdict': {'colour': 'red', 'sentence': 'Please do not sign.'},
            'short_answer': {'text': "Please don't go ahead with this as it is."},
          },
        }),
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      );
    });
    final cases = CaseProvider(FakeSettings(client));
    final entry = await cases.ask(AskRequest(text: 'Is this loan ok?'));
    expect(entry.status, AskStatus.queued);
    online = true;
    await cases.retry(entry);
    expect(entry.status, AskStatus.done);
    expect(entry.result!.colour, 'red');
    expect(keys.single, entry.request.key);
  });

  testWidgets('verdict chip always shows icon and word', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData(),
        home: const Scaffold(body: Column(children: [VerdictChip('red'), VerdictChip('yellow'), VerdictChip('green')])),
      ),
    );
    expect(find.text('Stop'), findsOneWidget);
    expect(find.text('Careful'), findsOneWidget);
    expect(find.text('Looks fine'), findsOneWidget);
    expect(find.byIcon(VerdictStyle.red.icon), findsOneWidget);
  });

  testWidgets('error card offers Retry', (tester) async {
    var tapped = false;
    await tester.pumpWidget(KanakkuFrame(home: Scaffold(body: ErrorCard('The connection dropped. Tap Retry.', onRetry: () => tapped = true)),
      ),
    );
    await tester.tap(find.text('Retry'));
    expect(tapped, isTrue);
  });
}
