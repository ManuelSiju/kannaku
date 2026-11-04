import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import '../core/api_client.dart';
import '../core/connect_link.dart';
import '../state/settings.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'scan.dart';

/// Server address + access token (saved securely), Test connection (provider + server version), app version,
/// language, earphones, guardian view.
class SettingsScreen extends StatefulWidget {
  final bool embedded;
  const SettingsScreen({super.key, this.embedded = false});
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

  Future<void> _scan() async {
    final link = await Navigator.push<ConnectLink>(context, MaterialPageRoute(builder: (_) => const ScanScreen()));
    if (link == null || !mounted) return;
    _url.text = link.url;
    _token.text = link.token;
    await _test();
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
      appBar: widget.embedded ? null : AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const SectionTitle('Server'),
          KButton('Scan code', kind: 'outline', icon: LucideIcons.qrCode, onPressed: _scan),
          const SizedBox(height: 10),
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
                icon: Icon(_hide ? LucideIcons.eye : LucideIcons.eyeOff),
                onPressed: () => setState(() => _hide = !_hide),
              ),
            ),
          ),
          if (_result != null)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Text(
                _result!,
                key: const Key('connection_result'),
                style: TextStyle(
                  fontSize: 17,
                  color: _ok ? K.alfii : VerdictStyle.red.solid,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          const SizedBox(height: 10),
          KButton(
            _testing ? 'Testing…' : 'Save and test connection',
            icon: LucideIcons.wifi,
            onPressed: _testing ? null : _test,
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
          const SizedBox(height: 12),
          ShadSwitch(
            value: s.earphones,
            onChanged: (v) => s.set(earphones: v),
            label: const Text('I use earphones', style: TextStyle(fontSize: 17)),
            sublabel: const Text('Private answers can then be spoken', style: TextStyle(fontSize: 15)),
          ),
          const SizedBox(height: 14),
          ShadSwitch(
            key: const Key('guardian_switch'),
            value: s.guardianView,
            onChanged: (v) => s.set(guardianView: v),
            label: const Text('Guardian view', style: TextStyle(fontSize: 17)),
            sublabel: const Text('Show alerts for the family instead of the chat', style: TextStyle(fontSize: 15)),
          ),
          const SectionTitle('About'),
          ListTile(
            title: const Text('App version'),
            trailing: Text(s.appVersion, style: const TextStyle(fontSize: 17)),
          ),
          ListTile(
            title: const Text('Server version'),
            trailing: Text(s.server?.version ?? 'test the connection', style: const TextStyle(fontSize: 17)),
          ),
          ListTile(
            title: const Text('Model provider'),
            trailing: Text(
              s.server == null ? '—' : '${s.server!.provider} · ${s.server!.model}',
              style: const TextStyle(fontSize: 17),
            ),
          ),
          ListTile(
            title: const Text('Family'),
            trailing: Text('#${s.familyId}', style: const TextStyle(fontSize: 17)),
          ),
        ],
      ),
    );
  }
}
