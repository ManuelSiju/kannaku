import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../state/settings.dart';
import '../theme.dart';
import '../widgets/common.dart';

/// Server address + access token (saved securely), Test connection (provider + server version), app version,
/// language, earphones, guardian view.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final _url = TextEditingController(text: context.read<SettingsProvider>().serverUrl);
  late final _token = TextEditingController(text: context.read<SettingsProvider>().token);
  bool _hide = true;
  bool _testing = false;
  String? _result;
  bool _ok = false;

  @override
  void dispose() {
    _url.dispose();
    _token.dispose();
    super.dispose();
  }

  Future<void> _test() async {
    final s = context.read<SettingsProvider>();
    setState(() {
      _testing = true;
      _result = null;
    });
    await s.setServer(_url.text, _token.text);
    try {
      final h = await s.testConnection();
      _ok = true;
      _result = 'Connected ✔  Provider: ${h.provider} (${h.model}) · server ${h.version}';
    } on ApiException catch (e) {
      _ok = false;
      _result = e.friendly;
    }
    if (mounted) setState(() => _testing = false);
  }

  @override
  Widget build(BuildContext context) {
    final s = context.watch<SettingsProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        const SectionTitle('Server'),
        TextField(
          controller: _url,
          keyboardType: TextInputType.url,
          decoration: const InputDecoration(labelText: 'Server address', hintText: 'http://192.168.1.10:8013'),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _token,
          obscureText: _hide,
          decoration: InputDecoration(
            labelText: 'Access token (from make up)',
            suffixIcon: IconButton(
                tooltip: _hide ? 'Show' : 'Hide',
                icon: Icon(_hide ? Icons.visibility : Icons.visibility_off),
                onPressed: () => setState(() => _hide = !_hide)),
          ),
        ),
        const SizedBox(height: 10),
        FilledButton.icon(
          onPressed: _testing ? null : _test,
          icon: _testing
              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.wifi_tethering),
          label: const Text('Save and test connection'),
        ),
        if (_result != null)
          Padding(
            padding: const EdgeInsets.only(top: 10),
            child: Text(_result!,
                style: TextStyle(fontSize: 17, color: _ok ? K.alfii : VerdictStyle.red.solid, fontWeight: FontWeight.w600)),
          ),
        const SectionTitle('Voice and language'),
        SegmentedButton<String>(
          segments: const [
            ButtonSegment(value: 'ml', label: Text('മലയാളം')),
            ButtonSegment(value: 'hi', label: Text('हिन्दी')),
            ButtonSegment(value: 'en', label: Text('English')),
          ],
          selected: {s.language},
          onSelectionChanged: (v) => s.set(language: v.first),
        ),
        SwitchListTile(
          value: s.earphones,
          onChanged: (v) => s.set(earphones: v),
          title: const Text('I use earphones'),
          subtitle: const Text('Private answers can then be spoken'),
        ),
        SwitchListTile(
          value: s.guardianView,
          onChanged: (v) => s.set(guardianView: v),
          title: const Text('Guardian view'),
          subtitle: const Text('Show alerts for the family instead of the chat'),
        ),
        const SectionTitle('About'),
        ListTile(title: const Text('App version'), trailing: Text(s.appVersion, style: const TextStyle(fontSize: 17))),
        ListTile(
            title: const Text('Server version'),
            trailing: Text(s.server?.version ?? 'test the connection', style: const TextStyle(fontSize: 17))),
        ListTile(
            title: const Text('Model provider'),
            trailing: Text(s.server == null ? '—' : '${s.server!.provider} · ${s.server!.model}',
                style: const TextStyle(fontSize: 17))),
        ListTile(title: const Text('Family'), trailing: Text('#${s.familyId}', style: const TextStyle(fontSize: 17))),
      ]),
    );
  }
}
