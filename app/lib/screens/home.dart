import 'dart:async';

import 'package:flutter/material.dart';
import 'package:gap/gap.dart';
import 'package:provider/provider.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../core/api_client.dart';
import '../core/pickers.dart';
import '../core/speech.dart';
import '../state/cases.dart';
import '../state/profile.dart';
import '../state/settings.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/talk_button.dart';
import 'guardian.dart';
import 'my_details.dart';
import 'settings_screen.dart';
import 'under_hood.dart';
import 'verdict.dart';
import 'working.dart';

/// The app shell: logo + privacy pill on top, four tabs below. Guardian view swaps the Chat tab for the alerts.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _tab = 0;

  void _go(int i) {
    setState(() => _tab = i);
    if (i == 2) context.read<ProfileProvider>().load();
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();
    final cases = context.watch<CaseProvider>();
    final latest = cases.chat.lastWhereOrNull((e) => e.result != null)?.result;
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            _TopBar(settings: settings),
            Expanded(
              child: IndexedStack(
                index: _tab,
                children: [
                  settings.guardianView ? const GuardianScreen(embedded: true) : ChatPage(onOpenVerdict: () => _go(1)),
                  latest == null
                      ? const _NoVerdict()
                      : VerdictScreen(key: ValueKey(latest.caseId), result: latest, embedded: true),
                  const MyDetailsScreen(embedded: true),
                  const SettingsScreen(embedded: true),
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: _TabBar(index: _tab, guardian: settings.guardianView, onTap: _go),
    );
  }
}

extension _LastOrNull<T> on List<T> {
  T? lastWhereOrNull(bool Function(T) test) {
    for (var i = length - 1; i >= 0; i--) {
      if (test(this[i])) return this[i];
    }
    return null;
  }
}

class _TopBar extends StatelessWidget {
  final SettingsProvider settings;
  const _TopBar({required this.settings});

  @override
  Widget build(BuildContext context) {
    final loud = settings.outLoud;
    final color = loud ? K.amber900 : K.alfii;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: const BoxDecoration(
        color: K.surface,
        border: Border(bottom: BorderSide(color: K.line)),
      ),
      child: Row(
        children: [
          GestureDetector(
            key: const Key('logo'),
            onLongPress: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const UnderHoodScreen())),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(color: K.alfii, borderRadius: BorderRadius.circular(10)),
                  child: const Text(
                    'क',
                    style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w700),
                  ),
                ),
                const Gap(8),
                const Text(
                  'Kanakku',
                  style: TextStyle(fontSize: 19, fontWeight: FontWeight.w700, color: K.ink),
                ),
              ],
            ),
          ),
          const Spacer(),
          Flexible(
            child: Semantics(
              button: true,
              label: loud ? 'Answers out loud. Tap for private.' : 'Private answers. Tap for out loud.',
              child: GestureDetector(
                key: const Key('privacy_pill'),
                onTap: () => settings.setOutLoud(!loud),
                child: Container(
                  constraints: const BoxConstraints(minHeight: 44),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: loud ? K.amber50 : K.emerald50,
                    border: Border.all(color: loud ? K.amber200 : K.emerald200),
                    borderRadius: BorderRadius.circular(30),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(loud ? LucideIcons.volume2 : LucideIcons.lock, size: 18, color: color),
                      const Gap(6),
                      Flexible(
                        child: Text(
                          loud ? 'Out loud' : 'Private',
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(color: color, fontSize: 16, fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TabBar extends StatelessWidget {
  final int index;
  final bool guardian;
  final ValueChanged<int> onTap;
  const _TabBar({required this.index, required this.guardian, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final tabs = [
      (guardian ? LucideIcons.bell : LucideIcons.messageSquare, guardian ? 'Alerts' : 'Chat', 'tab_chat'),
      (LucideIcons.shield, 'Verdict', 'tab_verdict'),
      (LucideIcons.wallet, 'My Details', 'tab_details'),
      (LucideIcons.settings, 'Settings', 'tab_settings'),
    ];
    return Container(
      decoration: const BoxDecoration(
        color: K.surface,
        border: Border(top: BorderSide(color: K.line)),
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            for (var i = 0; i < tabs.length; i++)
              Expanded(
                child: InkWell(
                  key: Key(tabs[i].$3),
                  onTap: () => onTap(i),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(tabs[i].$1, size: 24, color: i == index ? K.alfii : K.muted),
                        const Gap(2),
                        Text(
                          tabs[i].$2,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontSize: 14,
                            color: i == index ? K.alfii : K.muted,
                            fontWeight: i == index ? FontWeight.w700 : FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _NoVerdict extends StatelessWidget {
  const _NoVerdict();
  @override
  Widget build(BuildContext context) => const Center(
    child: Padding(
      padding: EdgeInsets.all(28),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(LucideIcons.shield, size: 44, color: K.muted),
          Gap(12),
          Text('No answer yet', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
          Gap(4),
          Text(
            'Ask a question in Chat. The full answer appears here.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 17, color: K.muted),
          ),
        ],
      ),
    ),
  );
}

class ChatPage extends StatefulWidget {
  final VoidCallback onOpenVerdict;
  const ChatPage({super.key, required this.onOpenVerdict});
  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  final _text = TextEditingController();
  final List<Upload> _pages = [];

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  Future<void> _send(AskRequest req) async {
    final cases = context.read<CaseProvider>();
    _text.clear();
    setState(() => _pages.clear());
    FocusScope.of(context).unfocus();
    if (!cases.online) {
      await cases.ask(req);
      if (!mounted) return;
      toast(context, CaseProvider.queuedMessage);
      Speaker().say(CaseProvider.queuedMessage, lang: context.read<SettingsProvider>().language);
      return;
    }
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => WorkingScreen(request: req)));
  }

  Future<void> _addPage() async {
    final choice = await askPaperSource(context);
    if (choice == null) return;
    try {
      final up = await Pickers.pick(choice, 'files');
      if (up != null) setState(() => _pages.add(up));
    } catch (_) {
      if (mounted) toast(context, 'Could not open that. Please try again.');
    }
  }

  void _sendTyped() {
    if (_text.text.trim().isEmpty && _pages.isEmpty) return;
    _send(AskRequest(text: _text.text, files: List.of(_pages), outLoud: context.read<SettingsProvider>().outLoud));
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();
    final cases = context.watch<CaseProvider>();
    return Column(
      children: [
        if (!cases.online)
          Container(
            width: double.infinity,
            color: K.amber50,
            padding: const EdgeInsets.all(10),
            child: const Text(
              'No internet. Questions wait and are checked when it is back.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 16, color: K.amber900),
            ),
          ),
        const _CouncilStrip(),
        const NotesBanner(),
        Expanded(
          child: ListView(
            reverse: true,
            padding: const EdgeInsets.fromLTRB(14, 8, 14, 12),
            children: [
              for (final e in cases.chat.reversed) ...[_Entry(e, onOpenVerdict: widget.onOpenVerdict), const Gap(14)],
              _Welcome(name: settings.userName),
            ],
          ),
        ),
        _dock(settings),
      ],
    );
  }

  Widget _dock(SettingsProvider settings) => Container(
    decoration: const BoxDecoration(
      color: K.ground,
      border: Border(top: BorderSide(color: K.line)),
    ),
    padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (_pages.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Wrap(
              spacing: 8,
              children: [
                for (final p in _pages)
                  InputChip(
                    label: Text(p.filename, overflow: TextOverflow.ellipsis),
                    onDeleted: () => setState(() => _pages.remove(p)),
                  ),
              ],
            ),
          ),
        Row(
          children: [
            Tooltip(
              message: 'Show a paper or photo',
              child: ShadIconButton.outline(
                width: 56,
                height: 56,
                onPressed: _pages.length >= 5 ? null : _addPage,
                icon: const Icon(LucideIcons.camera, size: 24),
              ),
            ),
            const Gap(8),
            Expanded(
              child: TextField(
                controller: _text,
                minLines: 1,
                maxLines: 3,
                textInputAction: TextInputAction.send,
                style: const TextStyle(fontSize: 18),
                decoration: InputDecoration(
                  hintText: 'Type your question',
                  suffixIcon: IconButton(
                    tooltip: 'Send',
                    icon: const Icon(LucideIcons.send, color: K.alfii),
                    onPressed: _sendTyped,
                  ),
                ),
                onSubmitted: (_) => _sendTyped(),
              ),
            ),
            const Gap(8),
            TalkButton(
              onSend: (audio, outLoud) => _send(
                AskRequest(
                  text: '',
                  audio: Upload('audio', 'question.m4a', audio, 'audio/mp4'),
                  files: List.of(_pages),
                  outLoud: outLoud,
                ),
              ),
            ),
          ],
        ),
        const Gap(6),
        Text(
          settings.earphones
              ? 'Earphones: private answers are spoken'
              : 'Hold and talk: slide up Private, down Out loud',
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 15, color: K.muted),
        ),
      ],
    ),
  );
}

class _CouncilStrip extends StatelessWidget {
  const _CouncilStrip();
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
    child: KCard(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          for (final a in const ['alfii', 'sankz', 'dani', 'vick'])
            Padding(padding: const EdgeInsets.only(right: 4), child: AgentAvatar(a, size: 26)),
          const Gap(6),
          const Flexible(
            child: Text(
              'Council ready',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: K.ink),
            ),
          ),
        ],
      ),
    ),
  );
}

class _Welcome extends StatelessWidget {
  final String name;
  const _Welcome({required this.name});
  @override
  Widget build(BuildContext context) => _AlfiiBubble(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Alfii',
          style: TextStyle(fontWeight: FontWeight.w700, color: K.alfii, fontSize: 16),
        ),
        const Gap(2),
        Text(
          '${name.isEmpty ? 'Hello' : 'Hello $name'}! Show me any paper or ask a question. '
          'Hold the mic button to speak to us.',
          style: const TextStyle(fontSize: 18, height: 1.35),
        ),
      ],
    ),
  );
}

class _AlfiiBubble extends StatelessWidget {
  final Widget child;
  final Color? color, border;
  const _AlfiiBubble({required this.child, this.color, this.border});
  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const AgentAvatar('alfii', size: 32),
      const Gap(8),
      Expanded(
        child: KCard(color: color, border: border, padding: const EdgeInsets.all(14), child: child),
      ),
    ],
  );
}

class _Entry extends StatelessWidget {
  final ChatEntry e;
  final VoidCallback onOpenVerdict;
  const _Entry(this.e, {required this.onOpenVerdict});

  @override
  Widget build(BuildContext context) {
    final cases = context.read<CaseProvider>();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Align(
          alignment: Alignment.centerRight,
          child: Container(
            constraints: const BoxConstraints(maxWidth: 320),
            padding: const EdgeInsets.all(14),
            decoration: const BoxDecoration(
              color: K.alfii,
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(16),
                topRight: Radius.circular(4),
                bottomLeft: Radius.circular(16),
                bottomRight: Radius.circular(16),
              ),
            ),
            child: Text(e.request.label, style: const TextStyle(fontSize: 18, color: Colors.white, height: 1.3)),
          ),
        ),
        const Gap(10),
        switch (e.status) {
          AskStatus.queued => const ErrorCard(CaseProvider.queuedMessage, icon: LucideIcons.clock),
          AskStatus.failed => ErrorCard(
            e.error ?? 'Something went wrong.',
            onRetry: () {
              Navigator.push(context, MaterialPageRoute(builder: (_) => WorkingScreen(entry: e)));
            },
          ),
          AskStatus.working => const _AlfiiBubble(
            child: Row(
              children: [
                SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 3)),
                Gap(12),
                Flexible(child: Text('Alfii is checking…', style: TextStyle(fontSize: 18))),
              ],
            ),
          ),
          AskStatus.done => _AnswerCard(e, onOpenVerdict: onOpenVerdict),
        },
        if (e.status == AskStatus.queued)
          Align(
            alignment: Alignment.centerLeft,
            child: TextButton(onPressed: () => cases.retry(e), child: const Text('Try now')),
          ),
      ],
    ).appear(context);
  }
}

class _AnswerCard extends StatelessWidget {
  final ChatEntry e;
  final VoidCallback onOpenVerdict;
  const _AnswerCard(this.e, {required this.onOpenVerdict});

  @override
  Widget build(BuildContext context) {
    final r = e.result!;
    final v = VerdictStyle.of(r.colour);
    final lang = context.read<SettingsProvider>().language;
    return _AlfiiBubble(
      color: v.bg,
      border: r.colour == null ? K.line : v.solid.withValues(alpha: 0.35),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 8,
            runSpacing: 6,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              if (r.colour != null) VerdictChip(r.colour),
              if (r.localFallback) const Pill('local fallback', icon: LucideIcons.laptop),
              if (r.provider.startsWith('replay')) Pill(r.provider, icon: LucideIcons.history),
            ],
          ),
          if (r.colour != null) const Gap(8),
          Text(
            r.shortAnswer,
            style: TextStyle(fontSize: 19, color: v.ink, fontWeight: FontWeight.w700, height: 1.3),
          ),
          const Gap(10),
          KButton(
            'Read aloud',
            kind: 'outline',
            icon: LucideIcons.volume2,
            onPressed: () => Speaker().say(r.shortAnswer, lang: lang),
          ),
          if (r.colour != null) ...[
            const Gap(6),
            KButton('View full verdict', kind: 'ghost', icon: LucideIcons.arrowRight, onPressed: onOpenVerdict),
          ],
        ],
      ),
    );
  }
}

/// "A note from Arun": what the guardian wrote for Amma (newest), loaded each time Home is shown.
class NotesBanner extends StatefulWidget {
  const NotesBanner({super.key});
  @override
  State<NotesBanner> createState() => _NotesBannerState();
}

class _NotesBannerState extends State<NotesBanner> {
  Map<String, dynamic>? _note;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
    // a note can arrive while the app is open; a failed load is retried on the next tick
    _timer = Timer.periodic(const Duration(seconds: 30), (_) => _load());
  }

  Future<void> _load() async {
    final s = context.read<SettingsProvider>();
    try {
      final n = await s.api.notes(s.familyId);
      if (mounted && n.isNotEmpty) setState(() => _note = n.first);
    } catch (_) {
      // not shown; the timer tries again
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final n = _note;
    if (n == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 0),
      child: KCard(
        color: K.emerald50,
        border: K.emerald200,
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            const Icon(LucideIcons.heart, color: K.alfii),
            const Gap(10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('A note from ${n['from']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 17)),
                  Text('${n['note']}', style: const TextStyle(fontSize: 17, color: K.ink)),
                ],
              ),
            ),
            IconButton(
              tooltip: 'Read aloud',
              icon: const Icon(LucideIcons.volume2),
              onPressed: () => Speaker().say(
                'A note from ${n['from']}. ${n['note']}',
                lang: context.read<SettingsProvider>().language,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Used by screens that show a saved value's source as a small label.
String sourceLabel(String source) => switch (source) {
  'voice' => 'Said',
  'document' => 'Paper',
  _ => 'Typed',
};
