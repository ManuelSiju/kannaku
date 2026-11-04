import 'package:flutter/foundation.dart';

import '../core/api_client.dart';
import '../core/models.dart';
import 'settings.dart';

/// The family's money each month and their policies / loans / deposits ("My details").
class ProfileProvider extends ChangeNotifier {
  final SettingsProvider settings;
  ProfileProvider(this.settings);

  List<ProfileValue> values = [];
  List<FamilyItem> items = [];
  List<Document> documents = [];
  bool loading = false;
  String? error;

  Future<void> load() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      final api = settings.api;
      final p = await api.profile(settings.familyId);
      values = objs(p['values']).map(ProfileValue.from).toList();
      items = await api.items(settings.familyId);
      documents = await api.documents(settings.familyId);
    } on ApiException catch (e) {
      error = e.friendly;
    } catch (_) {
      error = 'Could not load your details. Tap Retry.';
    }
    loading = false;
    notifyListeners();
  }

  Future<Proposal> extract({String? text, String? field, Upload? audio, Upload? file}) =>
      settings.api.extract(settings.familyId, text: text, field: field, audio: audio, file: file);

  Future<void> confirm(List<Proposed> chosen) async {
    await settings.api.confirm(settings.familyId, chosen);
    await load();
  }
}
