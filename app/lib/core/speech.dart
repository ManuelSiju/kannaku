import 'dart:io';

import 'package:flutter/foundation.dart';
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

/// A different installed voice per speaker for this locale: on-device voices first, sorted so the choice is stable.
/// Empty when fewer than two exist; then the pitch and rate above tell the speakers apart.
Map<String, Map<String, String>> assignVoices(List<Map<String, String>> installed, String locale) {
  final want = locale.toLowerCase().replaceAll('_', '-');
  final all = [
    for (final v in installed)
      if ((v['locale'] ?? '').toLowerCase().replaceAll('_', '-') == want) v,
  ];
  final local = all.where((v) => (v['name'] ?? '').contains('local')).toList();
  final pool = (local.length >= 2 ? local : all)..sort((a, b) => (a['name'] ?? '').compareTo(b['name'] ?? ''));
  if (pool.length < 2) return {};
  final speakers = voices.keys.toList();
  return {for (var i = 0; i < speakers.length; i++) speakers[i]: pool[i % pool.length]};
}

const _ones = [
  'zero',
  'one',
  'two',
  'three',
  'four',
  'five',
  'six',
  'seven',
  'eight',
  'nine',
  'ten',
  'eleven',
  'twelve',
  'thirteen',
  'fourteen',
  'fifteen',
  'sixteen',
  'seventeen',
  'eighteen',
  'nineteen',
]; // fmt: skip
const _tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'];

String _words(int n) {
  if (n < 20) return _ones[n];
  if (n < 100) return '${_tens[n ~/ 10]}${n % 10 == 0 ? '' : ' ${_ones[n % 10]}'}';
  return '${_ones[n ~/ 100]} hundred${n % 100 == 0 ? '' : ' ${_words(n % 100)}'}';
}

/// English voices misread digits before lakh and crore ("7.5 lakh" comes out as a long number), so those are said in
/// words: "seven point five lakh". The text on screen keeps its digits.
String speakable(String text, String lang) {
  if (lang != 'en') return text;
  return text.replaceAllMapped(RegExp(r'(\d{1,3})(?:\.(\d+))?\s*(lakhs?|crores?)', caseSensitive: false), (m) {
    final point = m[2] == null ? '' : ' point ${m[2]!.split('').map((d) => _ones[int.parse(d)]).join(' ')}';
    return '${_words(int.parse(m[1]!))}$point ${m[3]}';
  });
}

String ttsLocale(String lang) => switch (lang) {
  'ml' => 'ml-IN',
  'hi' => 'hi-IN',
  _ => 'en-IN',
};

/// Text-to-speech. Tests replace [Speaker.create] with a fake that records what was said.
class Speaker {
  static Speaker Function() create = Speaker.base;
  factory Speaker() => create();
  Speaker.base();

  FlutterTts? _ttsInstance;
  FlutterTts get _tts => _ttsInstance ??= FlutterTts();
  bool _ready = false;
  double speed = 1.0;
  final _assigned = <String, Map<String, Map<String, String>>>{};

  Future<Map<String, Map<String, String>>> _voicesFor(String locale) async {
    final known = _assigned[locale];
    if (known != null) return known;
    var found = <String, Map<String, String>>{};
    try {
      final list = await _tts.getVoices as List<dynamic>;
      final installed = [for (final v in list) (v as Map).map((k, x) => MapEntry('$k', '$x'))];
      found = assignVoices(installed, locale);
      debugPrint('voices $locale: ${found.map((k, v) => MapEntry(k, v['name']))}');
    } catch (_) {}
    return _assigned[locale] = found;
  }

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
      final locale = ttsLocale(lang);
      await _tts.setLanguage(locale);
      final own = (await _voicesFor(locale))[speaker];
      if (own != null) await _tts.setVoice({'name': own['name']!, 'locale': own['locale']!});
      await _tts.setPitch(own == null ? v.pitch : 1.0);
      await _tts.setSpeechRate((v.rate * speed).clamp(0.2, 0.9));
      await _tts.speak(speakable(text, lang));
    } catch (_) {}
  }

  Future<void> stop() async {
    try {
      await _tts.stop();
    } catch (_) {}
  }
}

/// Hold-to-talk recording to an .m4a file. Tests replace [Recorder.create] (e.g. with a fixture recording).
class Recorder {
  static Recorder Function() create = Recorder.base;
  factory Recorder() => create();
  Recorder.base();

  AudioRecorder? _recInstance;
  AudioRecorder get _rec => _recInstance ??= AudioRecorder();
  String? _path;

  Future<bool> start() async {
    try {
      if (!await _rec.hasPermission()) return false;
      final dir = await getTemporaryDirectory();
      _path = '${dir.path}/ask_${DateTime.now().millisecondsSinceEpoch}.m4a';
      await _rec.start(
        const RecordConfig(encoder: AudioEncoder.aacLc, sampleRate: 16000, numChannels: 1),
        path: _path!,
      );
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

  void dispose() => _recInstance?.dispose();
}
