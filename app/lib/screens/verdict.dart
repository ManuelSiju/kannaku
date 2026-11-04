import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:gap/gap.dart';
import 'package:provider/provider.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

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

/// The full answer. [embedded]: inside the Verdict tab (no app bar of its own).
class VerdictScreen extends StatefulWidget {
  final CaseResult result;
  final bool autoplayCouncil, embedded;
  const VerdictScreen({super.key, required this.result, this.autoplayCouncil = false, this.embedded = false});
  @override
  State<VerdictScreen> createState() => _VerdictScreenState();
}

class _VerdictScreenState extends State<VerdictScreen> {
  final _speaker = Speaker();
  String? _speaking; // the "Ask him this" question being read out
  final _followUp = TextEditingController();

  /// A follow-up continues this case: the brochure and earlier answers still count.
  void _ask(String text) {
    if (text.trim().isEmpty) return;
    _followUp.clear();
    final route = MaterialPageRoute<void>(
      builder: (_) => WorkingScreen(
        request: AskRequest(text: text, caseId: widget.result.caseId),
      ),
    );
    widget.embedded ? Navigator.of(context).push(route) : Navigator.of(context).pushReplacement(route);
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
    showShadDialog<void>(
      context: context,
      builder: (c) => FutureBuilder<String>(
        future: settings.api.letter(widget.result.caseId, sender: settings.userName),
        builder: (c, snap) => ShadDialog(
          title: const Text('Help me say no', style: TextStyle(fontSize: 20)),
          actions: [
            if (snap.hasData)
              ShadButton.outline(
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: snap.data!));
                  toast(context, 'Copied. You can paste it into a message.');
                },
                child: const Text('Copy'),
              ),
            ShadButton(onPressed: () => Navigator.pop(c), child: const Text('Close')),
          ],
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 360),
            child: SingleChildScrollView(
              child: snap.hasError
                  ? Text(snap.error is ApiException ? (snap.error as ApiException).friendly : 'Could not write it.')
                  : snap.hasData
                  ? SelectableText(snap.data!, style: const TextStyle(fontSize: 17))
                  : const Padding(
                      padding: EdgeInsets.all(20),
                      child: Center(child: CircularProgressIndicator()),
                    ),
            ),
          ),
        ),
      ),
    );
  }

  /// The verdict arrives with a short fade and scale; none when the phone asks for reduced motion.
  Widget _arrive(Widget child) => TweenAnimationBuilder<double>(
    tween: Tween(begin: MediaQuery.of(context).disableAnimations ? 1 : 0, end: 1),
    duration: const Duration(milliseconds: 300),
    curve: Curves.easeOut,
    builder: (_, t, c) => Opacity(
      opacity: t,
      child: Transform.scale(scale: 0.96 + 0.04 * t, child: c),
    ),
    child: child,
  );

  Future<void> _sayQuestion(String q, String lang) async {
    setState(() => _speaking = q);
    await _speaker.say(q, lang: lang);
    if (mounted) setState(() => _speaking = null);
  }

  Widget _header(CaseResult r, VerdictStyle v, String lang) => KCard(
    color: v.bg,
    border: r.colour == null ? K.line : v.solid.withValues(alpha: 0.4),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 8,
          runSpacing: 6,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            if (r.colour != null) VerdictChip(r.colour, large: true),
            if (r.colour != null && !r.degraded)
              const Pill('Verified by Alfii', color: K.alfii, icon: LucideIcons.badgeCheck),
            if (r.localFallback) const Pill('local fallback', icon: LucideIcons.laptop),
            if (r.provider.startsWith('replay')) Pill(r.provider, icon: LucideIcons.history),
            if (r.degraded) const Pill('partly checked', icon: LucideIcons.info),
          ],
        ),
        const Gap(12),
        Text(
          r.shortAnswer,
          style: TextStyle(fontSize: 23, height: 1.25, color: v.ink, fontWeight: FontWeight.w800),
        ),
        if (r.sentence.isNotEmpty && r.sentence != r.shortAnswer) ...[
          const Gap(6),
          Text(r.sentence, style: TextStyle(fontSize: 18, color: v.ink, height: 1.35)),
        ],
        const Gap(12),
        KButton(
          'Read aloud',
          kind: 'outline',
          icon: LucideIcons.volume2,
          onPressed: () => _speaker.say(r.sentence.isNotEmpty ? r.sentence : r.shortAnswer, lang: lang),
        ),
      ],
    ),
  );

  Widget _opinion(CouncilLine l, String lang) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: KCard(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              AgentAvatar(l.speaker, size: 34),
              const Gap(8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(K.agentName(l.speaker), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 17)),
                    Text(K.agentRole(l.speaker), style: const TextStyle(fontSize: 15, color: K.muted)),
                  ],
                ),
              ),
              ShadButton.secondary(
                height: 44,
                leading: const Icon(LucideIcons.volume2, size: 18),
                onPressed: () => _speaker.say(l.text, speaker: l.speaker, lang: lang),
                child: const Text('Listen', style: TextStyle(fontSize: 16)),
              ),
            ],
          ),
          const Gap(8),
          Text(l.text, style: const TextStyle(fontSize: 18, height: 1.35)),
        ],
      ),
    ),
  );

  Widget _why(CaseResult r) {
    final rows = r.numbers.where((d) => d.value.isNotEmpty && d.value != 'unknown').take(8).toList();
    return KCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 2),
      child: ShadAccordion<String>(
        children: [
          ShadAccordionItem<String>(
            value: 'why',
            title: const Text(
              'Why?',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: K.alfii),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final d in rows)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(d.label, style: const TextStyle(fontSize: 16)),
                        Text(d.value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                        if (d.source.isNotEmpty) Text(d.source, style: const TextStyle(fontSize: 15, color: K.muted)),
                      ],
                    ),
                  ),
                KButton(
                  'All numbers and the paper\'s words',
                  kind: 'ghost',
                  icon: LucideIcons.fileSearch,
                  onPressed: () {
                    Navigator.push(context, MaterialPageRoute(builder: (_) => WhyScreen(result: r)));
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final r = widget.result;
    final v = VerdictStyle.of(r.colour);
    final lang = context.read<SettingsProvider>().language;
    final stock = const {'stock_tip', 'shares', 'ipo'}.contains(r.caseType);
    final opinions = r.council.where((l) => l.kind == 'agent').toList();
    return Scaffold(
      appBar: widget.embedded ? null : AppBar(title: const Text("Alfii's answer")),
      body: ListView(
        padding: const EdgeInsets.all(14),
        children: [
          _arrive(_header(r, v, lang)),
          if (r.questions.isNotEmpty) ...[
            SectionTitle(stock ? 'Ask this' : 'Ask him this'),
            for (final q in r.questions)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: KCard(
                  padding: const EdgeInsets.all(12),
                  color: _speaking == q ? K.alfii.withValues(alpha: 0.12) : null,
                  border: _speaking == q ? K.alfii : null,
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(q, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                      ),
                      IconButton(
                        tooltip: 'Say it',
                        icon: const Icon(LucideIcons.volume2, color: K.alfii),
                        onPressed: () => _sayQuestion(q, lang),
                      ),
                      IconButton(
                        tooltip: 'Copy',
                        icon: const Icon(LucideIcons.copy, color: K.alfii),
                        onPressed: () {
                          Clipboard.setData(ClipboardData(text: q));
                          toast(context, 'Question copied.');
                        },
                      ),
                    ],
                  ),
                ),
              ),
          ],
          if (r.notes.isNotEmpty) ...[
            const Gap(12),
            KCard(
              color: K.amber50,
              border: K.amber200,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(LucideIcons.lock, color: K.amber900, size: 20),
                      Gap(8),
                      Text(
                        'Only on your screen',
                        style: TextStyle(fontWeight: FontWeight.w700, fontSize: 17, color: K.amber900),
                      ),
                    ],
                  ),
                  const Gap(6),
                  for (final n in r.notes)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 3),
                      child: Text('• ${n.label}', style: const TextStyle(fontSize: 18, color: K.amber900)),
                    ),
                ],
              ),
            ),
          ],
          if (r.claims.any((c) => c.status == 'contradicted')) ...[
            const SectionTitle('What you were told'),
            for (final c in r.claims.where((c) => c.status == 'contradicted'))
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: ShadAlert.destructive(
                  icon: const Icon(LucideIcons.circleAlert),
                  title: Text('"${c.claim}"', style: const TextStyle(fontSize: 17)),
                  description: Text('The paper says: ${c.evidence}', style: const TextStyle(fontSize: 16)),
                ),
              ),
          ],
          if (opinions.isNotEmpty) ...[
            SectionTitle('Council opinions (${opinions.length})'),
            for (final l in opinions) _opinion(l, lang),
          ],
          const Gap(8),
          if (r.council.isNotEmpty) KButton('Hear the council', icon: LucideIcons.users, onPressed: _openCouncil),
          if (r.numbers.isNotEmpty) ...[const Gap(10), _why(r)],
          if (r.colour == 'red' && r.caseType != 'scam_or_payment_request') ...[
            const Gap(10),
            KButton('Help me say no', kind: 'outline', icon: LucideIcons.squarePen, onPressed: _helpSayNo),
          ],
          const SectionTitle('Ask more about this'),
          if (r.followups.isNotEmpty)
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final f in r.followups)
                  ShadButton.outline(
                    height: 44,
                    onPressed: () => _ask(f),
                    child: Flexible(child: Text(f, style: const TextStyle(fontSize: 16))),
                  ),
              ],
            ),
          const Gap(10),
          Row(
            children: [
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
              const Gap(8),
              ShadIconButton(
                key: const Key('followup_send'),
                width: 52,
                height: 52,
                onPressed: () => _ask(_followUp.text),
                icon: const Icon(LucideIcons.send, size: 22),
              ),
            ],
          ),
          const Gap(20),
        ],
      ),
    );
  }
}
