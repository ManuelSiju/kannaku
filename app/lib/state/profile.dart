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
  List<MemberValues> members = []; // empty when the server has members switched off
  Map<String, dynamic> snapshot = {}; // empty when the server has it switched off
  int? memberId; // the chip chosen in My details; null = the primary member
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
      members = objs(p['member_values']).map(MemberValues.from).toList();
      snapshot = obj(p['snapshot']);
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

  MemberValues? get member {
    if (members.isEmpty) return null;
    return members.firstWhere((m) => m.id == memberId, orElse: () => members.first);
  }

  void chooseMember(int id) {
    memberId = id;
    notifyListeners();
  }

  /// Items without an owner belong to the primary member, who comes first.
  String ownerOf(FamilyItem item) {
    if (members.isEmpty) return '';
    return members.firstWhere((m) => m.id == item.memberId, orElse: () => members.first).name;
  }

  List<FamilyItem> get memberItems => members.isEmpty
      ? items
      : [
          for (final it in items)
            if (ownerOf(it) == member!.name) it,
        ];

  Future<Proposal> extract({String? text, String? field, Upload? audio, Upload? file}) => settings.api.extract(
    settings.familyId,
    text: text,
    field: field,
    memberId: field == null ? member?.id : null,
    audio: audio,
    file: file,
  );

  Future<void> confirm(List<Proposed> chosen, {int? memberId}) async {
    await settings.api.confirm(settings.familyId, chosen, memberId: memberId);
    await load();
  }
}
