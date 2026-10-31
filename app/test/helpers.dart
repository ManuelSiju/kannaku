import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:kanakku/core/api_client.dart';
import 'package:kanakku/core/models.dart';
import 'package:kanakku/core/speech.dart';
import 'package:kanakku/state/cases.dart';
import 'package:kanakku/state/profile.dart';
import 'package:kanakku/state/settings.dart';
import 'package:kanakku/theme.dart';
import 'package:provider/provider.dart';

/// Real server responses exported by `make app-fixtures` (server/scripts/export_app_fixtures.py).
dynamic fixture(String name) => jsonDecode(File('test/fixtures/$name.json').readAsStringSync());

CaseResult result(String name) => CaseResult.from(obj(fixture(name)['result']));

/// Settings without platform plugins, talking to a fake server.
class FakeSettings extends SettingsProvider {
  FakeSettings(http.Client client, {String lang = 'en'}) {
    httpClient = client;
    deviceId = 'test-device';
    language = lang;
    appVersion = '0.5.0+1';
    userName = 'Lakshmi';
  }

  @override
  Future<void> set({
    int? familyId,
    String? language,
    String? userName,
    bool? welcomed,
    bool? guardianView,
    bool? earphones,
    double? speechSpeed,
  }) async {
    if (language != null) this.language = language;
    if (guardianView != null) this.guardianView = guardianView;
    if (earphones != null) this.earphones = earphones;
    if (speechSpeed != null) this.speechSpeed = speechSpeed;
    if (userName != null) this.userName = userName;
    notifyListeners();
  }
}

/// Records what would have been spoken.
class FakeSpeaker extends Speaker {
  static final said = <String>[];
  FakeSpeaker() : super.base();
  @override
  Future<void> say(String text, {String speaker = 'alfii', String lang = 'en'}) async => said.add('$speaker: $text');
  @override
  Future<void> stop() async {}
}

/// A fake server answering from the fixtures; [caseFixture] is what GET /v1/cases/{id} returns.
MockClient fakeServer({String caseFixture = 'endowment_red', bool hangCase = false}) => MockClient((req) async {
      final p = req.url.path;
      String body;
      if (p.endsWith('/health')) {
        body = jsonEncode(fixture('health'));
      } else if (p.endsWith('/profile')) {
        body = jsonEncode(fixture('profile'));
      } else if (p.endsWith('/items')) {
        body = jsonEncode(fixture('items'));
      } else if (p.endsWith('/alerts')) {
        body = jsonEncode(fixture('alerts'));
      } else if (p.endsWith('/notes')) {
        body = jsonEncode(fixture('notes'));
      } else if (p.endsWith('/extract')) {
        body = jsonEncode(fixture('proposal'));
      } else if (p.endsWith('/events')) {
        return http.Response(
            [
              'event: step_started\ndata: {"type":"step_started","step":"case_builder"}\n',
              'event: step_finished\ndata: {"type":"step_finished","step":"case_builder","outcome":"ok"}\n',
              'event: alfii_opener\ndata: {"type":"alfii_opener","text":"Let me ask Dani and Sankz."}\n',
              'event: agent_called\ndata: {"type":"agent_called","agent":"dani"}\n',
              'event: agent_called\ndata: {"type":"agent_called","agent":"sankz"}\n',
              'event: step_started\ndata: {"type":"step_started","step":"council"}\n',
              'event: done\ndata: {"type":"done"}\n',
            ].join('\n'),
            200);
      } else if (req.method == 'POST' && p.endsWith('/cases')) {
        body = jsonEncode({'case_id': 1, 'status': 'running'});
        return http.Response(body, 202, headers: {'content-type': 'application/json'});
      } else if (p.contains('/cases/')) {
        if (hangCase) await Completer<void>().future;
        final f = obj(fixture(caseFixture));
        body = jsonEncode({...obj(f['bundle']), 'result': f['result']});
      } else {
        return http.Response('{"error":{"code":"not_found","message":"no route","request_id":"t"}}', 404);
      }
      return http.Response.bytes(utf8.encode(body), 200, headers: {'content-type': 'application/json; charset=utf-8'});
    });

bool _fontsLoaded = false;

/// Loads the app's bundled fonts and Material icons so screenshots show real text, not boxes.
Future<void> loadFonts() async {
  if (_fontsLoaded) return;
  _fontsLoaded = true;
  final manifest = jsonDecode(await rootBundle.loadString('FontManifest.json')) as List;
  for (final family in manifest) {
    final loader = FontLoader(family['family'] as String);
    for (final font in family['fonts'] as List) {
      loader.addFont(rootBundle.load(font['asset'] as String));
    }
    await loader.load();
  }
}

/// Pumps [screen] at phone size (390x844 logical) with the providers the app uses.
Future<FakeSettings> pumpScreen(WidgetTester tester, Widget screen,
    {double textScale = 1.0, http.Client? client, String lang = 'en', CaseProvider? cases, bool settle = true}) async {
  await loadFonts();
  Speaker.create = FakeSpeaker.new;
  tester.view.physicalSize = const Size(780, 1688);
  tester.view.devicePixelRatio = 2.0;
  addTearDown(tester.view.reset);
  final settings = FakeSettings(client ?? fakeServer(), lang: lang);
  await tester.pumpWidget(MultiProvider(
    providers: [
      ChangeNotifierProvider<SettingsProvider>.value(value: settings),
      ChangeNotifierProvider<CaseProvider>.value(value: cases ?? CaseProvider(settings)),
      ChangeNotifierProvider(create: (_) => ProfileProvider(settings)),
    ],
    child: MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      builder: (context, child) =>
          MediaQuery(data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(textScale)), child: child!),
      home: screen,
    ),
  ));
  if (settle) {
    await tester.pumpAndSettle();
  } else {
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
  }
  return settings;
}

/// Golden file name for a screen at a text scale, e.g. goldens/verdict_endowment_red@1.3.png.
String golden(String name, double scale) => 'goldens/$name@$scale.png';

/// An ApiClient-level upload for tests.
Upload pdfUpload() => Upload('files', 'kanakavalli_brochure.pdf', utf8.encode('%PDF-1.4 test'), 'application/pdf');
