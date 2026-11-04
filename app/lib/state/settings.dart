import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:package_info_plus/package_info_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/api_client.dart';
import '../core/models.dart';

/// Server address and access token (token in secure storage), family, language, view and voice settings.
class SettingsProvider extends ChangeNotifier {
  static const defaultUrl = String.fromEnvironment('API_URL', defaultValue: 'http://10.0.2.2:8013');
  static const defaultToken = String.fromEnvironment('API_TOKEN'); // make run-app passes the LAN token
  static const _secure = FlutterSecureStorage();

  late SharedPreferences _prefs;
  String serverUrl = defaultUrl;
  String token = '';
  String deviceId = '';
  int familyId = 1;
  String language = 'en';
  String userName = '';
  bool welcomed = false;
  bool guardianView = false;
  bool earphones = false;
  double speechSpeed = 1.0;
  String appVersion = '';
  HealthInfo? server; // from the last successful connection test
  bool outLoud = false; // the header pill; Private is the default and is not remembered between runs

  void setOutLoud(bool v) {
    outLoud = v;
    notifyListeners();
  }

  http.Client? httpClient; // tests inject a fake
  ApiClient? _api;
  ApiClient get api => _api ??= ApiClient(baseUrl: serverUrl, token: token, deviceId: deviceId, client: httpClient);

  Future<void> load() async {
    _prefs = await SharedPreferences.getInstance();
    serverUrl = _prefs.getString('server_url') ?? defaultUrl;
    familyId = _prefs.getInt('family_id') ?? 1;
    language = _prefs.getString('language') ?? 'en';
    userName = _prefs.getString('user_name') ?? '';
    welcomed = _prefs.getBool('welcomed') ?? false;
    guardianView = _prefs.getBool('guardian_view') ?? false;
    earphones = _prefs.getBool('earphones') ?? false;
    speechSpeed = _prefs.getDouble('speech_speed') ?? 1.0;
    deviceId = _prefs.getString('device_id') ?? '';
    if (deviceId.isEmpty) {
      final r = Random.secure();
      deviceId = List.generate(16, (_) => r.nextInt(16).toRadixString(16)).join();
      await _prefs.setString('device_id', deviceId);
    }
    try {
      token = await _secure.read(key: 'access_token') ?? defaultToken;
    } catch (_) {
      token = defaultToken;
    }
    try {
      final info = await PackageInfo.fromPlatform();
      appVersion = '${info.version}+${info.buildNumber}';
    } catch (_) {
      appVersion = '?';
    }
    notifyListeners();
  }

  void _rebuild() {
    _api?.close();
    _api = null;
    notifyListeners();
  }

  Future<void> setServer(String url, String newToken) async {
    serverUrl = url.trim().isEmpty ? defaultUrl : url.trim();
    token = newToken.trim();
    await _prefs.setString('server_url', serverUrl);
    try {
      await _secure.write(key: 'access_token', value: token);
    } catch (_) {}
    server = null;
    _rebuild();
  }

  /// Health (provider, server version) and a protected call to prove the token. Throws [ApiException].
  Future<HealthInfo> testConnection() async {
    final h = await api.testConnection(familyId);
    server = h;
    notifyListeners();
    return h;
  }

  Future<void> set({
    int? familyId,
    String? language,
    String? userName,
    bool? welcomed,
    bool? guardianView,
    bool? earphones,
    double? speechSpeed,
  }) async {
    if (familyId != null) await _prefs.setInt('family_id', this.familyId = familyId);
    if (language != null) await _prefs.setString('language', this.language = language);
    if (userName != null) await _prefs.setString('user_name', this.userName = userName);
    if (welcomed != null) await _prefs.setBool('welcomed', this.welcomed = welcomed);
    if (guardianView != null) await _prefs.setBool('guardian_view', this.guardianView = guardianView);
    if (earphones != null) await _prefs.setBool('earphones', this.earphones = earphones);
    if (speechSpeed != null) await _prefs.setDouble('speech_speed', this.speechSpeed = speechSpeed);
    notifyListeners();
  }
}
