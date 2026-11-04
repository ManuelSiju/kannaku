import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../core/api_client.dart';
import '../core/models.dart';
import '../core/pickers.dart';
import '../core/speech.dart';
import '../state/profile.dart';
import '../state/settings.dart';
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
  bool _shown = false; // tapped "Tap to show"; figures stay blurred until then unless the person is private

  Widget _private(bool hidden, Widget child) =>
      hidden ? ImageFiltered(imageFilter: ImageFilter.blur(sigmaX: 9, sigmaY: 9), child: child) : child;

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
    final hidden = !_shown && !context.watch<SettingsProvider>().earphones;
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
            if (p.snapshot.isNotEmpty) _Snapshot(p.snapshot, hidden: hidden, onShow: () => setState(() => _shown = true)),
            const SectionTitle('Money each month'),
            _private(
              hidden,
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
            ),
            if (p.members.length > 1) ...[
              const SectionTitle('Whose details'),
              Wrap(
                spacing: 8,
                children: [
                  for (final m in p.members)
                    ChoiceChip(
                      label: Text(m.name, style: const TextStyle(fontSize: 17)),
                      selected: m.id == p.member?.id,
                      onSelected: (_) => p.chooseMember(m.id),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              if (p.member!.values.isEmpty) Text('Nothing saved for ${p.member!.name} yet.'),
              for (final v in p.member!.values)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: _private(
                    hidden,
                    KCard(
                      padding: const EdgeInsets.all(12),
                      child: Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(fieldLabel(v.field), style: const TextStyle(fontSize: 17)),
                                Text(
                                  '${inr(v.value)} · ${p.member!.name} · '
                                  '${v.inHousehold ? 'in the family budget' : 'not in the family budget'}',
                                  style: const TextStyle(fontSize: 16, color: K.muted),
                                ),
                              ],
                            ),
                          ),
                          Pill(_source(v.source), color: _dot(v.source)),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
            const SectionTitle('Policies, loans and deposits'),
            if (p.memberItems.isEmpty && !p.loading) const Text('Nothing added yet.', style: TextStyle(fontSize: 17)),
            for (final it in p.memberItems)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: _private(
                  hidden,
                  KCard(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(it.name, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
                              Text(
                                [
                                  inr(it.amount),
                                  if (it.units != null)
                                    '${it.units!.toStringAsFixed(it.units! % 1 == 0 ? 0 : 3)} '
                                        '${it.kind == 'stock_holding' ? 'shares' : 'units'}',
                                  if (it.frequency != 'once') it.frequency,
                                  if (p.members.isNotEmpty) p.ownerOf(it),
                                ].join(' · '),
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
        final text = await _ask(
          context,
          'Type it',
          'e.g. My pension is 25,000 a month. Health policy Rs 9,600 a year.',
        );
        if (text == null || text.trim().isEmpty) return;
        proposal = await p.extract(text: text);
      } else if (how == 'say') {
        final audio = await showDialog<List<int>>(context: context, builder: (_) => const _RecordDialog());
        if (audio == null) return;
        proposal = await p.extract(audio: Upload('audio', 'details.m4a', audio, 'audio/mp4'));
      } else {
        final choice = await askPaperSource(context);
        if (choice == null) return;
        final up = await Pickers.pick(choice, 'file');
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

/// The family's money at a glance, from facts. Blurred until tapped when nobody said it is private.
class _Snapshot extends StatelessWidget {
  final Map<String, dynamic> data;
  final bool hidden;
  final VoidCallback onShow;
  const _Snapshot(this.data, {required this.hidden, required this.onShow});

  String _money(String key) {
    final v = number(data[key]);
    return v == null ? 'not given' : inr(v);
  }

  Widget _row(String label, String value) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 3),
    child: Row(
      children: [
        Expanded(child: Text(label, style: const TextStyle(fontSize: 16))),
        Text(value, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
      ],
    ),
  );

  @override
  Widget build(BuildContext context) {
    final share = number(data['emi_share']);
    final card = KCard(
      padding: const EdgeInsets.all(12),
      child: Column(
        children: [
          _row('Bank savings', _money('savings')),
          if (data['holdings_total'] != null) _row('Investments', _money('holdings_total')),
          _row('Money in each month', _money('money_in')),
          _row('Money out each month', _money('money_out')),
          _row('Loan EMIs out of income', share == null ? 'not given' : '${(share * 100).toStringAsFixed(1)}%'),
        ],
      ),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SectionTitle('Family money snapshot'),
        if (!hidden)
          card
        else
          Semantics(
            button: true,
            label: 'Tap to show the family money snapshot',
            child: InkWell(
              onTap: onShow,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  ExcludeSemantics(
                    child: ImageFiltered(imageFilter: ImageFilter.blur(sigmaX: 9, sigmaY: 9), child: card),
                  ),
                  const Pill('Tap to show', color: K.alfii),
                ],
              ),
            ),
          ),
      ],
    );
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
      await context.read<ProfileProvider>().confirm([
        for (final i in _keep) _items[i],
      ], memberId: widget.proposal.memberId);
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
            child: Column(
              children: [
                CheckboxListTile(
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
                  secondary: IconButton(
                    tooltip: 'Edit',
                    icon: const Icon(LucideIcons.pencil),
                    onPressed: () => _edit(i),
                  ),
                ),
                if (widget.proposal.askHousehold)
                  SwitchListTile(
                    title: const Text('Count this in the family budget?', style: TextStyle(fontSize: 16)),
                    value: _items[i].inHousehold,
                    onChanged: (on) => setState(() => _items = [..._items]..[i] = _items[i].withHousehold(on)),
                  ),
              ],
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
