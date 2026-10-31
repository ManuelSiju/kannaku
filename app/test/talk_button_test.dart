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

  for (final (name, dy, outLoud) in const [('slide up = private', -120.0, false), ('slide down = out loud', 120.0, true), ('no slide = private', 0.0, false)]) {
    testWidgets(name, (tester) async {
      bool? sent;
      await tester.pumpWidget(MaterialApp(
          home: Scaffold(body: Center(child: TalkButton(onSend: (audio, loud) => sent = loud)))));
      final g = await tester.startGesture(tester.getCenter(find.text('Hold and talk')));
      await tester.pump(const Duration(milliseconds: 700));
      await tester.pump();
      expect(find.text('Listening… let go to send'), findsOneWidget);
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
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: Center(child: TalkButton(onSend: (_, _) => sent = true)))));
    final g = await tester.startGesture(tester.getCenter(find.text('Hold and talk')));
    await tester.pump(const Duration(milliseconds: 700));
    await g.moveBy(const Offset(160, 0));
    await tester.pump();
    expect(find.text('Let go to cancel'), findsOneWidget);
    await g.up();
    await tester.pumpAndSettle();
    expect(sent, isFalse);
  });
}
