import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/models.dart';
import '../core/speech.dart';
import '../state/profile.dart';
import '../state/settings.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'home.dart';
import 'settings_screen.dart';

class WelcomeScreen extends StatelessWidget {
  const WelcomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final s = context.watch<SettingsProvider>();
    return Scaffold(
      body: SafeArea(
        child: ListView(padding: const EdgeInsets.all(24), children: [
          Align(
            alignment: Alignment.topRight,
            child: IconButton(
                tooltip: 'Settings',
                icon: const Icon(Icons.settings_outlined),
                onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsScreen()))),
          ),
          const SizedBox(height: 20),
          const Center(child: AgentAvatar('alfii', size: 110)),
          const SizedBox(height: 20),
          Text("Hello, I'm Alfii", textAlign: TextAlign.center, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          const Text('I check money offers with my friends Sankz, Dani and Vick, and tell you plainly.',
              textAlign: TextAlign.center, style: TextStyle(fontSize: 18, color: K.muted)),
          const SizedBox(height: 30),
          const Text('Choose your language', textAlign: TextAlign.center, style: TextStyle(fontSize: 18)),
          const SizedBox(height: 10),
          for (final (code, label) in const [('ml', 'മലയാളം'), ('hi', 'हिन्दी'), ('en', 'English')])
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: s.language == code
                  ? FilledButton(onPressed: () {}, child: Text(label, style: const TextStyle(fontSize: 22)))
                  : OutlinedButton(
                      onPressed: () => s.set(language: code), child: Text(label, style: const TextStyle(fontSize: 22))),
            ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: () => Navigator.of(context)
                .pushReplacement(MaterialPageRoute(builder: (_) => const OnboardingScreen())),
            child: const Text('Start'),
          ),
        ]),
      ),
    );
  }
}

/// Five skippable questions. Every number is read back ("I heard ₹45,000 a month. Is that right?") with
/// Yes / Say again / Type it; only confirmed values are saved.
class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});
  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _Q {
  final String question, field, hint;
  const _Q(this.question, this.field, this.hint);
}

const _questions = [
  _Q('What should I call you?', 'name', 'Your name'),
  _Q('How much money comes in each month?', 'monthly_income', 'e.g. 45,000 pension'),
  _Q('How much does the house spend each month (not loans)?', 'monthly_expenses', 'e.g. 28,000'),
  _Q('How much do you have saved?', 'savings', 'e.g. 1.6 lakh in the bank'),
  _Q('Any loans or policies you pay for?', 'items', 'e.g. LIC 12,000 a year, gold loan EMI 2,400'),
];

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _speaker = Speaker();
  final _text = TextEditingController();
  final _rec = Recorder();
  int _i = 0;
  bool _busy = false, _recording = false;
  Proposal? _heard;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _speak());
  }

  @override
  void dispose() {
    _speaker.stop();
    _rec.dispose();
    _text.dispose();
    super.dispose();
  }

  void _speak() => _speaker.say(_questions[_i].question, lang: context.read<SettingsProvider>().language);

  Future<void> _finish() async {
    await context.read<SettingsProvider>().set(welcomed: true);
    if (!mounted) return;
    Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const HomeScreen()));
  }

  void _next() {
    _text.clear();
    setState(() => _heard = null);
    if (_i == _questions.length - 1) {
      _finish();
    } else {
      setState(() => _i++);
      _speak();
    }
  }

  Future<void> _submit({String? text, List<int>? audio}) async {
    final q = _questions[_i];
    if (q.field == 'name') {
      await context.read<SettingsProvider>().set(userName: (text ?? '').trim());
      _next();
      return;
    }
    setState(() => _busy = true);
    try {
      final p = await context.read<ProfileProvider>().extract(
            text: text,
            field: q.field == 'items' ? null : q.field,
            audio: audio == null ? null : Upload('audio', 'answer.m4a', audio, 'audio/mp4'),
          );
      if (!mounted) return;
      if (p.values.isEmpty) {
        toast(context, 'I did not catch an amount. Say it again or type it.');
      } else {
        setState(() => _heard = p);
        final first = p.values.first.readback;
        _speaker.say('$first Is that right?', lang: context.read<SettingsProvider>().language);
      }
    } on ApiException catch (e) {
      if (mounted) toast(context, e.friendly);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _yes() async {
    setState(() => _busy = true);
    try {
      await context.read<ProfileProvider>().confirm(_heard!.values);
      _next();
    } on ApiException catch (e) {
      if (mounted) toast(context, e.friendly);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _toggleRecord() async {
    if (!_recording) {
      if (await _rec.start()) {
        setState(() => _recording = true);
      } else if (mounted) {
        toast(context, 'Please allow the microphone, or type instead.');
      }
      return;
    }
    setState(() => _recording = false);
    final audio = await _rec.stop();
    if (audio != null) await _submit(audio: audio);
  }

  @override
  Widget build(BuildContext context) {
    final q = _questions[_i];
    return Scaffold(
      appBar: AppBar(
        title: Text('${_i + 1} of ${_questions.length}'),
        actions: [TextButton(onPressed: _finish, child: const Text('Skip all', style: TextStyle(fontSize: 17)))],
      ),
      body: ListView(padding: const EdgeInsets.all(24), children: [
        LinearProgressIndicator(value: (_i + 1) / _questions.length, minHeight: 6),
        const SizedBox(height: 24),
        Row(children: [
          const AgentAvatar('alfii', size: 52),
          const SizedBox(width: 12),
          Expanded(child: Text(q.question, style: Theme.of(context).textTheme.titleMedium)),
        ]),
        const SizedBox(height: 24),
        if (_heard != null) ...[
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                for (final v in _heard!.values)
                  Text('${v.readback}${v.uncertain ? '  ⚠' : ''}', style: const TextStyle(fontSize: 19)),
                const SizedBox(height: 6),
                const Text('Is that right?', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
              ]),
            ),
          ),
          const SizedBox(height: 12),
          FilledButton(onPressed: _busy ? null : _yes, child: const Text('Yes')),
          const SizedBox(height: 8),
          OutlinedButton(
              onPressed: _busy
                  ? null
                  : () {
                      setState(() => _heard = null);
                      _toggleRecord();
                    },
              child: const Text('Say again')),
          const SizedBox(height: 8),
          OutlinedButton(onPressed: _busy ? null : () => setState(() => _heard = null), child: const Text('Type it')),
        ] else ...[
          TextField(
            controller: _text,
            style: const TextStyle(fontSize: 19),
            decoration: InputDecoration(hintText: q.hint),
            onSubmitted: (t) => _submit(text: t),
          ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: _busy ? null : () => _submit(text: _text.text),
            child: _busy ? const CircularProgressIndicator() : const Text('Next'),
          ),
          const SizedBox(height: 10),
          if (q.field != 'name')
            OutlinedButton.icon(
              onPressed: _busy ? null : _toggleRecord,
              icon: Icon(_recording ? Icons.stop : Icons.mic),
              label: Text(_recording ? 'Done talking' : 'Say it instead'),
            ),
          const SizedBox(height: 10),
          TextButton(onPressed: _next, child: const Text('Skip this question', style: TextStyle(fontSize: 17))),
        ],
      ]),
    );
  }
}
