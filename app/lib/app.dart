import 'package:flutter/material.dart';
import 'package:shadcn_ui/shadcn_ui.dart';

import 'theme.dart';

/// shadcn_ui around MaterialApp: both themes share the same tokens.
class KanakkuFrame extends StatelessWidget {
  final Widget home;
  final TransitionBuilder? builder;
  const KanakkuFrame({super.key, required this.home, this.builder});

  @override
  Widget build(BuildContext context) => ShadApp.custom(
    themeMode: ThemeMode.light,
    theme: buildShadTheme(),
    appBuilder: (context) => MaterialApp(
      title: 'Kanakku',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      home: home,
      builder: (context, child) {
        final inner = ShadAppBuilder(child: child!);
        return builder == null ? inner : builder!(context, inner);
      },
    ),
  );
}
