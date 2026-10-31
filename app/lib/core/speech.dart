import 'dart:io';

import 'package:flutter_tts/flutter_tts.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

/// One voice per speaker (configurable): pitch and rate make Alfii, Sankz, Dani and Vick easy to tell apart.
class Voice {
  final double pitch, rate;
  const Voice(this.pitch, this.rate);
}

const voices = <String, Voice>{
  'alfii': Voice(1.0, 0.45),
  'sankz': Voice(0.85, 0.44),
  'dani': Voice(1.2, 0.46),
  'vick': Voice(0.75, 0.47),
};

String ttsLocale(String lang) => switch (lang) {
      'ml' => 'ml-IN',
      'hi' => 'hi-IN',
      _ => 'en-IN',
    };

class Speaker {
  final FlutterTts _tts = FlutterTts();
  bool _ready = false;
  double speed = 1.0;

  Future<void> _init() async {
    if (_ready) return;
    _ready = true;
    try {
      await _tts.awaitSpeakCompletion(true);
    } catch (_) {}
  }

  /// Speaks and completes when done (or at once if TTS is unavailable). Never throws.
  Future<void> say(String text, {String speaker = 'alfii', String lang = 'en'}) async {
    if (text.trim().isEmpty) return;
    try {
      await _init();
      final v = voices[speaker] ?? voices['alfii']!;
      await _tts.setLanguage(ttsLocale(lang));
      await _tts.setPitch(v.pitch);
      await _tts.setSpeechRate((v.rate * speed).clamp(0.2, 0.9));
      await _tts.speak(text);
    } catch (_) {}
  }

  Future<void> stop() async {
    try {
      await _tts.stop();
    } catch (_) {}
  }
}

/// Hold-to-talk recording to an .m4a file.
class Recorder {
  final AudioRecorder _rec = AudioRecorder();
  String? _path;

  Future<bool> start() async {
    try {
      if (!await _rec.hasPermission()) return false;
      final dir = await getTemporaryDirectory();
      _path = '${dir.path}/ask_${DateTime.now().millisecondsSinceEpoch}.m4a';
      await _rec.start(const RecordConfig(encoder: AudioEncoder.aacLc, sampleRate: 16000, numChannels: 1),
          path: _path!);
      return true;
    } catch (_) {
      return false;
    }
  }

  /// The recorded bytes, or null if nothing usable was recorded.
  Future<List<int>?> stop() async {
    try {
      final path = await _rec.stop() ?? _path;
      if (path == null) return null;
      final f = File(path);
      if (!await f.exists()) return null;
      final bytes = await f.readAsBytes();
      await f.delete();
      return bytes.length > 2000 ? bytes : null;
    } catch (_) {
      return null;
    }
  }

  Future<void> cancel() async {
    try {
      await _rec.cancel();
    } catch (_) {}
  }

  void dispose() => _rec.dispose();
}
