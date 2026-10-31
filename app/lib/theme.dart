import 'package:flutter/material.dart';

/// Design tokens for older users: large type, strong contrast, verdicts always colour + icon + word.
class K {
  static const ground = Color(0xFFF3F6F5);
  static const surface = Color(0xFFFFFFFF);
  static const ink = Color(0xFF12201C);
  static const muted = Color(0xFF42524D);
  static const line = Color(0xFFD5DEDA);
  static const alfii = Color(0xFF0B5D52);
  static const sankz = Color(0xFF1F4FA3);
  static const dani = Color(0xFF6B3FA0);
  static const vick = Color(0xFFA84A12);

  static const double body = 17;
  static const double touch = 48;

  static Color agent(String speaker) => switch (speaker) {
        'sankz' => sankz,
        'dani' => dani,
        'vick' => vick,
        _ => alfii,
      };

  static String agentName(String speaker) => switch (speaker) {
        'sankz' => 'Sankz',
        'dani' => 'Dani',
        'vick' => 'Vick',
        _ => 'Alfii',
      };

  static String agentRole(String speaker) => switch (speaker) {
        'sankz' => 'Banking',
        'dani' => 'Mutual funds',
        'vick' => 'Stocks',
        _ => 'Curator',
      };
}

/// Verdict colours: background, solid, ink; plus the icon and word that always go with the colour.
class VerdictStyle {
  final Color bg, solid, ink;
  final IconData icon;
  final String word;
  const VerdictStyle(this.bg, this.solid, this.ink, this.icon, this.word);

  static const red = VerdictStyle(Color(0xFFFBE4E1), Color(0xFFB3261E), Color(0xFF5C0F0A), Icons.block, 'Stop');
  static const yellow =
      VerdictStyle(Color(0xFFFFF0CC), Color(0xFF8A5A00), Color(0xFF4A3300), Icons.warning_amber_rounded, 'Careful');
  static const green =
      VerdictStyle(Color(0xFFDDF1E3), Color(0xFF1E6B3A), Color(0xFF0F3A1F), Icons.check_circle_outline, 'Looks fine');
  static const none = VerdictStyle(K.surface, K.alfii, K.ink, Icons.chat_bubble_outline, 'Answer');

  static VerdictStyle of(String? colour) => switch (colour) {
        'red' => red,
        'yellow' => yellow,
        'green' => green,
        _ => none,
      };
}

const fonts = ['Noto', 'NotoMalayalam', 'NotoDevanagari'];

ThemeData buildTheme() {
  final base = ThemeData(
    useMaterial3: true,
    fontFamily: 'Noto',
    fontFamilyFallback: fonts,
    colorScheme: ColorScheme.fromSeed(seedColor: K.alfii, primary: K.alfii, surface: K.surface),
    scaffoldBackgroundColor: K.ground,
  );
  // Noto for body text, with Malayalam and Devanagari fallbacks; Baloo Chettan 2 (variable font) for headings.
  final body = base.textTheme.apply(
      fontFamily: 'Noto', fontFamilyFallback: fonts, bodyColor: K.ink, displayColor: K.ink);
  const heading = TextStyle(
      fontFamily: 'Baloo',
      fontFamilyFallback: fonts,
      fontWeight: FontWeight.w700,
      fontVariations: [FontVariation('wght', 700)],
      color: K.ink);
  return base.copyWith(
    textTheme: body.copyWith(
      bodyLarge: body.bodyLarge?.copyWith(fontSize: 18, height: 1.35),
      bodyMedium: body.bodyMedium?.copyWith(fontSize: K.body, height: 1.35),
      bodySmall: body.bodySmall?.copyWith(fontSize: 15, color: K.muted),
      titleLarge: heading.copyWith(fontSize: 26),
      titleMedium: heading.copyWith(fontSize: 21),
      headlineSmall: heading.copyWith(fontSize: 30),
      labelLarge: body.labelLarge?.copyWith(fontSize: K.body, fontWeight: FontWeight.w600),
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: K.ground,
      foregroundColor: K.ink,
      elevation: 0,
      titleTextStyle: heading.copyWith(fontSize: 24),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(K.touch, 56),
        textStyle: const TextStyle(fontFamily: 'Noto', fontFamilyFallback: fonts, fontSize: 18, fontWeight: FontWeight.w600),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(K.touch, 52),
        foregroundColor: K.ink,
        side: const BorderSide(color: K.line, width: 1.5),
        textStyle: const TextStyle(fontFamily: 'Noto', fontFamilyFallback: fonts, fontSize: K.body, fontWeight: FontWeight.w600),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: K.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: K.line)),
      enabledBorder:
          OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: K.line)),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        minimumSize: const Size(K.touch, K.touch),
        textStyle: const TextStyle(fontFamily: 'Noto', fontFamilyFallback: fonts, fontSize: K.body),
      ),
    ),
    cardTheme: CardThemeData(
      color: K.surface,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18), side: const BorderSide(color: K.line)),
    ),
  );
}
