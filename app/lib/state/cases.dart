import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/api_client.dart';
import '../core/models.dart';
import 'settings.dart';

String newKey() {
  final r = Random.secure();
  return List.generate(24, (_) => r.nextInt(36).toRadixString(36)).join();
}

/// What the user asked. [key] is the idempotency key: a Retry resends with the same key, so the server never
/// creates a second case for one question.
class AskRequest {
  final String key;
  final String text;
  final Upload? audio;
  final List<Upload> files;
  final bool outLoud;
  final int? caseId; // a follow-up continues this case (its documents still count)
  AskRequest({required this.text, this.audio, this.files = const [], this.outLoud = false, this.caseId, String? key})
      : key = key ?? newKey();

  String get label {
    final bits = [
      if (text.trim().isNotEmpty) text.trim(),
      if (audio != null) '🎙 Voice question',
      if (files.isNotEmpty) '📄 ${files.length} ${files.length == 1 ? 'page' : 'pages'}',
    ];
    return bits.join('  ·  ');
  }

  /// Only text questions survive an app restart in the offline queue; voice and photos wait in memory.
  Map<String, dynamic>? toJson() =>
      audio == null && files.isEmpty ? {'key': key, 'text': text, 'out_loud': outLoud} : null;
  static AskRequest fromJson(Map<String, dynamic> j) =>
      AskRequest(text: str(j['text']), outLoud: boolean(j['out_loud']), key: str(j['key'], newKey()));
}

enum AskStatus { queued, working, done, failed }

class ChatEntry {
  final AskRequest request;
  AskStatus status = AskStatus.working;
  int? caseId;
  CaseResult? result;
  String? error;
  ChatEntry(this.request);
}

class StepInfo {
  final String name;
  String state; // running | ok | degraded | failed
  StepInfo(this.name, this.state);
}

const stepWords = {
  'ingest': 'Reading what you sent',
  'scam_rules': 'Checking for tricks',
  'case_builder': 'Understanding the question',
  'verify_terms': 'Checking every amount twice',
  'compute': 'Doing the sums',
  'router': 'Choosing who to ask',
  'council': 'Asking the specialists',
  'debate': 'The specialists discuss',
  'consensus': 'Deciding',
  'privacy': 'Keeping your details private',
  'explainer': 'Writing the answer',
  'questions': 'Choosing what to ask them',
};

/// The chat, the running ask (with live steps from the server) and the offline queue.
class CaseProvider extends ChangeNotifier {
  final SettingsProvider settings;
  final List<ChatEntry> chat = [];
  final List<AskRequest> _queue = [];
  StreamSubscription<List<ConnectivityResult>>? _net;
  bool online = true;

  // the ask being worked on (for the Working screen)
  ChatEntry? current;
  String opener = '';
  final Set<String> called = {};
  final Set<String> doneAgents = {};
  final List<StepInfo> steps = [];

  static const queuedMessage = "I'll check this when the internet is back.";

  CaseProvider(this.settings);

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    for (final raw in prefs.getStringList('ask_queue') ?? <String>[]) {
      try {
        final req = AskRequest.fromJson(obj(jsonDecode(raw)));
        _queue.add(req);
        chat.add(ChatEntry(req)..status = AskStatus.queued);
      } catch (_) {}
    }
    try {
      online = !(await Connectivity().checkConnectivity()).every((c) => c == ConnectivityResult.none);
      _net = Connectivity().onConnectivityChanged.listen((r) {
        final now = !r.every((c) => c == ConnectivityResult.none);
        if (now && !online) _flush();
        online = now;
        notifyListeners();
      });
    } catch (_) {
      online = true;
    }
    notifyListeners();
    if (online) _flush();
  }

  Future<void> _saveQueue() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(
        'ask_queue', [for (final q in _queue) if (q.toJson() != null) jsonEncode(q.toJson())]);
  }

  Future<void> _flush() async {
    final pending = List<AskRequest>.from(_queue);
    _queue.clear();
    await _saveQueue();
    for (final req in pending) {
      final entry = chat.firstWhere((e) => e.request.key == req.key, orElse: () {
        final e = ChatEntry(req);
        chat.add(e);
        return e;
      });
      await _run(entry);
    }
  }

  Future<void> _enqueue(ChatEntry entry) async {
    entry
      ..status = AskStatus.queued
      ..error = null;
    if (!_queue.any((q) => q.key == entry.request.key)) _queue.add(entry.request);
    notifyListeners();
    await _saveQueue();
  }

  /// Ask a question. Returns the chat entry; the UI watches [current] while it runs.
  Future<ChatEntry> ask(AskRequest req) async {
    final entry = ChatEntry(req);
    chat.add(entry);
    notifyListeners();
    if (!online) {
      await _enqueue(entry);
      return entry;
    }
    await _run(entry);
    return entry;
  }

  /// Retry a failed or queued ask with the same idempotency key.
  Future<void> retry(ChatEntry entry) async {
    _queue.removeWhere((q) => q.key == entry.request.key);
    await _saveQueue();
    await _run(entry);
  }

  Future<void> _run(ChatEntry entry) async {
    final api = settings.api;
    current = entry;
    entry
      ..status = AskStatus.working
      ..error = null;
    opener = '';
    called.clear();
    doneAgents.clear();
    steps.clear();
    notifyListeners();
    try {
      final req = entry.request;
      entry.caseId = await api.startAsk(
        familyId: settings.familyId,
        text: req.text,
        audio: req.audio,
        files: req.files,
        outLoud: req.outLoud,
        earphones: settings.earphones,
        idempotencyKey: req.key,
        caseId: req.caseId,
      );
      await _follow(api, entry.caseId!);
      entry.result = await _result(api, entry.caseId!);
      entry.status = AskStatus.done;
    } on ApiException catch (e) {
      if (e.offline && entry.caseId == null) {
        await _enqueue(entry); // never reached the server: send it when the connection is back
      } else {
        entry
          ..status = AskStatus.failed
          ..error = e.offline ? 'The connection dropped. Your question is kept; tap Retry.' : e.friendly;
      }
    } catch (e) {
      entry
        ..status = AskStatus.failed
        ..error = 'Something went wrong. Tap Retry.';
    }
    notifyListeners();
  }

  /// Live progress from the server; if the event stream fails, the caller falls back to polling.
  Future<void> _follow(ApiClient api, int caseId) async {
    try {
      await for (final ev in api.events(caseId).timeout(const Duration(seconds: 90))) {
        switch (ev.type) {
          case 'step_started':
            steps.add(StepInfo(ev.step, 'running'));
          case 'step_finished':
            final s = steps.lastWhere((s) => s.name == ev.step, orElse: () {
              final n = StepInfo(ev.step, 'running');
              steps.add(n);
              return n;
            });
            s.state = str(ev.data['outcome'], 'ok');
          case 'alfii_opener':
            opener = str(ev.data['text']);
          case 'agent_called':
            called.add(ev.agent);
          case 'agent_done':
            doneAgents.add(ev.agent);
        }
        notifyListeners();
      }
    } catch (_) {
      // progress is a nicety; the answer is fetched below either way
    }
  }

  Future<CaseResult> _result(ApiClient api, int caseId) async {
    final deadline = DateTime.now().add(const Duration(seconds: 180));
    while (true) {
      final bundle = await api.caseBundle(caseId);
      final raw = bundle['result'];
      if (raw is Map) {
        try {
          return CaseResult.from(obj(raw));
        } catch (_) {
          throw ApiException('bad_response', 'The answer came back in a form I could not read. Tap Retry.');
        }
      }
      if (DateTime.now().isAfter(deadline)) {
        throw ApiException('timeout', 'This is taking too long. Tap Retry.');
      }
      await Future<void>.delayed(const Duration(seconds: 2));
    }
  }

  @override
  void dispose() {
    _net?.cancel();
    super.dispose();
  }
}
