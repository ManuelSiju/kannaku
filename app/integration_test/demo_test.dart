// The whole demo path on a device, against the real local server and model:
// Welcome -> language -> Home -> endowment question + brochure PDF -> Working (live steps) -> Verdict red ->
// council (TTS fake) -> Why (sources) -> follow-up -> new verdict -> My details: type a value -> Confirm -> saved ->
// Guardian view: the alert -> note for Amma -> Home shows "A note from Arun"; hold-and-slide sends the right privacy.
//
// Run: scripts/app_integration.sh (starts the server, resets the demo family, records the screen)
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:kanakku/main.dart' as app;
import 'package:kanakku/state/cases.dart';

import 'common.dart';

const endowmentQ = 'An agent from the company says this plan is guaranteed to give 15 lakh. Should I take it?';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('demo path against the real server', (tester) async {
    await freshInstall();
    await app.main();
    await tester.pumpAndSettle();

    log('Welcome -> English -> Start -> skip onboarding');
    await waitFor(tester, find.text("Hello, I'm Alfii"));
    await tapAndSettle(tester, find.text('English'));
    await tapAndSettle(tester, find.text('Start'));
    await waitFor(tester, find.text('Skip all'));
    await tapAndSettle(tester, find.text('Skip all'));
    await waitFor(tester, talkHint);

    log('Home: attach the brochure PDF and type the endowment question');
    await tapAndSettle(tester, find.byTooltip('Show a paper or photo'));
    await tapAndSettle(tester, find.text('Choose a PDF'));
    expect(find.text('kanakavalli_brochure.pdf'), findsOneWidget);
    await typeInto(tester, find.byType(TextField).first, endowmentQ);
    await tapAndSettle(tester, find.byTooltip('Send'));

    log('Working: live steps from the server');
    await waitFor(tester, find.text('Checking'));
    await waitFor(tester, find.byWidgetPredicate((w) => w is Text && stepWords.values.contains(w.data)));

    log('Verdict: red; a private question stays on the screen; the council is played on request (TTS fake)');
    await waitFor(tester, find.text("Alfii's answer"), timeout: const Duration(seconds: 180));
    final first = casesOf(tester).chat.last.result!;
    expect(first.colour, 'red');
    expect(first.council, isNotEmpty);
    expect(find.text('Stop'), findsOneWidget);
    await tapAndSettle(tester, find.text('Hear the council'));
    await waitFor(tester, find.text('Skip to Alfii'));
    expect(FakeSpeaker.said.length, greaterThanOrEqualTo(first.council.length));
    await back(tester);
    await waitFor(tester, find.text("Alfii's answer"));

    log('Why: numbers with their sources');
    await tapAndSettle(tester, find.text('Why?'));
    await waitFor(tester, find.textContaining('Brochure page'));

    log('Follow-up on the same case');
    await typeInto(tester, find.byKey(const Key('followup_field')), 'What if I pay for 10 years?');
    await tapAndSettle(tester, find.byKey(const Key('followup_send')));
    await waitFor(tester, find.text('Checking'));
    final before = casesOf(tester).chat.length;
    await waitFor(tester, find.text("Alfii's answer"), timeout: const Duration(seconds: 180));
    final second = casesOf(tester).chat.last;
    expect(casesOf(tester).chat.length, before);
    expect(second.status, AskStatus.done);
    expect(second.caseId, first.caseId, reason: 'the follow-up continues the same case');
    log('follow-up verdict: ${second.result!.colour} — ${second.result!.shortAnswer}');
    await back(tester);
    await waitFor(tester, talkHint);

    log('My details: type a value -> Confirm -> saved');
    await tapAndSettle(tester, find.byKey(const Key('tab_details')));
    await waitFor(tester, find.text('kanakavalli_brochure.pdf'));
    expect(find.text('Insurance'), findsOneWidget, reason: 'the paper keeps its category');
    await tapAndSettle(tester, find.text('Type it'));
    await typeInto(tester, find.byType(TextField).last, 'My pension is 47,500 a month.');
    await tapAndSettle(tester, find.text('OK'));
    await waitFor(tester, find.text('Is this right?'));
    await tapAndSettle(tester, find.textContaining('Save 1'));
    await waitFor(tester, find.text('₹47,500'));

    log('Guardian view: the alert, then a note for Amma');
    await tapAndSettle(tester, find.byKey(const Key('tab_settings')));
    await tapSwitch(tester, find.byKey(const Key('guardian_switch')));
    await tapAndSettle(tester, find.byKey(const Key('tab_chat')));
    await waitFor(tester, find.text('Note for Amma'));
    await tapAndSettle(tester, find.text('Note for Amma').first);
    await typeInto(tester, find.byType(TextField).last, 'Please wait for me before you sign. I will call tonight.');
    await tapAndSettle(tester, find.text('Save'));
    await waitFor(tester, find.textContaining('Your note: Please wait'));

    log('Back to Amma: Home shows the note');
    await tapAndSettle(tester, find.byKey(const Key('tab_settings')));
    await tapSwitch(tester, find.byKey(const Key('guardian_switch')));
    await tapAndSettle(tester, find.byKey(const Key('tab_chat')));
    await waitFor(tester, find.text('A note from Arun'));

    for (final (dy, expected) in const [(140.0, 'full'), (-140.0, 'discreet')]) {
      log('Hold and talk, slide ${dy > 0 ? 'down (out loud)' : 'up (private)'}, release');
      await waitFor(tester, talkHint);
      final gesture = await tester.startGesture(tester.getCenter(find.byKey(const ValueKey('talk_button'))));
      await Future<void>.delayed(const Duration(milliseconds: 900));
      await tester.pump(const Duration(milliseconds: 100));
      await gesture.moveBy(Offset(0, dy / 2));
      await tester.pump(const Duration(milliseconds: 100));
      await gesture.moveBy(Offset(0, dy / 2));
      await tester.pump(const Duration(milliseconds: 100));
      await gesture.up();
      await waitFor(tester, find.text('Checking'));
      await waitFor(
        tester,
        find.byWidgetPredicate((w) => w is Text && (w.data == "Alfii's answer" || w.data == 'The council')),
        timeout: const Duration(seconds: 180),
      );
      final r = casesOf(tester).chat.last.result!;
      expect(r.privacyMode, expected, reason: 'slide ${dy > 0 ? 'down' : 'up'}');
      log('privacy_mode=${r.privacyMode} verdict=${r.colour}');
      while (talkHint.evaluate().isEmpty) {
        await back(tester);
        await tester.pump(const Duration(milliseconds: 500));
      }
    }
    log('DEMO PATH PASSED');
  });
}
