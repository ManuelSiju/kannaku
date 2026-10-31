import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/api_client.dart';
import '../core/models.dart';
import '../state/settings.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'settings_screen.dart';

/// Guardian view (switched on in Settings): alerts for red answers and big yellow ones.
class GuardianScreen extends StatefulWidget {
  const GuardianScreen({super.key});
  @override
  State<GuardianScreen> createState() => _GuardianScreenState();
}

class _GuardianScreenState extends State<GuardianScreen> {
  late Future<List<Alert>> _alerts;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final s = context.read<SettingsProvider>();
    _alerts = s.api.alerts(s.familyId);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Guardian'), actions: [
          IconButton(
              tooltip: 'Settings',
              icon: const Icon(Icons.settings_outlined),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsScreen()))),
        ]),
        body: RefreshIndicator(
          onRefresh: () async => setState(_load),
          child: FutureBuilder<List<Alert>>(
            future: _alerts,
            builder: (_, s) {
              if (s.hasError) {
                return ListView(padding: const EdgeInsets.all(16), children: [
                  ErrorCard(s.error is ApiException ? (s.error as ApiException).friendly : 'Could not load alerts.',
                      onRetry: () => setState(_load)),
                ]);
              }
              if (!s.hasData) return const Center(child: CircularProgressIndicator());
              if (s.data!.isEmpty) {
                return ListView(padding: const EdgeInsets.all(24), children: const [
                  Text('No alerts. Amma has not met anything risky.', style: TextStyle(fontSize: 18)),
                ]);
              }
              return ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: s.data!.length,
                separatorBuilder: (_, _) => const SizedBox(height: 12),
                itemBuilder: (_, i) => _AlertCard(s.data![i], onChanged: () => setState(_load)),
              );
            },
          ),
        ),
      );
}

class _AlertCard extends StatelessWidget {
  final Alert a;
  final VoidCallback onChanged;
  const _AlertCard(this.a, {required this.onChanged});

  Future<void> _note(BuildContext context) async {
    final c = TextEditingController(text: a.note);
    final text = await showDialog<String>(
      context: context,
      builder: (d) => AlertDialog(
        title: const Text('Note for Amma'),
        content: TextField(controller: c, maxLines: 3, autofocus: true),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(d, c.text), child: const Text('Save')),
        ],
      ),
    );
    if (text == null || !context.mounted) return;
    try {
      await context.read<SettingsProvider>().api.updateAlert(a.id, note: text);
      onChanged();
    } on ApiException catch (e) {
      if (context.mounted) toast(context, e.friendly);
    }
  }

  @override
  Widget build(BuildContext context) {
    final v = VerdictStyle.of(a.colour);
    final handled = a.status == 'handled';
    return Card(
      color: handled ? K.surface : v.bg,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Wrap(spacing: 8, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
            VerdictChip(a.colour),
            Text(a.caseType.replaceAll('_', ' '), style: const TextStyle(fontSize: 16, color: K.muted)),
            if (handled) const Pill('handled', icon: Icons.check),
          ]),
          const SizedBox(height: 10),
          Text(a.sentence.isNotEmpty ? a.sentence : a.message, style: const TextStyle(fontSize: 18)),
          if (a.keyFacts.isNotEmpty) ...[
            const SizedBox(height: 10),
            for (final f in a.keyFacts)
              Text('• ${str(f['label'])}: ${_display(f)}', style: const TextStyle(fontSize: 16)),
          ],
          for (final l in a.agentLines)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text('${K.agentName(str(l['speaker']))}: ${str(l['text'])}',
                  style: TextStyle(fontSize: 16, color: K.agent(str(l['speaker'])))),
            ),
          if (a.note.isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 8), child: Text('Your note: ${a.note}')),
          const SizedBox(height: 12),
          Wrap(spacing: 8, runSpacing: 8, children: [
            FilledButton.icon(
                onPressed: () => launchUrl(Uri.parse('tel:')), icon: const Icon(Icons.call), label: const Text('Call')),
            if (!handled)
              OutlinedButton.icon(
                onPressed: () async {
                  try {
                    await context.read<SettingsProvider>().api.updateAlert(a.id, status: 'handled');
                    onChanged();
                  } on ApiException catch (e) {
                    if (context.mounted) toast(context, e.friendly);
                  }
                },
                icon: const Icon(Icons.done),
                label: const Text('Mark handled'),
              ),
            OutlinedButton.icon(
                onPressed: () => _note(context), icon: const Icon(Icons.edit_note), label: const Text('Note for Amma')),
          ]),
        ]),
      ),
    );
  }

  static String _display(Map<String, dynamic> f) {
    final v = number(f['value']);
    if (f['value_text'] != null) return str(f['value_text']);
    return switch (str(f['unit'])) {
      'fraction' => '${((v ?? 0) * 100).toStringAsFixed(1)}%',
      'INR' => inr(v),
      _ => '${v ?? '?'} ${str(f['unit'])}'.trim(),
    };
  }
}
