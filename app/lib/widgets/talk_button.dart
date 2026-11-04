import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../core/speech.dart';
import '../theme.dart';

enum TalkZone { private, outLoud, cancel }

/// Hold the mic to talk. A full-screen overlay shows the three choices: slide UP = Private (the default, also when
/// you do not slide), slide DOWN = Out loud, slide SIDEWAYS = cancel. A haptic tick marks each change.
class TalkButton extends StatefulWidget {
  final void Function(List<int> audio, bool outLoud) onSend;
  const TalkButton({super.key, required this.onSend});

  @override
  State<TalkButton> createState() => _TalkButtonState();
}

class _TalkButtonState extends State<TalkButton> {
  final _rec = Recorder();
  final _zone = ValueNotifier(TalkZone.private);
  OverlayEntry? _overlay;
  bool _recording = false;
  static const _slide = 50.0, _sideways = 110.0;

  void _setZone(TalkZone z) {
    if (z != _zone.value) {
      HapticFeedback.selectionClick();
      _zone.value = z;
    }
  }

  void _closeOverlay() {
    _overlay?.remove();
    _overlay = null;
  }

  Future<void> _start(LongPressStartDetails _) async {
    HapticFeedback.mediumImpact();
    final ok = await _rec.start();
    if (!mounted) return;
    if (!ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please allow the microphone in your phone settings, or type instead.')),
      );
      return;
    }
    _recording = true;
    _zone.value = TalkZone.private;
    _overlay = OverlayEntry(builder: (_) => _GestureOverlay(zone: _zone));
    Overlay.of(context).insert(_overlay!);
  }

  void _move(LongPressMoveUpdateDetails d) {
    if (!_recording) return;
    final o = d.offsetFromOrigin;
    if (o.dx.abs() > _sideways) {
      _setZone(TalkZone.cancel);
    } else if (o.dy > _slide) {
      _setZone(TalkZone.outLoud);
    } else if (o.dy < -_slide) {
      _setZone(TalkZone.private);
    }
  }

  Future<void> _end(LongPressEndDetails _) async {
    if (!_recording) return;
    _recording = false;
    final zone = _zone.value;
    _closeOverlay();
    if (zone == TalkZone.cancel) {
      await _rec.cancel();
      return;
    }
    final audio = await _rec.stop();
    if (!mounted) return;
    if (audio == null) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('I did not hear anything. Hold the button while you talk.')));
      return;
    }
    widget.onSend(audio, zone == TalkZone.outLoud);
  }

  @override
  void dispose() {
    _closeOverlay();
    _zone.dispose();
    _rec.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Semantics(
    key: const ValueKey('talk_button'),
    button: true,
    label: 'Hold and talk. Slide up for private, down to say it out loud.',
    child: GestureDetector(
      onLongPressStart: _start,
      onLongPressMoveUpdate: _move,
      onLongPressEnd: _end,
      child: Container(
        width: 56,
        height: 56,
        decoration: BoxDecoration(color: K.alfii, borderRadius: BorderRadius.circular(14)),
        child: const Icon(LucideIcons.mic, color: Colors.white, size: 28),
      ),
    ),
  );
}

/// The three choices while the finger is down. It only shows; the finger stays on the mic button's detector.
class _GestureOverlay extends StatelessWidget {
  final ValueNotifier<TalkZone> zone;
  const _GestureOverlay({required this.zone});

  Widget _target(TalkZone me, TalkZone now, String title, String sub, IconData icon, Color color) {
    final active = me == now;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 120),
      width: double.infinity,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: active ? color : const Color(0xFF18181B),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color, width: 2),
      ),
      child: Column(
        children: [
          Icon(icon, color: Colors.white, size: 26),
          const SizedBox(height: 6),
          Text(
            title,
            style: const TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w700),
          ),
          Text(
            sub,
            textAlign: TextAlign.center,
            style: const TextStyle(color: Color(0xFFD4D4D8), fontSize: 16),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) => IgnorePointer(
    child: Material(
      color: const Color(0xE6090909),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: ValueListenableBuilder(
            valueListenable: zone,
            builder: (_, now, _) => Column(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _target(
                  TalkZone.private,
                  now,
                  'Slide UP: Private',
                  'The answer stays on the screen',
                  LucideIcons.lock,
                  K.alfii,
                ),
                Column(
                  children: [
                    Container(
                      width: 88,
                      height: 88,
                      decoration: const BoxDecoration(color: K.alfii, shape: BoxShape.circle),
                      child: const Icon(LucideIcons.mic, color: Colors.white, size: 40),
                    ),
                    const SizedBox(height: 14),
                    Text(
                      now == TalkZone.cancel ? 'Let go to cancel' : 'Listening… let go to send',
                      style: const TextStyle(color: Colors.white, fontSize: 21, fontWeight: FontWeight.w700),
                    ),
                    const Text('Slide sideways to cancel', style: TextStyle(color: Color(0xFFA1A1AA), fontSize: 16)),
                  ],
                ),
                _target(
                  TalkZone.outLoud,
                  now,
                  'Slide DOWN: Out loud',
                  'Alfii and the helpers will speak',
                  LucideIcons.volume2,
                  const Color(0xFFD97706),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}
