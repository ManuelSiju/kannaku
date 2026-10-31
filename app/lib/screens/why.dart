import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/models.dart';
import '../state/settings.dart';
import '../theme.dart';
import '../widgets/common.dart';

/// The key numbers with where each came from, and the key words from the brochure.
class WhyScreen extends StatefulWidget {
  final CaseResult result;
  const WhyScreen({super.key, required this.result});
  @override
  State<WhyScreen> createState() => _WhyScreenState();
}

class _WhyScreenState extends State<WhyScreen> {
  late Future<Map<String, dynamic>> _bundle;

  @override
  void initState() {
    super.initState();
    _bundle = context.read<SettingsProvider>().api.caseBundle(widget.result.caseId);
  }

  @override
  Widget build(BuildContext context) {
    final rows = widget.result.numbers.where((d) => d.value.isNotEmpty && d.value != 'unknown').toList();
    final fromPaper = rows.where((d) => d.id.startsWith('term.')).toList();
    final allTwice = fromPaper.isNotEmpty && fromPaper.every((d) => d.source.contains('read twice'));
    return Scaffold(
      appBar: AppBar(title: const Text('Why?')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        if (allTwice)
          const Padding(
            padding: EdgeInsets.only(bottom: 12),
            child: Pill('Every amount was read twice', color: K.alfii, icon: Icons.verified_outlined),
          ),
        for (final d in rows)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(d.label, style: const TextStyle(fontSize: 17)),
                      if (d.source.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Text(d.source, style: const TextStyle(fontSize: 15, color: K.muted)),
                        ),
                    ]),
                  ),
                  const SizedBox(width: 12),
                  Text(d.value, style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w800)),
                  if (d.personal) const Padding(padding: EdgeInsets.only(left: 6), child: Icon(Icons.lock_outline, size: 18)),
                ]),
              ),
            ),
          ),
        FutureBuilder<Map<String, dynamic>>(
          future: _bundle,
          builder: (_, snap) {
            if (snap.hasError) {
              final e = snap.error;
              return ErrorCard(e is ApiException ? e.friendly : 'Could not load the brochure words.');
            }
            final quotes = objs(snap.data?['quotes']).where((q) => str(q['source']) != 'transcript').toList();
            if (quotes.isEmpty) return const SizedBox.shrink();
            return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const SectionTitle('From the paper'),
              for (final q in quotes.take(3))
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Text('“${str(q['text']).trim()}”',
                        maxLines: 6, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 17, height: 1.4)),
                  ),
                ),
            ]);
          },
        ),
      ]),
    );
  }
}
