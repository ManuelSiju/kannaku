import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import 'screens/home.dart';
import 'screens/welcome.dart';
import 'state/cases.dart';
import 'state/profile.dart';
import 'state/settings.dart';
import 'theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  GoogleFonts.config.allowRuntimeFetching = true; // falls back to the system font when offline
  final settings = SettingsProvider();
  await settings.load();
  final cases = CaseProvider(settings);
  await cases.init();
  runApp(KanakkuApp(settings: settings, cases: cases));
}

class KanakkuApp extends StatelessWidget {
  final SettingsProvider settings;
  final CaseProvider cases;
  const KanakkuApp({super.key, required this.settings, required this.cases});

  @override
  Widget build(BuildContext context) => MultiProvider(
        providers: [
          ChangeNotifierProvider.value(value: settings),
          ChangeNotifierProvider.value(value: cases),
          ChangeNotifierProvider(create: (_) => ProfileProvider(settings)),
        ],
        child: MaterialApp(
          title: 'Kanakku',
          debugShowCheckedModeBanner: false,
          theme: buildTheme(),
          home: settings.welcomed ? const HomeScreen() : const WelcomeScreen(),
        ),
      );
}
