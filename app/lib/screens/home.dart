import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/speech.dart';
import '../state/cases.dart';
import '../state/settings.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/talk_button.dart';
import 'council.dart';
import 'guardian.dart';
import 'my_details.dart';
import 'settings_screen.dart';
import 'under_hood.dart';
import 'verdict.dart';
import 'why.dart';
import 'working.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _text = TextEditingController();
  final _scroll = ScrollController();
  final List<Upload> _pages = [];
  bool _outLoud = false;

  @override
  void dispose() {
    _text.dispose();
    _scroll.dispose();
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
    final choice = await showModalBottomSheet<String>(
      context: context,
      builder: (c) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(
              leading: const Icon(Icons.photo_camera_outlined),
              title: const Text('Take a photo'),
              onTap: () => Navigator.pop(c, 'camera')),
          ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Choose a photo'),
              onTap: () => Navigator.pop(c, 'gallery')),
          ListTile(
              leading: const Icon(Icons.picture_as_pdf_outlined),
              title: const Text('Choose a PDF'),
              onTap: () => Navigator.pop(c, 'pdf')),
        ]),
      ),
    );
    if (choice == null) return;
    try {
      if (choice == 'pdf') {
        final picked = await FilePicker.pickFiles(type: FileType.custom, allowedExtensions: ['pdf']);
        if (picked.isNotEmpty) {
          final bytes = await picked.first.readAsBytes();
          setState(() => _pages.add(Upload('files', picked.first.name, bytes, 'application/pdf')));
        }
      } else {
        final x = await ImagePicker().pickImage(
            source: choice == 'camera' ? ImageSource.camera : ImageSource.gallery, maxWidth: 2400, imageQuality: 85);
        if (x != null) {
          final bytes = await x.readAsBytes();
          setState(() => _pages.add(Upload('files', x.name, bytes, 'image/jpeg')));
        }
      }
    } catch (_) {
      if (mounted) toast(context, 'Could not open that. Please try again.');
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();
    if (settings.guardianView) return const GuardianScreen();
    final cases = context.watch<CaseProvider>();
    return Scaffold(
      appBar: AppBar(
        title: GestureDetector(
          onLongPress: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const UnderHoodScreen())),
          child: const Text('Kanakku'),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 4),
            child: Semantics(
              button: true,
              label: _outLoud ? 'Answers out loud. Tap for private.' : 'Private answers. Tap for out loud.',
              child: ActionChip(
                avatar: Icon(_outLoud ? Icons.volume_up_outlined : Icons.lock_outline, size: 18),
                label: Text(_outLoud ? 'Out loud' : 'Private'),
                onPressed: () => setState(() => _outLoud = !_outLoud),
              ),
            ),
          ),
          IconButton(
              tooltip: 'My details',
              icon: const Icon(Icons.person_outline),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const MyDetailsScreen()))),
          IconButton(
              tooltip: 'Settings',
              icon: const Icon(Icons.settings_outlined),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsScreen()))),
        ],
      ),
      body: Column(children: [
        if (!cases.online)
          Container(
            width: double.infinity,
            color: const Color(0xFFFFF0CC),
            padding: const EdgeInsets.all(10),
            child: const Text('No internet. Questions wait and are checked when it is back.',
                textAlign: TextAlign.center, style: TextStyle(fontSize: 16)),
          ),
        Expanded(
          child: cases.chat.isEmpty
              ? _Empty(name: settings.userName)
              : ListView.separated(
                  controller: _scroll,
                  padding: const EdgeInsets.all(16),
                  itemCount: cases.chat.length,
                  separatorBuilder: (_, _) => const SizedBox(height: 14),
                  itemBuilder: (_, i) => _Entry(cases.chat[cases.chat.length - 1 - i]),
                  reverse: true,
                ),
        ),
        _dock(settings),
      ]),
    );
  }

  Widget _dock(SettingsProvider settings) => Material(
        color: K.surface,
        elevation: 8,
        child: SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              if (_pages.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Wrap(spacing: 8, children: [
                    for (final p in _pages)
                      InputChip(
                          label: Text(p.filename, overflow: TextOverflow.ellipsis),
                          onDeleted: () => setState(() => _pages.remove(p))),
                  ]),
                ),
              Row(children: [
                IconButton.filledTonal(
                  tooltip: 'Show a paper or photo',
                  iconSize: 28,
                  constraints: const BoxConstraints(minWidth: 52, minHeight: 52),
                  onPressed: _pages.length >= 5 ? null : _addPage,
                  icon: const Icon(Icons.photo_camera_outlined),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: TextField(
                    controller: _text,
                    minLines: 1,
                    maxLines: 4,
                    textInputAction: TextInputAction.send,
                    style: const TextStyle(fontSize: 18),
                    decoration: const InputDecoration(hintText: 'Type your question'),
                    onSubmitted: (_) => _sendTyped(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  tooltip: 'Send',
                  iconSize: 28,
                  constraints: const BoxConstraints(minWidth: 52, minHeight: 52),
                  onPressed: _sendTyped,
                  icon: const Icon(Icons.send),
                ),
              ]),
              const SizedBox(height: 10),
              TalkButton(
                earphones: settings.earphones,
                onSend: (audio, outLoud) => _send(AskRequest(
                    text: '', audio: Upload('audio', 'question.m4a', audio, 'audio/mp4'), files: List.of(_pages),
                    outLoud: outLoud)),
              ),
            ]),
          ),
        ),
      );

  void _sendTyped() {
    if (_text.text.trim().isEmpty && _pages.isEmpty) return;
    _send(AskRequest(text: _text.text, files: List.of(_pages), outLoud: _outLoud));
  }
}

class _Empty extends StatelessWidget {
  final String name;
  const _Empty({required this.name});
  @override
  Widget build(BuildContext context) => ListView(padding: const EdgeInsets.all(24), children: [
        const SizedBox(height: 30),
        const Center(child: AgentAvatar('alfii', size: 84)),
        const SizedBox(height: 16),
        Text(name.isEmpty ? 'Hello, I am Alfii.' : 'Hello $name, I am Alfii.',
            textAlign: TextAlign.center, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        const Text(
            'Ask me about a loan, an insurance policy, an investment or a message about shares. '
            'You can show me the paper too.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 18, color: K.muted)),
      ]);
}

class _Entry extends StatelessWidget {
  final ChatEntry e;
  const _Entry(this.e);

  @override
  Widget build(BuildContext context) {
    final cases = context.read<CaseProvider>();
    final lang = context.read<SettingsProvider>().language;
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      Align(
        alignment: Alignment.centerRight,
        child: Container(
          constraints: const BoxConstraints(maxWidth: 320),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(color: const Color(0xFFDDEDEA), borderRadius: BorderRadius.circular(18)),
          child: Text(e.request.label, style: const TextStyle(fontSize: 18)),
        ),
      ),
      const SizedBox(height: 8),
      switch (e.status) {
        AskStatus.queued => const ErrorCard(CaseProvider.queuedMessage, icon: Icons.schedule),
        AskStatus.failed => ErrorCard(e.error ?? 'Something went wrong.', onRetry: () {
            Navigator.push(context, MaterialPageRoute(builder: (_) => WorkingScreen(entry: e)));
          }),
        AskStatus.working => const Card(
            child: Padding(
                padding: EdgeInsets.all(16),
                child: Row(children: [
                  SizedBox(width: 24, height: 24, child: CircularProgressIndicator(strokeWidth: 3)),
                  SizedBox(width: 14),
                  Text('Alfii is checking…', style: TextStyle(fontSize: 18)),
                ]))),
        AskStatus.done => _AnswerCard(e, onRead: () => Speaker().say(e.result!.shortAnswer, lang: lang)),
      },
      if (e.status == AskStatus.queued)
        Align(
            alignment: Alignment.centerLeft,
            child: TextButton(onPressed: () => cases.retry(e), child: const Text('Try now'))),
    ]);
  }
}

class _AnswerCard extends StatelessWidget {
  final ChatEntry e;
  final VoidCallback onRead;
  const _AnswerCard(this.e, {required this.onRead});

  @override
  Widget build(BuildContext context) {
    final r = e.result!;
    final v = VerdictStyle.of(r.colour);
    return Card(
      color: v.bg,
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => VerdictScreen(result: r))),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              if (r.colour != null) VerdictChip(r.colour) else const AgentAvatar('alfii', size: 30),
              const Spacer(),
              if (r.localFallback) const Pill('local fallback', icon: Icons.computer),
            ]),
            const SizedBox(height: 10),
            Text(r.shortAnswer, style: TextStyle(fontSize: 19, color: v.ink, fontWeight: FontWeight.w600)),
            const SizedBox(height: 12),
            Wrap(spacing: 8, runSpacing: 8, children: [
              OutlinedButton.icon(onPressed: onRead, icon: const Icon(Icons.volume_up_outlined), label: const Text('Read aloud')),
              if (r.council.isNotEmpty)
                OutlinedButton.icon(
                    onPressed: () =>
                        Navigator.push(context, MaterialPageRoute(builder: (_) => CouncilScreen(result: r))),
                    icon: const Icon(Icons.groups_outlined),
                    label: const Text('Hear the council')),
              if (r.numbers.isNotEmpty)
                OutlinedButton.icon(
                    onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => WhyScreen(result: r))),
                    icon: const Icon(Icons.help_outline),
                    label: const Text('Why?')),
            ]),
          ]),
        ),
      ),
    );
  }
}
