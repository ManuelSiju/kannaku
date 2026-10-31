import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/models.dart';
import '../core/pickers.dart';
import '../core/speech.dart';
import '../state/profile.dart';
import '../theme.dart';
import '../widgets/common.dart';

/// Money each month and the family's policies / loans / deposits, each with where it came from.
class MyDetailsScreen extends StatefulWidget {
  const MyDetailsScreen({super.key});
  @override
  State<MyDetailsScreen> createState() => _MyDetailsScreenState();
}

class _MyDetailsScreenState extends State<MyDetailsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => context.read<ProfileProvider>().load());
  }

  static Color _dot(String source) => switch (source) {
        'voice' => K.dani,
        'document' => K.sankz,
        _ => K.alfii,
      };

  @override
  Widget build(BuildContext context) {
    final p = context.watch<ProfileProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('My details')),
      body: RefreshIndicator(
        onRefresh: p.load,
        child: ListView(padding: const EdgeInsets.all(16), children: [
          if (p.error != null) ErrorCard(p.error!, onRetry: p.load),
          if (p.loading && p.values.isEmpty) const Center(child: CircularProgressIndicator()),
          const SectionTitle('Money each month'),
          for (final v in p.values)
            Card(
              child: ListTile(
                title: Text(fieldLabel(v.field), style: const TextStyle(fontSize: 17)),
                trailing: Text(v.status == 'known' ? inr(v.value) : 'not given',
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                leading: Icon(Icons.circle, size: 12, color: v.status == 'known' ? _dot(v.source) : K.line),
                subtitle: v.source.isEmpty ? null : Text('from: ${v.source}'),
              ),
            ),
          const SectionTitle('Policies, loans and deposits'),
          if (p.items.isEmpty && !p.loading) const Text('Nothing added yet.', style: TextStyle(fontSize: 17)),
          for (final it in p.items)
            Card(
              child: ListTile(
                leading: Icon(Icons.circle, size: 12, color: _dot(it.source)),
                title: Text(it.name, style: const TextStyle(fontSize: 17)),
                subtitle: Text('${it.kind} · ${it.frequency} · from: ${it.source}'),
                trailing: Text(inr(it.amount), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
              ),
            ),
          const SizedBox(height: 20),
          Row(children: [
            Expanded(child: _AddButton(Icons.mic, 'Say it', () => _add(context, 'say'))),
            const SizedBox(width: 8),
            Expanded(child: _AddButton(Icons.photo_camera_outlined, 'Show paper', () => _add(context, 'paper'))),
            const SizedBox(width: 8),
            Expanded(child: _AddButton(Icons.keyboard, 'Type it', () => _add(context, 'type'))),
          ]),
          const SizedBox(height: 10),
          const Text('Dots: green typed · purple said · blue from a paper', style: TextStyle(color: K.muted)),
        ]),
      ),
    );
  }

  Future<void> _add(BuildContext context, String how) async {
    final p = context.read<ProfileProvider>();
    Proposal? proposal;
    try {
      if (how == 'type') {
        final text = await _ask(context, 'Type it', 'e.g. My pension is 25,000 a month. LIC premium 12,000 a year.');
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
      content: TextField(controller: c, autofocus: true, maxLines: 3, decoration: InputDecoration(hintText: hint)),
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
        content: Icon(_on ? Icons.graphic_eq : Icons.mic_none, size: 64, color: K.alfii),
        actions: [
          TextButton(
              onPressed: () async {
                await _rec.cancel();
                if (context.mounted) Navigator.pop(context);
              },
              child: const Text('Cancel')),
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
        body: ListView(padding: const EdgeInsets.all(16), children: [
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
                subtitle: Text(_items[i].readback +
                    (_items[i].uncertain ? '\n⚠ Not sure I got this right. Please check.' : '')),
                secondary: IconButton(tooltip: 'Edit', icon: const Icon(Icons.edit), onPressed: () => _edit(i)),
              ),
            ),
          const SizedBox(height: 16),
          FilledButton(
              onPressed: _saving || _keep.isEmpty ? null : _save,
              child: Text(_saving ? 'Saving…' : 'Save ${_keep.length} ${_keep.length == 1 ? 'item' : 'items'}')),
        ]),
      );
}
