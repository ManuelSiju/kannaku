import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/models.dart';
import '../core/speech.dart';
import '../state/cases.dart';
import '../state/settings.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'council.dart';
import 'why.dart';
import 'working.dart';

class VerdictScreen extends StatefulWidget {
  final CaseResult result;
  final bool autoplayCouncil;
  const VerdictScreen({super.key, required this.result, this.autoplayCouncil = false});
  @override
  State<VerdictScreen> createState() => _VerdictScreenState();
}

class _VerdictScreenState extends State<VerdictScreen> {
  final _speaker = Speaker();
  final _followUp = TextEditingController();

  /// A follow-up continues this case: the brochure and earlier answers still count.
  void _ask(String text) {
    if (text.trim().isEmpty) return;
    _followUp.clear();
    Navigator.of(context).pushReplacement(MaterialPageRoute(
        builder: (_) => WorkingScreen(request: AskRequest(text: text, caseId: widget.result.caseId))));
  }

  @override
  void initState() {
    super.initState();
    if (widget.autoplayCouncil && widget.result.council.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _openCouncil();
      });
    }
  }

  @override
  void dispose() {
    _speaker.stop();
    _followUp.dispose();
    super.dispose();
  }

  void _openCouncil() =>
      Navigator.push(context, MaterialPageRoute(builder: (_) => CouncilScreen(result: widget.result)));

  Future<void> _helpSayNo() async {
    final settings = context.read<SettingsProvider>();
    showDialog<void>(
      context: context,
      builder: (c) => FutureBuilder<String>(
        future: settings.api.letter(widget.result.caseId, sender: settings.userName),
        builder: (c, snap) => AlertDialog(
          title: const Text('Help me say no'),
          content: SingleChildScrollView(
            child: snap.hasError
                ? Text(snap.error is ApiException ? (snap.error as ApiException).friendly : 'Could not write it.')
                : snap.hasData
                    ? SelectableText(snap.data!, style: const TextStyle(fontSize: 17))
                    : const Padding(padding: EdgeInsets.all(20), child: Center(child: CircularProgressIndicator())),
          ),
          actions: [
            if (snap.hasData)
              TextButton(
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: snap.data!));
                    toast(context, 'Copied. You can paste it into a message.');
                  },
                  child: const Text('Copy')),
            TextButton(onPressed: () => Navigator.pop(c), child: const Text('Close')),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final r = widget.result;
    final v = VerdictStyle.of(r.colour);
    final lang = context.read<SettingsProvider>().language;
    return Scaffold(
      appBar: AppBar(backgroundColor: v.bg, title: const Text('Alfii\'s answer')),
      body: ListView(padding: EdgeInsets.zero, children: [
        Container(
          color: v.bg,
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              if (r.colour != null) VerdictChip(r.colour, large: true),
              const Spacer(),
              if (r.localFallback) const Pill('local fallback', icon: Icons.computer),
              if (r.degraded) ...[
                const SizedBox(width: 6),
                const Pill('partly checked', icon: Icons.info_outline),
              ],
            ]),
            const SizedBox(height: 14),
            Text(r.shortAnswer, style: Theme.of(context).textTheme.titleLarge?.copyWith(color: v.ink)),
            if (r.sentence.isNotEmpty && r.sentence != r.shortAnswer) ...[
              const SizedBox(height: 8),
              Text(r.sentence, style: TextStyle(fontSize: 18, color: v.ink)),
            ],
            const SizedBox(height: 14),
            OutlinedButton.icon(
              onPressed: () => _speaker.say(r.sentence.isNotEmpty ? r.sentence : r.shortAnswer, lang: lang),
              icon: const Icon(Icons.volume_up_outlined),
              label: const Text('Read aloud'),
            ),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.all(20),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            if (r.notes.isNotEmpty)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    const Row(children: [
                      Icon(Icons.lock_outline, color: K.muted),
                      SizedBox(width: 8),
                      Text('Only on your screen', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 17)),
                    ]),
                    const SizedBox(height: 8),
                    for (final n in r.notes)
                      Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Text('• ${n.label}', style: const TextStyle(fontSize: 18))),
                  ]),
                ),
              ),
            if (r.questions.isNotEmpty) ...[
              SectionTitle(r.caseType.contains('stock') || r.caseType == 'shares' || r.caseType == 'ipo'
                  ? 'Ask this'
                  : 'Ask him this'),
              for (final q in r.questions)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(alignment: Alignment.centerLeft, padding: const EdgeInsets.all(14)),
                    onPressed: () => _speaker.say(q, lang: lang),
                    icon: const Icon(Icons.record_voice_over_outlined),
                    label: Text(q, style: const TextStyle(fontSize: 18)),
                  ),
                ),
            ],
            if (r.claims.any((c) => c.status == 'contradicted')) ...[
              const SectionTitle('What you were told'),
              for (final c in r.claims.where((c) => c.status == 'contradicted'))
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.report_gmailerrorred, color: Color(0xFFB3261E)),
                    title: Text('"${c.claim}"', style: const TextStyle(fontSize: 17)),
                    subtitle: Text('The paper says: ${c.evidence}', style: const TextStyle(fontSize: 16)),
                  ),
                ),
            ],
            const SizedBox(height: 16),
            if (r.council.isNotEmpty)
              FilledButton.icon(
                  onPressed: _openCouncil, icon: const Icon(Icons.groups_outlined), label: const Text('Hear the council')),
            const SizedBox(height: 10),
            if (r.numbers.isNotEmpty)
              OutlinedButton.icon(
                  onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => WhyScreen(result: r))),
                  icon: const Icon(Icons.help_outline),
                  label: const Text('Why?')),
            if (r.colour == 'red') ...[
              const SizedBox(height: 10),
              OutlinedButton.icon(
                  onPressed: _helpSayNo, icon: const Icon(Icons.edit_note), label: const Text('Help me say no')),
            ],
            const SectionTitle('Ask more about this'),
            if (r.followups.isNotEmpty)
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (final f in r.followups)
                  ActionChip(label: Text(f, style: const TextStyle(fontSize: 16)), onPressed: () => _ask(f)),
              ]),
            const SizedBox(height: 10),
            Row(children: [
              Expanded(
                child: TextField(
                  key: const Key('followup_field'),
                  textInputAction: TextInputAction.send,
                  controller: _followUp,
                  style: const TextStyle(fontSize: 18),
                  decoration: const InputDecoration(hintText: 'e.g. What if I pay for 10 years?'),
                  onSubmitted: _ask,
                ),
              ),
              const SizedBox(width: 8),
              IconButton.filled(
                  key: const Key('followup_send'),
                  tooltip: 'Ask',
                  iconSize: 28,
                  onPressed: () => _ask(_followUp.text),
                  icon: const Icon(Icons.send)),
            ]),
          ]),
        ),
      ]),
    );
  }
}
