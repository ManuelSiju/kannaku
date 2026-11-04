import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../core/speech.dart';
import '../state/cases.dart';
import '../state/settings.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'verdict.dart';

/// While the council works: Alfii's opener, the called agents (others "Not needed"), live steps from the server,
/// and "Alfii, just tell me" (skip the council, hear the short answer).
class WorkingScreen extends StatefulWidget {
  final AskRequest? request; // a new ask
  final ChatEntry? entry; // or a retry
  const WorkingScreen({super.key, this.request, this.entry});
  @override
  State<WorkingScreen> createState() => _WorkingScreenState();
}

class _WorkingScreenState extends State<WorkingScreen> {
  final _speaker = Speaker();
  ChatEntry? _entry;
  bool _justTell = false;
  String _spokenOpener = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _go());
  }

  Future<void> _go() async {
    final cases = context.read<CaseProvider>();
    final settings = context.read<SettingsProvider>();
    final lang = settings.language;
    if (widget.entry != null) {
      _entry = widget.entry;
      await cases.retry(widget.entry!);
    } else {
      _entry = await cases.ask(widget.request!);
    }
    if (!mounted) return;
    final e = _entry!;
    if (e.status == AskStatus.done && e.result != null) {
      await _speaker.stop();
      if (_justTell) await _speaker.say(e.result!.shortAnswer, lang: lang);
      if (!mounted) return;
      // Private answers stay on the screen; the council plays by itself only out loud or with earphones
      final speak = !_justTell && (e.request.outLoud || settings.earphones);
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => VerdictScreen(result: e.result!, autoplayCouncil: speak),
        ),
      );
    } else if (e.status == AskStatus.queued) {
      await _speaker.say(CaseProvider.queuedMessage, lang: lang);
    }
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _speaker.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cases = context.watch<CaseProvider>();
    final lang = context.read<SettingsProvider>().language;
    final e = _entry ?? cases.current;
    if (cases.opener.isNotEmpty && cases.opener != _spokenOpener && !_justTell) {
      _spokenOpener = cases.opener;
      if (_entry?.request.outLoud == true || context.read<SettingsProvider>().earphones) {
        _speaker.say(cases.opener, lang: lang);
      }
    }
    final failed = e != null && e.status == AskStatus.failed;
    final queued = e != null && e.status == AskStatus.queued;
    return Scaffold(
      appBar: AppBar(title: const Text('Checking')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Row(
            children: [
              const AgentAvatar('alfii', size: 56),
              const SizedBox(width: 14),
              Expanded(
                child: Text(
                  cases.opener.isNotEmpty ? cases.opener : 'Let me look at this.',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          if (failed)
            ErrorCard(
              e.error ?? 'Something went wrong.',
              onRetry: () {
                setState(() {});
                context.read<CaseProvider>().retry(e).then((_) => _afterRetry());
              },
            )
          else if (queued)
            const ErrorCard(CaseProvider.queuedMessage, icon: LucideIcons.clock)
          else ...[
            Row(
              children: [
                for (final a in const ['sankz', 'dani', 'vick'])
                  Expanded(
                    child: _AgentCard(a, called: cases.called.contains(a), done: cases.doneAgents.contains(a)),
                  ),
              ],
            ),
            const SizedBox(height: 20),
            for (final s in cases.steps.where((s) => stepWords.containsKey(s.name)))
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Row(
                  children: [
                    SizedBox(
                      width: 28,
                      child: s.state == 'running'
                          ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 3))
                          : Icon(
                              s.state == 'ok' ? LucideIcons.circleCheck : LucideIcons.info,
                              color: s.state == 'ok' ? K.alfii : VerdictStyle.yellow.solid,
                            ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(child: Text(stepWords[s.name]!, style: const TextStyle(fontSize: 18))),
                  ],
                ),
              ),
            if (cases.steps.isEmpty)
              const Padding(
                padding: EdgeInsets.all(20),
                child: Center(child: CircularProgressIndicator()),
              ),
            const SizedBox(height: 24),
            KButton(
              _justTell ? 'I will just tell you the answer' : 'Alfii, just tell me',
              kind: 'outline',
              icon: LucideIcons.fastForward,
              onPressed: _justTell
                  ? null
                  : () {
                      setState(() => _justTell = true);
                      _speaker.stop();
                    },
            ),
          ],
        ],
      ),
    );
  }

  void _afterRetry() {
    final e = _entry;
    if (!mounted || e == null) return;
    if (e.status == AskStatus.done && e.result != null) {
      Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => VerdictScreen(result: e.result!)));
    } else {
      setState(() {});
    }
  }
}

class _AgentCard extends StatelessWidget {
  final String agent;
  final bool called, done;
  const _AgentCard(this.agent, {required this.called, required this.done});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(horizontal: 4),
    child: KCard(
      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 6),
      child: SizedBox(
        width: double.infinity,
        child: Column(
          children: [
            AgentAvatar(agent, dimmed: !called),
            const SizedBox(height: 6),
            Text(
              K.agentName(agent),
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 17, color: called ? K.ink : K.muted),
            ),
            Text(
              called ? (done ? 'Done' : 'Thinking…') : 'Not needed',
              style: TextStyle(fontSize: 14, color: called ? K.agent(agent) : K.muted),
            ),
          ],
        ),
      ),
    ),
  );
}
