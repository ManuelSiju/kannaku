// Every screen with real fixture answers, at phone size (390x844) and text scale 1.0 and 1.3: renders without
// overflow, verdicts show colour + icon + word, the main buttons are there. Goldens: test/goldens -> docs/screens.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kanakku/core/models.dart';
import 'package:kanakku/screens/council.dart';
import 'package:kanakku/screens/guardian.dart';
import 'package:kanakku/screens/home.dart';
import 'package:kanakku/screens/my_details.dart';
import 'package:kanakku/screens/settings_screen.dart';
import 'package:kanakku/screens/under_hood.dart';
import 'package:kanakku/screens/verdict.dart';
import 'package:kanakku/screens/welcome.dart';
import 'package:kanakku/screens/why.dart';
import 'package:kanakku/screens/working.dart';
import 'package:kanakku/state/cases.dart';
import 'package:kanakku/theme.dart';
import 'package:kanakku/widgets/common.dart';

import 'helpers.dart';

const verdictCases = {
  'endowment_red': 'red',
  'endowment_full': 'red',
  'loan_red': 'red',
  'stock_red': 'red',
  'scam': 'red',
  'out_of_scope': null,
  'degraded': 'yellow',
};

CaseProvider casesWith(FakeSettings s, List<String> names) {
  final c = CaseProvider(s);
  for (final n in names) {
    final r = result(n);
    c.chat.add(ChatEntry(AskRequest(text: 'Question for $n'))
      ..status = AskStatus.done
      ..caseId = r.caseId
      ..result = r);
  }
  return c;
}

void main() {
  setUp(FakeSpeaker.said.clear);

  for (final scale in [1.0, 1.3]) {
    group('text scale $scale', () {
      for (final MapEntry(key: name, value: colour) in verdictCases.entries) {
        testWidgets('verdict $name', (tester) async {
          final r = result(name);
          await pumpScreen(tester, VerdictScreen(result: r), textScale: scale);
          final style = VerdictStyle.of(colour);
          if (colour != null) {
            expect(find.text(style.word), findsOneWidget, reason: 'verdict word');
            expect(find.byIcon(style.icon), findsOneWidget, reason: 'verdict icon');
            final chip = tester.widget<Container>(
                find.descendant(of: find.byType(VerdictChip), matching: find.byType(Container)).first);
            expect((chip.decoration as BoxDecoration).color, style.solid, reason: 'verdict colour');
          }
          expect(find.text(r.shortAnswer), findsOneWidget);
          expect(find.text('Read aloud'), findsOneWidget);
          if (r.council.isNotEmpty) expect(find.text('Hear the council'), findsOneWidget);
          if (colour == 'red' && name != 'scam') expect(find.text('Help me say no'), findsOneWidget);
          if (r.notes.isNotEmpty) expect(find.text('Only on your screen'), findsOneWidget);
          if (r.localFallback || r.degraded) expect(find.byType(VerdictScreen), findsOneWidget);
          if (name == 'degraded') expect(find.text('partly checked'), findsOneWidget);
          await expectLater(find.byType(MaterialApp), matchesGoldenFile(golden('verdict_$name', scale)));
        });
      }

      testWidgets('welcome', (tester) async {
        await pumpScreen(tester, const WelcomeScreen(), textScale: scale);
        expect(find.text("Hello, I'm Alfii"), findsOneWidget);
        for (final l in ['മലയാളം', 'हिन्दी', 'English', 'Start']) {
          expect(find.text(l), findsOneWidget);
        }
        await expectLater(find.byType(MaterialApp), matchesGoldenFile(golden('welcome', scale)));
      });

      testWidgets('onboarding', (tester) async {
        await pumpScreen(tester, const OnboardingScreen(), textScale: scale);
        expect(find.text('What should I call you?'), findsOneWidget);
        expect(find.text('Skip all'), findsOneWidget);
        await expectLater(find.byType(MaterialApp), matchesGoldenFile(golden('onboarding', scale)));
      });

      testWidgets('home empty with a note from the guardian', (tester) async {
        await pumpScreen(tester, const HomeScreen(), textScale: scale);
        expect(find.text('Hold and talk'), findsOneWidget);
        expect(find.text('Type your question'), findsOneWidget);
        expect(find.textContaining('A note from Arun'), findsOneWidget);
        await expectLater(find.byType(MaterialApp), matchesGoldenFile(golden('home_empty', scale)));
      });

      testWidgets('home with answers', (tester) async {
        final s = FakeSettings(fakeServer());
        await pumpScreen(tester, const HomeScreen(),
            textScale: scale, cases: casesWith(s, ['scam', 'out_of_scope', 'endowment_red']));
        expect(find.text('Stop'), findsWidgets);
        expect(find.text('Read aloud'), findsWidgets);
        await expectLater(find.byType(MaterialApp), matchesGoldenFile(golden('home_answers', scale)));
      });

      testWidgets('working (live steps)', (tester) async {
        await pumpScreen(tester, WorkingScreen(request: AskRequest(text: 'Is this plan good?')),
            textScale: scale, client: fakeServer(hangCase: true), settle: false);
        expect(find.text('Let me ask Dani and Sankz.'), findsOneWidget);
        expect(find.text('Not needed'), findsOneWidget); // Vick
        expect(find.text('Alfii, just tell me'), findsOneWidget);
        await expectLater(find.byType(MaterialApp), matchesGoldenFile(golden('working', scale)));
        await tester.pump(const Duration(seconds: 70)); // let the hung request time out
        await tester.pump(const Duration(seconds: 1));
      });

      testWidgets('council plays every line through TTS', (tester) async {
        final r = result('endowment_red');
        await pumpScreen(tester, CouncilScreen(result: r), textScale: scale);
        expect(FakeSpeaker.said, hasLength(r.council.length));
        expect(find.text('Skip to Alfii'), findsOneWidget);
        await expectLater(find.byType(MaterialApp), matchesGoldenFile(golden('council', scale)));
      });

      testWidgets('why shows sources', (tester) async {
        await pumpScreen(tester, WhyScreen(result: result('endowment_red')), textScale: scale);
        expect(find.textContaining('Brochure page'), findsWidgets);
        await expectLater(find.byType(MaterialApp), matchesGoldenFile(golden('why', scale)));
      });

      testWidgets('under the hood', (tester) async {
        final s = FakeSettings(fakeServer());
        await pumpScreen(tester, const UnderHoodScreen(), textScale: scale, cases: casesWith(s, ['endowment_red']));
        expect(find.textContaining('Provider: local'), findsOneWidget);
        expect(find.text('Router'), findsOneWidget);
        await expectLater(find.byType(MaterialApp), matchesGoldenFile(golden('under_hood', scale)));
      });

      testWidgets('my details', (tester) async {
        await pumpScreen(tester, const MyDetailsScreen(), textScale: scale);
        expect(find.text('Income each month'), findsOneWidget);
        expect(find.text('Scooter loan EMI'), findsOneWidget, reason: 'items load ({"items": [...]})');
        expect(find.textContaining('Could not load'), findsNothing);
        for (final b in ['Say it', 'Show paper', 'Type it']) {
          expect(find.text(b), findsOneWidget);
        }
        await expectLater(find.byType(MaterialApp), matchesGoldenFile(golden('my_details', scale)));
      });

      testWidgets('confirm', (tester) async {
        await pumpScreen(tester, ConfirmScreen(proposal: Proposal.from(obj(fixture('proposal')))), textScale: scale);
        expect(find.textContaining('Save 1'), findsOneWidget);
        await expectLater(find.byType(MaterialApp), matchesGoldenFile(golden('confirm', scale)));
      });

      testWidgets('guardian alerts', (tester) async {
        await pumpScreen(tester, const GuardianScreen(), textScale: scale);
        expect(find.text('Mark handled'), findsWidgets);
        expect(find.text('Call'), findsWidgets);
        await expectLater(find.byType(MaterialApp), matchesGoldenFile(golden('guardian', scale)));
      });

      testWidgets('settings', (tester) async {
        await pumpScreen(tester, const SettingsScreen(), textScale: scale);
        for (final t in ['Server address', 'Save and test connection']) {
          expect(find.textContaining(t), findsWidgets);
        }
        await expectLater(find.byType(MaterialApp), matchesGoldenFile(golden('settings', scale)));
        await tester.scrollUntilVisible(find.text('Model provider'), 300, scrollable: find.byType(Scrollable).first);
        expect(find.text('App version'), findsOneWidget);
        expect(find.text('0.5.0+1'), findsOneWidget);
      });
    });
  }
}

