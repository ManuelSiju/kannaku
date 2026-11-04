import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../core/speech.dart';
import '../theme.dart';

enum TalkZone { private, outLoud, cancel }

/// Press and hold the mic to talk; a quick tap explains that. While held, an overlay shows the choices for this question:
/// slide UP = Private, slide DOWN = Out loud, slide SIDEWAYS = cancel. With no slide, or back at the centre, the header
/// pill's setting stands, and a slide never changes that setting. The circle follows the finger.
class TalkButton extends StatefulWidget {
  final bool outLoud; // the header pill
  final void Function(List<int> audio, bool outLoud) onSend;
  const TalkButton({super.key, required this.onSend, this.outLoud = false});

  @override
  State<TalkButton> createState() => _TalkButtonState();
}

class _TalkButtonState extends State<TalkButton> {
  final _rec = Recorder();
  final _zone = ValueNotifier(TalkZone.private);
  final _finger = ValueNotifier(Offset.zero);
  OverlayEntry? _overlay;
  bool _held = false, _recording = false;
  Future<bool>? _started;
  static const _slide = 50.0, _centre = 28.0, _sideways = 110.0;

  TalkZone get _pill => widget.outLoud ? TalkZone.outLoud : TalkZone.private;

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

  void _tip() => ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(const SnackBar(content: Text('Press and hold the mic, talk, then let go.')));

  /// The overlay comes first, so the finger gets an answer at once; the microphone starts behind it.
  Future<void> _start(LongPressStartDetails _) async {
    HapticFeedback.mediumImpact();
    _closeOverlay(); // never two overlays: one left behind could not be removed
    _held = true;
    _zone.value = _pill;
    _finger.value = Offset.zero;
    _overlay = OverlayEntry(
      builder: (_) => _GestureOverlay(zone: _zone, finger: _finger, pill: _pill),
    );
    Overlay.of(context).insert(_overlay!);
    final started = _started = _rec.start();
    final ok = await started;
    if (!mounted) return;
    _recording = ok;
    if (!ok) {
      _held = false;
      _closeOverlay();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please allow the microphone in your phone settings, or type instead.')),
      );
    }
  }

  void _move(LongPressMoveUpdateDetails d) {
    if (!_held) return;
    final o = d.offsetFromOrigin;
    _finger.value = o;
    if (o.dx.abs() > _sideways) {
      _setZone(TalkZone.cancel);
    } else if (o.dy > _slide) {
      _setZone(TalkZone.outLoud);
    } else if (o.dy < -_slide) {
      _setZone(TalkZone.private);
    } else if (o.dy.abs() < _centre && o.dx.abs() < _sideways - _centre) {
      _setZone(_pill); // back at the centre: changed your mind
    }
  }

  /// The system took the gesture away (a rotation, a call): nothing is sent and nothing stays on screen.
  Future<void> _lost() async {
    _held = false;
    _closeOverlay();
    await _started;
    if (_recording) {
      _recording = false;
      await _rec.cancel();
    }
  }

  Future<void> _end(LongPressEndDetails _) async {
    if (!_held) return;
    _held = false;
    final zone = _zone.value;
    _closeOverlay();
    await _started; // a very quick tap can end before the microphone is ready
    if (!_recording) return;
    _recording = false;
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
    _finger.dispose();
    _rec.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Semantics(
    key: const ValueKey('talk_button'),
    button: true,
    label: 'Hold and talk. Slide up for private, down to say it out loud.',
    child: RawGestureDetector(
      gestures: {
        // A deliberate press, shorter than the default half second, which feels like the button is stuck.
        LongPressGestureRecognizer: GestureRecognizerFactoryWithHandlers<LongPressGestureRecognizer>(
          () => LongPressGestureRecognizer(duration: const Duration(milliseconds: 300)),
          (r) => r
            ..onLongPressStart = _start
            ..onLongPressMoveUpdate = _move
            ..onLongPressEnd = _end
            ..onLongPressCancel = _lost,
        ),
        TapGestureRecognizer: GestureRecognizerFactoryWithHandlers<TapGestureRecognizer>(
          TapGestureRecognizer.new,
          (r) => r.onTap = _tip,
        ),
      },
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
  final ValueNotifier<Offset> finger;
  final TalkZone pill;
  const _GestureOverlay({required this.zone, required this.finger, required this.pill});

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
                    ValueListenableBuilder(
                      valueListenable: finger,
                      builder: (_, o, child) => Transform.translate(
                        offset: Offset(o.dx.clamp(-120, 120), o.dy.clamp(-120, 120)),
                        child: child,
                      ),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 120),
                        width: 88,
                        height: 88,
                        decoration: BoxDecoration(
                          color: switch (now) {
                            TalkZone.private => K.alfii,
                            TalkZone.outLoud => const Color(0xFFD97706),
                            TalkZone.cancel => const Color(0xFF52525B),
                          },
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(LucideIcons.mic, color: Colors.white, size: 40),
                      ),
                    ),
                    const SizedBox(height: 14),
                    Text(switch (now) {
                      TalkZone.cancel => 'Let go to cancel',
                      TalkZone.outLoud => 'Listening… answer out loud',
                      TalkZone.private => 'Listening… answer private',
                    }, style: const TextStyle(color: Colors.white, fontSize: 21, fontWeight: FontWeight.w700)),
                    Text(
                      'No slide: ${pill == TalkZone.outLoud ? 'Out loud' : 'Private'}. Slide sideways to cancel.',
                      style: const TextStyle(color: Color(0xFFA1A1AA), fontSize: 16),
                    ),
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
