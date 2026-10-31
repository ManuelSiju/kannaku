import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/models.dart';
import '../state/cases.dart';
import '../state/settings.dart';
import '../theme.dart';
import '../widgets/common.dart';

/// For demos (long-press the Kanakku title): provider, router decision, facts with offer|personal tags,
/// dropped arguments, the vote maths, overrides and privacy blocks of the latest answer.
class UnderHoodScreen extends StatefulWidget {
  const UnderHoodScreen({super.key});
  @override
  State<UnderHoodScreen> createState() => _UnderHoodScreenState();
}

class _UnderHoodScreenState extends State<UnderHoodScreen> {
  Future<Map<String, dynamic>>? _bundle;
  Future<HealthInfo>? _health;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final api = context.read<SettingsProvider>().api;
    final done = context.read<CaseProvider>().chat.where((e) => e.caseId != null).toList();
    _health = api.health();
    _bundle = done.isEmpty ? null : api.caseBundle(done.last.caseId!);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Under the hood'), actions: [
        IconButton(onPressed: () => setState(_load), icon: const Icon(Icons.refresh), tooltip: 'Reload'),
      ]),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        FutureBuilder<HealthInfo>(
          future: _health,
          builder: (_, s) => Card(
            child: ListTile(
              leading: const Icon(Icons.memory),
              title: Text(s.hasData ? 'Provider: ${s.data!.provider} · ${s.data!.model}' : 'Provider: …'),
              subtitle: Text(s.hasError
                  ? (s.error is ApiException ? (s.error as ApiException).friendly : 'unreachable')
                  : s.hasData
                      ? 'Server ${s.data!.version} · cache ${s.data!.cache ? 'on' : 'off'}'
                          '${s.data!.spend.isNotEmpty ? ' · ${s.data!.spend['calls_today']}/${s.data!.spend['cap']} calls today' : ''}'
                      : ''),
            ),
          ),
        ),
        if (_bundle == null)
          const Padding(padding: EdgeInsets.all(20), child: Text('Ask a question first.'))
        else
          FutureBuilder<Map<String, dynamic>>(
            future: _bundle,
            builder: (_, s) {
              if (s.hasError) {
                return ErrorCard(s.error is ApiException ? (s.error as ApiException).friendly : 'Could not load.',
                    onRetry: () => setState(_load));
              }
              if (!s.hasData) return const Padding(padding: EdgeInsets.all(30), child: Center(child: CircularProgressIndicator()));
              return _Details(s.data!);
            },
          ),
      ]),
    );
  }
}

class _Details extends StatelessWidget {
  final Map<String, dynamic> b;
  const _Details(this.b);

  Map<String, dynamic> _step(String name) =>
      obj(objs(b['trace']).firstWhere((t) => str(t['step']) == name, orElse: () => {})['detail']);

  @override
  Widget build(BuildContext context) {
    final router = _step('router');
    final consensus = _step('consensus');
    final privacy = _step('privacy');
    final facts = objs(b['facts']);
    final args = objs(b['arguments']);
    final blocked = objs(b['spoken_lines']).where((l) => l['allowed'] == 0 || l['allowed'] == false).toList();
    final positions = objs(b['positions']);
    final mono = const TextStyle(fontFamily: 'monospace', fontSize: 14);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      const SectionTitle('Router'),
      Text('Called: ${strs(router['agents']).join(', ')}   flags: ${strs(router['flags']).join(', ')}', style: mono),
      const SectionTitle('Votes'),
      for (final p in positions)
        Text('round ${p['round']}  ${str(p['agent']).padRight(6)} ${p['stance']} ${p['strength']}', style: mono),
      Text('score ${consensus['score']}  disagreement ${consensus['disagreement']}  → ${consensus['verdict']}',
          style: mono),
      for (final o in objs(consensus['overrides']))
        Text('override ${o['rule']}: ${o['detail'] ?? ''}', style: mono.copyWith(color: const Color(0xFFB3261E))),
      const SectionTitle('Privacy'),
      Text('mode ${privacy['mode']}   earphones ${privacy['earphones']}', style: mono),
      for (final l in blocked)
        Text('blocked ${l['speaker']}: ${l['blocked_reason']}', style: mono.copyWith(color: const Color(0xFFB3261E))),
      const SectionTitle('Arguments'),
      for (final a in args)
        Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Text('${a['kept'] == 1 || a['kept'] == true ? '✔' : '✘'} ${a['agent']}: ${a['text']}'
              '${a['drop_reason'] != null ? '\n   dropped: ${a['drop_reason']}' : ''}',
              style: mono),
        ),
      const SectionTitle('Facts (from code)'),
      for (final f in facts)
        Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Pill(str(f['kind']), color: str(f['kind']) == 'personal' ? K.vick : K.sankz),
            const SizedBox(width: 8),
            Expanded(child: Text('${f['id']} = ${f['value'] ?? f['value_text'] ?? '?'} ${f['unit'] ?? ''}', style: mono)),
          ]),
        ),
      const SectionTitle('Steps'),
      for (final t in objs(b['trace'])) Text('${str(t['step']).padRight(14)} ${t['ms']} ms  ${t['outcome']}', style: mono),
    ]);
  }
}
