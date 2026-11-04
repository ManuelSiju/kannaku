import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

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
        padding: EdgeInsets.symmetric(horizontal: large ? 14 : 10, vertical: large ? 7 : 4),
        decoration: BoxDecoration(color: v.solid, borderRadius: BorderRadius.circular(10)),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(v.icon, color: Colors.white, size: large ? 24 : 18),
            const SizedBox(width: 6),
            Text(
              v.word,
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: large ? 19 : 15),
            ),
          ],
        ),
      ),
    );
  }
}

/// A helper's square badge; Alfii carries the alpha seal.
class AgentAvatar extends StatelessWidget {
  final String speaker;
  final double size;
  final bool dimmed;
  const AgentAvatar(this.speaker, {super.key, this.size = 44, this.dimmed = false});

  @override
  Widget build(BuildContext context) {
    final alfii = K.agentName(speaker) == 'Alfii';
    return Semantics(
      label: K.agentName(speaker),
      child: Container(
        width: size,
        height: size,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: dimmed ? K.line : K.agent(speaker),
          borderRadius: BorderRadius.circular(size * 0.26),
        ),
        child: ExcludeSemantics(
          child: Text(
            alfii ? 'α' : K.agentName(speaker)[0],
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: size * 0.5, height: 1),
          ),
        ),
      ),
    );
  }
}

/// shadcn buttons at a size older hands can use. [kind]: primary | outline | secondary | ghost | destructive.
class KButton extends StatelessWidget {
  final String label;
  final IconData? icon;
  final VoidCallback? onPressed;
  final String kind;
  final bool wide;
  const KButton(this.label, {super.key, this.icon, this.onPressed, this.kind = 'primary', this.wide = true});

  @override
  Widget build(BuildContext context) {
    final child = Text(label, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600));
    final leading = icon == null ? null : Icon(icon, size: 20);
    final width = wide ? double.infinity : null;
    const height = 52.0;
    return switch (kind) {
      'outline' => ShadButton.outline(
        onPressed: onPressed,
        leading: leading,
        width: width,
        height: height,
        child: Flexible(child: child),
      ),
      'secondary' => ShadButton.secondary(
        onPressed: onPressed,
        leading: leading,
        width: width,
        height: height,
        child: Flexible(child: child),
      ),
      'ghost' => ShadButton.ghost(
        onPressed: onPressed,
        leading: leading,
        width: width,
        height: height,
        child: Flexible(child: child),
      ),
      'destructive' => ShadButton.destructive(
        onPressed: onPressed,
        leading: leading,
        width: width,
        height: height,
        child: Flexible(child: child),
      ),
      _ => ShadButton(
        onPressed: onPressed,
        leading: leading,
        width: width,
        height: height,
        child: Flexible(child: child),
      ),
    };
  }
}

/// A plain card with the app's padding.
class KCard extends StatelessWidget {
  final Widget child;
  final Color? color;
  final Color? border;
  final EdgeInsets padding;
  const KCard({super.key, required this.child, this.color, this.border, this.padding = const EdgeInsets.all(16)});

  @override
  Widget build(BuildContext context) => ShadCard(
    padding: padding,
    backgroundColor: color ?? K.surface,
    border: ShadBorder.all(color: border ?? K.line, width: 1),
    child: child,
  );
}

/// A friendly error with a Retry button (never a crash, never a stack trace).
class ErrorCard extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;
  final IconData icon;
  const ErrorCard(this.message, {super.key, this.onRetry, this.icon = LucideIcons.wifiOff});

  @override
  Widget build(BuildContext context) => KCard(
    color: K.amber50,
    border: K.amber200,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: K.amber900),
            const SizedBox(width: 10),
            Expanded(
              child: Text(message, style: const TextStyle(fontSize: 18, color: K.amber900)),
            ),
          ],
        ),
        if (onRetry != null) ...[
          const SizedBox(height: 12),
          KButton('Retry', icon: LucideIcons.refreshCw, onPressed: onRetry),
        ],
      ],
    ),
  );
}

class SectionTitle extends StatelessWidget {
  final String text;
  const SectionTitle(this.text, {super.key});
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 20, bottom: 8),
    child: Text(
      text,
      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: K.ink),
    ),
  );
}

/// Small rounded label, e.g. "local fallback", "Typed".
class Pill extends StatelessWidget {
  final String text;
  final Color color;
  final IconData? icon;
  const Pill(this.text, {super.key, this.color = K.muted, this.icon});
  @override
  Widget build(BuildContext context) => ShadBadge.outline(
    foregroundColor: color,
    backgroundColor: color.withValues(alpha: 0.08),
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (icon != null) ...[Icon(icon, size: 15, color: color), const SizedBox(width: 4)],
        Flexible(
          child: Text(
            text,
            style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 14),
          ),
        ),
      ],
    ),
  );
}

/// Fades a new chat item in, unless the phone asks for less motion.
extension Appear on Widget {
  Widget appear(BuildContext context) => MediaQuery.of(context).disableAnimations
      ? this
      : animate().fadeIn(duration: 220.ms).slideY(begin: 0.04, end: 0, duration: 220.ms);
}

void toast(BuildContext context, String message) =>
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message, style: const TextStyle(fontSize: 16))));
