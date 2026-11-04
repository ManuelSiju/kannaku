import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:provider/provider.dart';
import 'package:shadcn_ui/shadcn_ui.dart';
import 'package:share_plus/share_plus.dart';

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
  int? _caseId;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final api = context.read<SettingsProvider>().api;
    final done = context.read<CaseProvider>().chat.where((e) => e.caseId != null).toList();
    _health = api.health();
    _caseId = done.isEmpty ? null : done.last.caseId;
    _bundle = _caseId == null ? null : api.caseBundle(_caseId!);
  }

  Future<void> _shareTrace() async {
    final api = context.read<SettingsProvider>().api;
    try {
      final trace = await api.caseTrace(_caseId!);
      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/kanakku_case_${_caseId}_trace.json');
      await file.writeAsString(const JsonEncoder.withIndent('  ').convert(trace));
      await SharePlus.instance.share(ShareParams(files: [XFile(file.path, mimeType: 'application/json')]));
    } on ApiException catch (e) {
      if (mounted) toast(context, e.friendly);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Under the hood'),
        actions: [
          IconButton(onPressed: () => setState(_load), icon: const Icon(LucideIcons.refreshCw), tooltip: 'Reload'),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          FutureBuilder<HealthInfo>(
            future: _health,
            builder: (_, s) => Card(
              child: ListTile(
                leading: const Icon(LucideIcons.cpu),
                title: Text(
                  s.hasData
                      ? s.data!.replayOf.isNotEmpty
                            ? 'Replay of recorded Meta calls · ${s.data!.model}'
                            : '${s.data!.provider == 'meta' ? 'Meta' : s.data!.provider} · ${s.data!.model}'
                      : 'Provider: …',
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                ),
                subtitle: Text(
                  s.hasError
                      ? (s.error is ApiException ? (s.error as ApiException).friendly : 'unreachable')
                      : s.hasData
                      ? 'Server ${s.data!.version} · cache ${s.data!.cache ? 'on' : 'off'}'
                            '${s.data!.spend.isNotEmpty ? ' · ${s.data!.spend['calls_today']}/${s.data!.spend['cap']} calls today' : ''}'
                            '${s.data!.replayOf.isNotEmpty ? '\nRecorded ${s.data!.replayOf}' : ''}'
                            '${s.data!.effort.isNotEmpty ? '\nReasoning: ${s.data!.effort.entries.map((e) => '${e.key} ${e.value}').join(', ')}' : ''}'
                      : '',
                ),
              ),
            ),
          ),
          FutureBuilder<HealthInfo>(
            future: _health,
            builder: (_, s) => s.data?.traceExport == true && _caseId != null
                ? Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: OutlinedButton.icon(
                      onPressed: _shareTrace,
                      icon: const Icon(LucideIcons.share2),
                      label: const Text('Share trace'),
                    ),
                  )
                : const SizedBox.shrink(),
          ),
          if (_bundle == null)
            const Padding(padding: EdgeInsets.all(20), child: Text('Ask a question first.'))
          else
            FutureBuilder<Map<String, dynamic>>(
              future: _bundle,
              builder: (_, s) {
                if (s.hasError) {
                  return ErrorCard(
                    s.error is ApiException ? (s.error as ApiException).friendly : 'Could not load.',
                    onRetry: () => setState(_load),
                  );
                }
                if (!s.hasData) {
                  return const Padding(
                    padding: EdgeInsets.all(30),
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                return _Details(s.data!);
              },
            ),
        ],
      ),
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
    final dropped = args.where((a) => a['kept'] == 0 || a['kept'] == false).toList();
    final kept = args.length - dropped.length;
    final tools = strs(_step('compute')['facts']);
    const body = TextStyle(fontSize: 16, height: 1.35);
    const red = TextStyle(fontSize: 16, height: 1.35, color: Color(0xFFB3261E), fontWeight: FontWeight.w600);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _StepCard('Router', [
          Text('Called: ${strs(router['agents']).join(', ')}', style: body),
          if (strs(router['flags']).isNotEmpty) Text('Flags: ${strs(router['flags']).join(', ')}', style: body),
        ]),
        _StepCard('Tools', [
          Text('Code computed ${tools.length} facts. The model only cites them.', style: body),
          for (final f in facts.take(40))
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Pill(str(f['kind']), color: str(f['kind']) == 'personal' ? K.vick : K.sankz),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text('${f['id']} = ${f['value'] ?? f['value_text'] ?? '?'} ${f['unit'] ?? ''}', style: body),
                  ),
                ],
              ),
            ),
        ]),
        _StepCard('Dropped arguments', [
          Text('$kept kept, ${dropped.length} dropped.', style: body),
          if (dropped.isEmpty) const Text('Nothing was dropped in this answer.', style: body),
          for (final a in dropped) ...[
            const SizedBox(height: 6),
            Text('${K.agentName(str(a['agent']))} said: “${a['text']}”', style: body),
            Text('Dropped because: ${a['drop_reason']}', style: red),
          ],
        ]),
        _StepCard('Vote', [
          for (final p in positions)
            Text(
              '${K.agentName(str(p['agent']))}: ${p['stance']}, strength ${p['strength']} (round ${p['round']})',
              style: body,
            ),
          Text(
            'Score ${consensus['score']}, disagreement ${consensus['disagreement']}: ${consensus['verdict']}',
            style: body.copyWith(fontWeight: FontWeight.w700),
          ),
          for (final o in objs(consensus['overrides']))
            Text('Safety rule ${o['rule']}: ${o['detail'] ?? ''}', style: red),
        ]),
        _StepCard('Privacy', [
          Text('Mode: ${privacy['mode']}. Earphones: ${privacy['earphones']}.', style: body),
          if (blocked.isEmpty) const Text('No line was blocked.', style: body),
          for (final l in blocked)
            Text('Blocked ${K.agentName(str(l['speaker']))}: ${l['blocked_reason']}', style: red),
        ]),
        _StepCard('Timings', [
          for (final t in objs(b['trace']))
            if ((number(t['ms']) ?? 0) >= 1)
              Text('${str(t['step'])}: ${((number(t['ms']) ?? 0) / 1000).toStringAsFixed(1)} s', style: body),
        ]),
      ],
    );
  }
}

/// One step of the pipeline, readable at arm's length.
class _StepCard extends StatelessWidget {
  final String title;
  final List<Widget> children;
  const _StepCard(this.title, this.children);
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 12),
    child: KCard(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
          const SizedBox(height: 6),
          ...children,
        ],
      ),
    ),
  );
}
