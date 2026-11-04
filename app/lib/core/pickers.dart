import 'package:file_picker/file_picker.dart';
import 'package:image_picker/image_picker.dart';

import 'api_client.dart';

/// Photos and PDFs the user shows. Tests replace [Pickers.pick] to return a fixture file.
class Pickers {
  /// how: camera | gallery | pdf. [field] is the multipart field name the server expects.
  static Future<Upload?> Function(String how, String field) pick = _pick;

  static Future<Upload?> _pick(String how, String field) async {
    if (how == 'pdf') {
      final picked = await FilePicker.pickFiles(type: FileType.custom, allowedExtensions: ['pdf']);
      if (picked.isEmpty) return null;
      return Upload(field, picked.first.name, await picked.first.readAsBytes(), 'application/pdf');
    }
    final x = await ImagePicker().pickImage(
      source: how == 'camera' ? ImageSource.camera : ImageSource.gallery,
      maxWidth: 2400,
      imageQuality: 85,
    );
    if (x == null) return null;
    return Upload(field, x.name, await x.readAsBytes(), 'image/jpeg');
  }
}
