import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

/// Design tokens from the UI mockup: zinc neutrals, deep emerald accent. Sizes stay large for
/// older users (body 17+, touch targets 48+), larger than the mockup's.
class K {
  static const ground = Color(0xFFFAFAFA); // zinc-50
  static const surface = Color(0xFFFFFFFF);
  static const ink = Color(0xFF18181B); // zinc-900
  static const muted = Color(0xFF52525B); // zinc-600
  static const line = Color(0xFFE4E4E7); // zinc-200
  static const alfii = Color(0xFF0D654C); // deep emerald
  static const emerald50 = Color(0xFFF0FDF4);
  static const emerald200 = Color(0xFFBBF7D0);
  static const sankz = Color(0xFF1D4ED8);
  static const dani = Color(0xFFB45309);
  static const vick = Color(0xFF7E22CE);
  static const amber50 = Color(0xFFFFFBEB);
  static const amber200 = Color(0xFFFDE68A);
  static const amber900 = Color(0xFF78350F);

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
    'sankz' => 'Banks & loans',
    'dani' => 'Savings & insurance',
    'vick' => 'Shares',
    _ => 'Leader',
  };
}

/// Verdict colours: background, solid, ink; plus the icon and word that always go with the colour.
class VerdictStyle {
  final Color bg, solid, ink;
  final IconData icon;
  final String word;
  const VerdictStyle(this.bg, this.solid, this.ink, this.icon, this.word);

  static const red = VerdictStyle(
    Color(0xFFFBE4E1),
    Color(0xFFB3261E),
    Color(0xFF5C0F0A),
    LucideIcons.octagonX,
    'Stop',
  );
  static const yellow = VerdictStyle(
    Color(0xFFFFF0CC),
    Color(0xFF8A5A00),
    Color(0xFF4A3300),
    LucideIcons.triangleAlert,
    'Careful',
  );
  static const green = VerdictStyle(
    Color(0xFFDDF1E3),
    Color(0xFF1E6B3A),
    Color(0xFF0F3A1F),
    LucideIcons.circleCheck,
    'Looks fine',
  );
  static const none = VerdictStyle(K.surface, K.alfii, K.ink, LucideIcons.messageSquare, 'Answer');

  static VerdictStyle of(String? colour) => switch (colour) {
    'red' => red,
    'yellow' => yellow,
    'green' => green,
    _ => none,
  };
}

const fonts = ['Noto', 'NotoMalayalam', 'NotoDevanagari'];

/// shadcn_ui theme: zinc scheme with the emerald accent, the app's fonts, 12 px corners.
ShadThemeData buildShadTheme() => ShadThemeData(
  brightness: Brightness.light,
  colorScheme: ShadColorScheme.fromName('zinc').copyWith(
    primary: K.alfii,
    primaryForeground: Colors.white,
    ring: K.alfii,
    background: K.ground,
    foreground: K.ink,
    card: K.surface,
    cardForeground: K.ink,
    border: K.line,
    mutedForeground: K.muted,
  ),
  radius: BorderRadius.circular(14),
  textTheme: ShadTextTheme(family: 'Noto'),
);

ThemeData buildTheme() {
  final base = ThemeData(
    useMaterial3: true,
    fontFamily: 'Noto',
    fontFamilyFallback: fonts,
    colorScheme: ColorScheme.fromSeed(seedColor: K.alfii, primary: K.alfii, surface: K.surface),
    dividerColor: K.line,
    scaffoldBackgroundColor: K.ground,
  );
  // Noto for body text, with Malayalam and Devanagari fallbacks; Baloo Chettan 2 (variable font) for headings.
  final body = base.textTheme.apply(
    fontFamily: 'Noto',
    fontFamilyFallback: fonts,
    bodyColor: K.ink,
    displayColor: K.ink,
  );
  const heading = TextStyle(
    fontFamily: 'Baloo',
    fontFamilyFallback: fonts,
    fontWeight: FontWeight.w700,
    fontVariations: [FontVariation('wght', 700)],
    color: K.ink,
  );
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
      backgroundColor: K.surface,
      foregroundColor: K.ink,
      elevation: 0,
      scrolledUnderElevation: 0,
      shape: const Border(bottom: BorderSide(color: K.line)),
      titleTextStyle: heading.copyWith(fontSize: 24),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(K.touch, 56),
        textStyle: const TextStyle(
          fontFamily: 'Noto',
          fontFamilyFallback: fonts,
          fontSize: 18,
          fontWeight: FontWeight.w600,
        ),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(K.touch, 52),
        foregroundColor: K.ink,
        side: const BorderSide(color: K.line, width: 1.5),
        textStyle: const TextStyle(
          fontFamily: 'Noto',
          fontFamilyFallback: fonts,
          fontSize: K.body,
          fontWeight: FontWeight.w600,
        ),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: K.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: K.line),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: K.line),
      ),
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
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(18),
        side: const BorderSide(color: K.line),
      ),
    ),
  );
}
