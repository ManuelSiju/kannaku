import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kanakku/core/speech.dart';
import 'package:kanakku/widgets/talk_button.dart';

class FakeRecorder extends Recorder {
  FakeRecorder() : super.base();
  @override
  Future<bool> start() async => true;
  @override
  Future<List<int>?> stop() async => List.filled(5000, 1);
  @override
  Future<void> cancel() async {}
  @override
  void dispose() {}
}

void main() {
  setUp(() => Recorder.create = FakeRecorder.new);

  Future<TestGesture> hold(WidgetTester tester, void Function(bool) onSent, {bool pill = false}) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: TalkButton(outLoud: pill, onSend: (audio, loud) => onSent(loud)),
          ),
        ),
      ),
    );
    final g = await tester.startGesture(tester.getCenter(find.byKey(const ValueKey('talk_button'))));
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pump();
    return g;
  }

  testWidgets('it reacts within 200 ms and the pill sets the default', (tester) async {
    bool? sent;
    final g = await hold(tester, (v) => sent = v, pill: true);
    expect(find.text('Listening… answer out loud'), findsOneWidget);
    await g.up();
    await tester.pumpAndSettle();
    expect(sent, isTrue);
  });

  testWidgets('back at the centre undoes a slide', (tester) async {
    bool? sent;
    final g = await hold(tester, (v) => sent = v);
    await g.moveBy(const Offset(0, 120));
    await tester.pump();
    expect(find.text('Listening… answer out loud'), findsOneWidget);
    await g.moveBy(const Offset(0, -115));
    await tester.pump();
    expect(find.text('Listening… answer private'), findsOneWidget);
    await g.up();
    await tester.pumpAndSettle();
    expect(sent, isFalse);
  });

  for (final (name, dy, outLoud) in const [
    ('slide up = private', -120.0, false),
    ('slide down = out loud', 120.0, true),
    ('no slide = private', 0.0, false),
  ]) {
    testWidgets(name, (tester) async {
      bool? sent;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Center(child: TalkButton(onSend: (audio, loud) => sent = loud)),
          ),
        ),
      );
      final g = await tester.startGesture(tester.getCenter(find.byKey(const ValueKey('talk_button'))));
      await tester.pump(const Duration(milliseconds: 700));
      await tester.pump();
      expect(find.text('Listening… answer private'), findsOneWidget);
      await g.moveBy(Offset(0, dy / 2));
      await tester.pump();
      await g.moveBy(Offset(0, dy / 2));
      await tester.pump();
      await g.up();
      await tester.pumpAndSettle();
      expect(sent, outLoud);
    });
  }

  testWidgets('slide sideways cancels', (tester) async {
    var sent = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(child: TalkButton(onSend: (_, _) => sent = true)),
        ),
      ),
    );
    final g = await tester.startGesture(tester.getCenter(find.byKey(const ValueKey('talk_button'))));
    await tester.pump(const Duration(milliseconds: 700));
    await g.moveBy(const Offset(160, 0));
    await tester.pump();
    expect(find.text('Let go to cancel'), findsOneWidget);
    await g.up();
    await tester.pumpAndSettle();
    expect(sent, isFalse);
  });
}
