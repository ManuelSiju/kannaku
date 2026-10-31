import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/models.dart';
import '../core/speech.dart';
import '../state/settings.dart';
import '../theme.dart';
import '../widgets/common.dart';

/// Plays the council in order, one voice per speaker, with progress, pause, speed and "Skip to Alfii".
class CouncilScreen extends StatefulWidget {
  final CaseResult result;
  const CouncilScreen({super.key, required this.result});
  @override
  State<CouncilScreen> createState() => _CouncilScreenState();
}

class _CouncilScreenState extends State<CouncilScreen> {
  final _speaker = Speaker();
  int _index = 0;
  bool _playing = false;
  int _run = 0; // bumps on every play/stop so an old loop stops

  List<CouncilLine> get _lines => widget.result.council;

  @override
  void initState() {
    super.initState();
    _speaker.speed = context.read<SettingsProvider>().speechSpeed;
    WidgetsBinding.instance.addPostFrameCallback((_) => _play());
  }

  @override
  void dispose() {
    _run++;
    _speaker.stop();
    super.dispose();
  }

  Future<void> _play() async {
    final run = ++_run;
    final lang = context.read<SettingsProvider>().language;
    setState(() => _playing = true);
    while (mounted && run == _run && _index < _lines.length) {
      final line = _lines[_index];
      await _speaker.say(line.text, speaker: line.speaker, lang: lang);
      if (!mounted || run != _run) return;
      if (_index < _lines.length - 1) {
        setState(() => _index++);
      } else {
        break;
      }
    }
    if (mounted && run == _run) setState(() => _playing = false);
  }

  Future<void> _pause() async {
    _run++;
    await _speaker.stop();
    setState(() => _playing = false);
  }

  Future<void> _jump(int i) async {
    await _pause();
    setState(() => _index = i.clamp(0, _lines.length - 1));
    _play();
  }

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.of(context).disableAnimations;
    final settings = context.watch<SettingsProvider>();
    final conclusion = _lines.lastIndexWhere((l) => l.kind == 'conclusion');
    return Scaffold(
      appBar: AppBar(title: const Text('The council')),
      body: Column(children: [
        LinearProgressIndicator(value: _lines.isEmpty ? 0 : (_index + 1) / _lines.length, minHeight: 6),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: _lines.length,
            itemBuilder: (_, i) {
              final l = _lines[i];
              final active = i == _index;
              return Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: InkWell(
                  onTap: () => _jump(i),
                  borderRadius: BorderRadius.circular(18),
                  child: AnimatedContainer(
                    duration: Duration(milliseconds: reduceMotion ? 0 : 200),
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: active ? K.agent(l.speaker).withValues(alpha: 0.08) : K.surface,
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(color: active ? K.agent(l.speaker) : K.line, width: active ? 2 : 1),
                    ),
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      AgentAvatar(l.speaker, size: 40, dimmed: i > _index),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Row(children: [
                            Text(K.agentName(l.speaker),
                                style: TextStyle(fontWeight: FontWeight.w800, color: K.agent(l.speaker), fontSize: 17)),
                            const SizedBox(width: 8),
                            if (active && _playing) _VoiceBar(color: K.agent(l.speaker), still: reduceMotion),
                          ]),
                          const SizedBox(height: 4),
                          Text(l.text, style: TextStyle(fontSize: 18, color: i > _index ? K.muted : K.ink)),
                        ]),
                      ),
                    ]),
                  ),
                ),
              );
            },
          ),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
            child: Wrap(spacing: 8, runSpacing: 8, crossAxisAlignment: WrapCrossAlignment.center, children: [
              IconButton.filled(
                iconSize: 32,
                tooltip: _playing ? 'Pause' : 'Play',
                onPressed: _playing ? _pause : _play,
                icon: Icon(_playing ? Icons.pause : Icons.play_arrow),
              ),
              PopupMenuButton<double>(
                tooltip: 'Speed',
                initialValue: settings.speechSpeed,
                onSelected: (s) {
                  settings.set(speechSpeed: s);
                  _speaker.speed = s;
                },
                itemBuilder: (_) => [
                  for (final s in const [0.75, 1.0, 1.25]) PopupMenuItem(value: s, child: Text('${s}x')),
                ],
                child: Pill('${settings.speechSpeed}x', icon: Icons.speed),
              ),
              if (conclusion >= 0)
                FilledButton.tonalIcon(
                    onPressed: () => _jump(conclusion),
                    icon: const Icon(Icons.skip_next),
                    label: const Text('Skip to Alfii')),
            ]),
          ),
        ),
      ]),
    );
  }
}

class _VoiceBar extends StatefulWidget {
  final Color color;
  final bool still;
  const _VoiceBar({required this.color, required this.still});
  @override
  State<_VoiceBar> createState() => _VoiceBarState();
}

class _VoiceBarState extends State<_VoiceBar> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 700));

  @override
  void initState() {
    super.initState();
    if (!widget.still) _c.repeat(reverse: true);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Semantics(
        label: 'speaking',
        child: AnimatedBuilder(
          animation: _c,
          builder: (_, _) => Row(children: [
            for (var i = 0; i < 4; i++)
              Container(
                width: 4,
                height: 6 + 12 * (widget.still ? 0.5 : ((_c.value + i * 0.25) % 1.0)),
                margin: const EdgeInsets.symmetric(horizontal: 1.5),
                decoration: BoxDecoration(color: widget.color, borderRadius: BorderRadius.circular(2)),
              ),
          ]),
        ),
      );
}
