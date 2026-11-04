import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../core/connect_link.dart';

/// Reads the square printed by `make start`; returns the address and token to the Settings screen.
class ScanScreen extends StatefulWidget {
  const ScanScreen({super.key});
  @override
  State<ScanScreen> createState() => _ScanScreenState();
}

class _ScanScreenState extends State<ScanScreen> {
  bool _done = false;

  void _found(BarcodeCapture capture) {
    if (_done) return;
    for (final code in capture.barcodes) {
      final link = ConnectLink.parse(code.rawValue);
      if (link != null) {
        _done = true;
        Navigator.of(context).pop(link);
        return;
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Scan the code')),
    body: Column(
      children: [
        const Padding(
          padding: EdgeInsets.all(16),
          child: Text('Point the phone at the square on the laptop screen.', style: TextStyle(fontSize: 18)),
        ),
        Expanded(child: MobileScanner(onDetect: _found)),
      ],
    ),
  );
}
