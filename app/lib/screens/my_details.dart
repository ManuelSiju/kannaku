import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../core/api_client.dart';
import '../core/models.dart';
import '../core/pickers.dart';
import '../core/speech.dart';
import '../state/profile.dart';
import '../theme.dart';
import '../widgets/common.dart';

/// Money each month and the family's policies / loans / deposits, each with where it came from.
class MyDetailsScreen extends StatefulWidget {
  final bool embedded;
  const MyDetailsScreen({super.key, this.embedded = false});
  @override
  State<MyDetailsScreen> createState() => _MyDetailsScreenState();
}

class _MyDetailsScreenState extends State<MyDetailsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => context.read<ProfileProvider>().load());
  }

  static String _source(String source) => switch (source) {
    'voice' => 'Said',
    'document' => 'Paper',
    _ => 'Typed',
  };

  static Color _dot(String source) => switch (source) {
    'voice' => K.dani,
    'document' => K.sankz,
    _ => K.alfii,
  };

  @override
  Widget build(BuildContext context) {
    final p = context.watch<ProfileProvider>();
    return Scaffold(
      appBar: widget.embedded ? null : AppBar(title: const Text('My details')),
      body: RefreshIndicator(
        onRefresh: p.load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (p.error != null) ErrorCard(p.error!, onRetry: p.load),
            if (p.loading && p.values.isEmpty) const Center(child: CircularProgressIndicator()),
            const Text('Kept on your laptop', style: TextStyle(fontSize: 15, color: K.muted)),
            const SectionTitle('Money each month'),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(color: K.ink, borderRadius: BorderRadius.circular(16)),
              child: Column(
                children: [
                  for (final v in p.values)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              fieldLabel(v.field),
                              style: const TextStyle(fontSize: 17, color: Color(0xFFD4D4D8)),
                            ),
                          ),
                          Text(
                            v.status == 'known' ? inr(v.value) : 'not given',
                            style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w700, color: Colors.white),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
            const SectionTitle('Policies, loans and deposits'),
            if (p.items.isEmpty && !p.loading) const Text('Nothing added yet.', style: TextStyle(fontSize: 17)),
            for (final it in p.items)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: KCard(
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(it.name, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
                            Text(
                              '${inr(it.amount)} · ${it.frequency}',
                              style: const TextStyle(fontSize: 16, color: K.muted),
                            ),
                          ],
                        ),
                      ),
                      Pill(_source(it.source), color: _dot(it.source)),
                    ],
                  ),
                ),
              ),
            if (p.documents.isNotEmpty) ...[
              const SectionTitle('Papers you showed'),
              for (final d in p.documents)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: KCard(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        const Icon(LucideIcons.fileText, color: K.alfii),
                        const SizedBox(width: 10),
                        Expanded(child: Text(d.filename, style: const TextStyle(fontSize: 17))),
                        Pill(d.typeLabel, color: K.alfii),
                      ],
                    ),
                  ),
                ),
            ],
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(child: _AddButton(LucideIcons.mic, 'Say it', () => _add(context, 'say'))),
                const SizedBox(width: 8),
                Expanded(child: _AddButton(LucideIcons.camera, 'Show paper', () => _add(context, 'paper'))),
                const SizedBox(width: 8),
                Expanded(child: _AddButton(LucideIcons.keyboard, 'Type it', () => _add(context, 'type'))),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _add(BuildContext context, String how) async {
    final p = context.read<ProfileProvider>();
    Proposal? proposal;
    try {
      if (how == 'type') {
        final text = await _ask(context, 'Type it', 'e.g. My pension is 25,000 a month. Health policy Rs 9,600 a year.');
        if (text == null || text.trim().isEmpty) return;
        proposal = await p.extract(text: text);
      } else if (how == 'say') {
        final audio = await showDialog<List<int>>(context: context, builder: (_) => const _RecordDialog());
        if (audio == null) return;
        proposal = await p.extract(audio: Upload('audio', 'details.m4a', audio, 'audio/mp4'));
      } else {
        final up = await Pickers.pick('camera', 'file') ?? await Pickers.pick('pdf', 'file');
        if (up == null) return;
        proposal = await p.extract(file: up);
      }
    } on ApiException catch (e) {
      if (context.mounted) toast(context, e.friendly);
      return;
    }
    if (!context.mounted) return;
    if (proposal.values.isEmpty) {
      toast(context, 'I could not find an amount in that. Please try again.');
      return;
    }
    Navigator.push(context, MaterialPageRoute(builder: (_) => ConfirmScreen(proposal: proposal!)));
  }
}

Future<String?> _ask(BuildContext context, String title, String hint) {
  final c = TextEditingController();
  return showDialog<String>(
    context: context,
    builder: (d) => AlertDialog(
      title: Text(title),
      content: TextField(
        controller: c,
        autofocus: true,
        maxLines: 3,
        decoration: InputDecoration(hintText: hint),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(d), child: const Text('Cancel')),
        FilledButton(onPressed: () => Navigator.pop(d, c.text), child: const Text('OK')),
      ],
    ),
  );
}

class _AddButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  const _AddButton(this.icon, this.label, this.onTap);
  @override
  Widget build(BuildContext context) => OutlinedButton(
    onPressed: onTap,
    style: OutlinedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 14)),
    child: Column(children: [Icon(icon, size: 28), const SizedBox(height: 4), Text(label)]),
  );
}

/// Tap to start, tap to stop.
class _RecordDialog extends StatefulWidget {
  const _RecordDialog();
  @override
  State<_RecordDialog> createState() => _RecordDialogState();
}

class _RecordDialogState extends State<_RecordDialog> {
  final _rec = Recorder();
  bool _on = false;

  @override
  void dispose() {
    _rec.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(_on ? 'Listening… tap Done when finished' : 'Tap Start and say it'),
    content: Icon(_on ? LucideIcons.audioLines : LucideIcons.micOff, size: 64, color: K.alfii),
    actions: [
      TextButton(
        onPressed: () async {
          await _rec.cancel();
          if (context.mounted) Navigator.pop(context);
        },
        child: const Text('Cancel'),
      ),
      FilledButton(
        onPressed: () async {
          if (!_on) {
            final ok = await _rec.start();
            if (!ok && context.mounted) {
              toast(context, 'Please allow the microphone, or type instead.');
              Navigator.pop(context);
              return;
            }
            setState(() => _on = true);
          } else {
            final audio = await _rec.stop();
            if (context.mounted) Navigator.pop(context, audio);
          }
        },
        child: Text(_on ? 'Done' : 'Start'),
      ),
    ],
  );
}

/// Lists what was read, with edit buttons; uncertain values are flagged. Nothing is saved until Save.
class ConfirmScreen extends StatefulWidget {
  final Proposal proposal;
  final VoidCallback? onSaved;
  const ConfirmScreen({super.key, required this.proposal, this.onSaved});
  @override
  State<ConfirmScreen> createState() => _ConfirmScreenState();
}

class _ConfirmScreenState extends State<ConfirmScreen> {
  late List<Proposed> _items = List.of(widget.proposal.values);
  late final Set<int> _keep = {for (var i = 0; i < _items.length; i++) i};
  bool _saving = false;

  Future<void> _edit(int i) async {
    final text = await _ask(context, _items[i].label, 'Amount in rupees');
    final v = double.tryParse((text ?? '').replaceAll(RegExp(r'[^0-9.]'), ''));
    if (v != null) setState(() => _items = [..._items]..[i] = _items[i].withAmount(v));
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await context.read<ProfileProvider>().confirm([for (final i in _keep) _items[i]]);
      if (!mounted) return;
      toast(context, 'Saved.');
      widget.onSaved?.call();
      Navigator.pop(context);
    } on ApiException catch (e) {
      if (mounted) toast(context, e.friendly);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Is this right?')),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (widget.proposal.heard.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Text('I heard: “${widget.proposal.heard}”', style: const TextStyle(fontSize: 17, color: K.muted)),
          ),
        for (var i = 0; i < _items.length; i++)
          Card(
            child: CheckboxListTile(
              value: _keep.contains(i),
              onChanged: (on) => setState(() => on == true ? _keep.add(i) : _keep.remove(i)),
              title: Text(_items[i].label, style: const TextStyle(fontSize: 17)),
              subtitle: Text(
                [
                  if (widget.proposal.heard.isEmpty && _items[i].quote.isNotEmpty) '“${_items[i].quote}”',
                  _items[i].readback,
                  if (_items[i].uncertain) '⚠ Not sure I got this right. Please check.',
                ].join('\n'),
              ),
              secondary: IconButton(tooltip: 'Edit', icon: const Icon(LucideIcons.pencil), onPressed: () => _edit(i)),
            ),
          ),
        const SizedBox(height: 16),
        KButton(
          _saving ? 'Saving…' : 'Save ${_keep.length} ${_keep.length == 1 ? 'item' : 'items'}',
          onPressed: _saving || _keep.isEmpty ? null : _save,
        ),
      ],
    ),
  );
}
