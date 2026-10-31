// Shared helpers for the on-device tests. They run against the REAL local server (make up PROVIDER=local).
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kanakku/core/api_client.dart';
import 'package:kanakku/core/pickers.dart';
import 'package:kanakku/core/speech.dart';
import 'package:kanakku/state/cases.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fixtures.dart';

/// TTS is replaced by a fake that records every spoken line (no audio on the emulator).
class FakeSpeaker extends Speaker {
  static final said = <String>[];
  FakeSpeaker() : super.base();
  @override
  Future<void> say(String text, {String speaker = 'alfii', String lang = 'en'}) async => said.add('$speaker: $text');
  @override
  Future<void> stop() async {}
}

/// The microphone is replaced by a fixture recording.
class FixtureRecorder extends Recorder {
  FixtureRecorder() : super.base();
  @override
  Future<bool> start() async => true;
  @override
  Future<List<int>?> stop() async => base64Decode(recordingWavBase64);
  @override
  Future<void> cancel() async {}
  @override
  void dispose() {}
}

/// What the camera / file picker returns: by default the fictional brochure PDF.
Upload? Function(String how, String field) pickResult =
    (how, field) => Upload(field, 'kanakavalli_brochure.pdf', base64Decode(brochurePdfBase64), 'application/pdf');

Future<void> freshInstall() async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.clear();
  await const FlutterSecureStorage().deleteAll();
  Speaker.create = FakeSpeaker.new;
  Recorder.create = FixtureRecorder.new;
  Pickers.pick = (how, field) async => pickResult(how, field);
}

/// Pumps until [finder] matches (real time: the real server and model answer at their own speed).
Future<void> waitFor(WidgetTester tester, Finder finder, {Duration timeout = const Duration(seconds: 150)}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    await tester.pump(const Duration(milliseconds: 300));
    if (finder.evaluate().isNotEmpty) return;
  }
  final onScreen = tester.widgetList<Text>(find.byType(Text)).map((t) => t.data ?? '').where((t) => t.isNotEmpty);
  throw TestFailure('Timed out after ${timeout.inSeconds}s waiting for $finder\nOn screen: ${onScreen.join(' | ')}');
}

/// Types into a text field. (On a device a second tester.enterText on the same field may not replace the text;
/// setting the controller is what a paste does.)
Future<void> typeInto(WidgetTester tester, Finder field, String text) async {
  await tester.ensureVisible(field);
  final controller = tester.widget<TextField>(field).controller;
  if (controller != null) {
    controller.text = text;
  } else {
    await tester.enterText(field, text);
  }
  await tester.pump(const Duration(milliseconds: 300));
}

/// Back one screen (like the phone's back button), after any page transition has finished.
Future<void> back(WidgetTester tester) async {
  for (var i = 0; i < 6; i++) {
    await tester.pump(const Duration(milliseconds: 150));
  }
  tester.state<NavigatorState>(find.byType(Navigator).first).maybePop();
  for (var i = 0; i < 6; i++) {
    await tester.pump(const Duration(milliseconds: 150));
  }
}

Future<void> tapAndSettle(WidgetTester tester, Finder finder) async {
  FocusManager.instance.primaryFocus?.unfocus(); // the keyboard would cover the target
  for (var i = 0; i < 4; i++) {
    await tester.pump(const Duration(milliseconds: 150));
  }
  await tester.ensureVisible(finder);
  await tester.pump(const Duration(milliseconds: 300));
  await tester.tap(finder);
  for (var i = 0; i < 6; i++) {
    await tester.pump(const Duration(milliseconds: 250));
  }
}

CaseProvider casesOf(WidgetTester tester) =>
    Provider.of<CaseProvider>(tester.element(find.byType(Navigator).first), listen: false);

void log(String step) => debugPrint('[demo] $step');
