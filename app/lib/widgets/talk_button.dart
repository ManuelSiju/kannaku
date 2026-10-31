import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/speech.dart';
import '../theme.dart';

enum TalkZone { private, outLoud, cancel }

/// Hold to talk. While holding: slide UP = Private (default), slide DOWN = Out loud, slide sideways = cancel.
/// Releasing without sliding sends a Private question. A haptic tick marks each zone change.
class TalkButton extends StatefulWidget {
  final void Function(List<int> audio, bool outLoud) onSend;
  final bool earphones;
  const TalkButton({super.key, required this.onSend, this.earphones = false});

  @override
  State<TalkButton> createState() => _TalkButtonState();
}

class _TalkButtonState extends State<TalkButton> {
  final _rec = Recorder();
  bool _recording = false;
  TalkZone _zone = TalkZone.private;
  static const _slide = 50.0, _sideways = 110.0;

  void _setZone(TalkZone z) {
    if (z != _zone) {
      HapticFeedback.selectionClick();
      setState(() => _zone = z);
    }
  }

  Future<void> _start(LongPressStartDetails _) async {
    HapticFeedback.mediumImpact();
    final ok = await _rec.start();
    if (!mounted) return;
    if (!ok) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please allow the microphone in your phone settings, or type instead.')));
      return;
    }
    setState(() {
      _recording = true;
      _zone = TalkZone.private;
    });
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
    final zone = _zone;
    setState(() => _recording = false);
    if (zone == TalkZone.cancel) {
      await _rec.cancel();
      return;
    }
    final audio = await _rec.stop();
    if (!mounted) return;
    if (audio == null) {
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('I did not hear anything. Hold the button while you talk.')));
      return;
    }
    widget.onSend(audio, zone == TalkZone.outLoud);
  }

  @override
  void dispose() {
    _rec.dispose();
    super.dispose();
  }

  Widget _zoneLabel(String text, IconData icon, bool active, {Color color = K.alfii}) => AnimatedContainer(
        duration: const Duration(milliseconds: 120),
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
        decoration: BoxDecoration(
          color: active ? color : K.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: active ? color : K.line, width: 2),
        ),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(icon, color: active ? Colors.white : K.muted),
          const SizedBox(width: 8),
          Text(text,
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700, color: active ? Colors.white : K.muted)),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    final label = _recording
        ? (_zone == TalkZone.cancel ? 'Let go to cancel' : 'Listening… let go to send')
        : 'Hold and talk';
    return Column(mainAxisSize: MainAxisSize.min, children: [
      if (_recording) ...[
        _zoneLabel('↑ Private (only on screen)', Icons.lock_outline, _zone == TalkZone.private),
        const SizedBox(height: 6),
      ],
      Semantics(
        // keyed: the zone labels appear above it while recording, and the gesture must survive that rebuild
        key: const ValueKey('talk_button'),
        button: true,
        label: 'Hold and talk. Slide up for private, down to say it out loud.',
        child: GestureDetector(
          onLongPressStart: _start,
          onLongPressMoveUpdate: _move,
          onLongPressEnd: _end,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            height: 64,
            decoration: BoxDecoration(
              color: _zone == TalkZone.cancel && _recording ? K.muted : K.alfii,
              borderRadius: BorderRadius.circular(32),
              boxShadow: _recording ? [BoxShadow(color: K.alfii.withValues(alpha: 0.4), blurRadius: 18)] : null,
            ),
            child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
              Icon(_recording ? Icons.graphic_eq : Icons.mic, color: Colors.white, size: 30),
              const SizedBox(width: 10),
              Text(label, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w700)),
            ]),
          ),
        ),
      ),
      if (_recording) ...[
        const SizedBox(height: 6),
        _zoneLabel('↓ Out loud (say everything)', Icons.volume_up_outlined, _zone == TalkZone.outLoud,
            color: K.vick),
        const SizedBox(height: 4),
        const Text('Slide sideways to cancel', style: TextStyle(color: K.muted, fontSize: 15)),
      ] else if (widget.earphones)
        const Padding(
          padding: EdgeInsets.only(top: 6),
          child: Text('🎧 Earphones: private answers spoken', style: TextStyle(color: K.muted, fontSize: 15)),
        ),
    ]);
  }
}
