import 'package:flutter/material.dart';

import '../theme.dart';

/// Verdict = colour + icon + word, never colour alone.
class VerdictChip extends StatelessWidget {
  final String? colour;
  final bool large;
  const VerdictChip(this.colour, {super.key, this.large = false});

  @override
  Widget build(BuildContext context) {
    final v = VerdictStyle.of(colour);
    return Semantics(
      label: 'Verdict: ${v.word}',
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: large ? 16 : 10, vertical: large ? 8 : 4),
        decoration: BoxDecoration(color: v.solid, borderRadius: BorderRadius.circular(40)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(v.icon, color: Colors.white, size: large ? 26 : 18),
          const SizedBox(width: 6),
          Text(v.word,
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: large ? 20 : 15)),
        ]),
      ),
    );
  }
}

class AgentAvatar extends StatelessWidget {
  final String speaker;
  final double size;
  final bool dimmed;
  const AgentAvatar(this.speaker, {super.key, this.size = 44, this.dimmed = false});

  @override
  Widget build(BuildContext context) {
    final c = dimmed ? K.line : K.agent(speaker);
    return Semantics(
      label: K.agentName(speaker),
      child: CircleAvatar(
        radius: size / 2,
        backgroundColor: c,
        child: Text(K.agentName(speaker)[0],
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: size * 0.45)),
      ),
    );
  }
}

/// A friendly error with a Retry button (never a crash, never a stack trace).
class ErrorCard extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;
  final IconData icon;
  const ErrorCard(this.message, {super.key, this.onRetry, this.icon = Icons.wifi_off_rounded});

  @override
  Widget build(BuildContext context) {
    return Card(
      color: const Color(0xFFFFF7E6),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(icon, color: K.muted),
            const SizedBox(width: 10),
            Expanded(child: Text(message, style: Theme.of(context).textTheme.bodyLarge)),
          ]),
          if (onRetry != null) ...[
            const SizedBox(height: 12),
            FilledButton.icon(onPressed: onRetry, icon: const Icon(Icons.refresh), label: const Text('Retry')),
          ],
        ]),
      ),
    );
  }
}

class SectionTitle extends StatelessWidget {
  final String text;
  const SectionTitle(this.text, {super.key});
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 20, bottom: 8),
        child: Text(text, style: Theme.of(context).textTheme.titleMedium),
      );
}

/// Small pill, e.g. "Private" / "local fallback" / "personal".
class Pill extends StatelessWidget {
  final String text;
  final Color color;
  final IconData? icon;
  const Pill(this.text, {super.key, this.color = K.muted, this.icon});
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
            color: color.withValues(alpha: 0.1),
            border: Border.all(color: color.withValues(alpha: 0.5)),
            borderRadius: BorderRadius.circular(30)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          if (icon != null) ...[Icon(icon, size: 16, color: color), const SizedBox(width: 4)],
          Text(text, style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 14)),
        ]),
      );
}

void toast(BuildContext context, String message) =>
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message, style: const TextStyle(fontSize: 16))));
