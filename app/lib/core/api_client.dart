import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import 'models.dart';

/// A request the user can retry. [friendly] is what the app says and shows; [code] is the server's error code
/// (or "offline" / "timeout" / "bad_response") and [requestId] helps when reading the server log.
class ApiException implements Exception {
  final String code, friendly, requestId;
  final int status;
  ApiException(this.code, this.friendly, {this.status = 0, this.requestId = ''});
  bool get offline => code == 'offline';
  bool get unauthorized => status == 401;
  @override
  String toString() => 'ApiException($code, $status): $friendly';
}

class Upload {
  final String field, filename, mime;
  final List<int> bytes;
  Upload(this.field, this.filename, this.bytes, this.mime);
}

/// Every call has a timeout and turns any failure into an [ApiException] with a sentence a person can understand.
class ApiClient {
  final String baseUrl;
  final String token;
  final String deviceId;
  final http.Client _http;

  static const shortTimeout = Duration(seconds: 15);
  static const askTimeout = Duration(seconds: 60);
  static const uploadTimeout = Duration(seconds: 90);

  ApiClient({required String baseUrl, required this.token, required this.deviceId, http.Client? client})
    : baseUrl = baseUrl.trim().replaceAll(RegExp(r'/+$'), ''),
      _http = client ?? http.Client();

  Map<String, String> get _headers => {
    if (token.isNotEmpty) 'Authorization': 'Bearer $token',
    'X-Device-ID': deviceId,
    'Accept': 'application/json',
  };

  Uri _u(String path, [Map<String, String>? q]) => Uri.parse('$baseUrl$path').replace(queryParameters: q);

  Future<dynamic> _send(Future<http.Response> Function() call, Duration timeout) async {
    http.Response r;
    try {
      r = await call().timeout(timeout);
    } on TimeoutException {
      throw ApiException('timeout', 'The server is taking too long. Please try again.');
    } on SocketException {
      throw ApiException('offline', "I can't reach the server. Check the internet or Wi-Fi, then try again.");
    } on http.ClientException {
      throw ApiException('offline', "I can't reach the server. Check the internet or Wi-Fi, then try again.");
    } on HandshakeException {
      throw ApiException('offline', "I can't make a safe connection to the server.");
    }
    return decode(r);
  }

  /// Parses a response; non-2xx answers become an [ApiException] from the server's standard error format.
  static dynamic decode(http.Response r) {
    dynamic body;
    try {
      body = r.body.isEmpty ? null : jsonDecode(utf8.decode(r.bodyBytes));
    } catch (_) {
      body = null;
    }
    if (r.statusCode >= 200 && r.statusCode < 300) {
      if (body == null && r.body.isNotEmpty) {
        throw ApiException(
          'bad_response',
          'The server sent an answer I could not read. Please try again.',
          status: r.statusCode,
        );
      }
      return body;
    }
    final err = obj(obj(body)['error']);
    final code = str(err['code'], 'http_${r.statusCode}');
    final message = str(err['message']);
    final rid = str(err['request_id'], r.headers['x-request-id'] ?? '');
    final friendly = switch (r.statusCode) {
      404 => 'That answer is no longer on the server. Please ask again.',
      401 => 'The access token is missing or wrong. Open Settings and paste the token shown by "make up".',
      413 => message.isNotEmpty ? message : 'That file is too big.',
      415 => message.isNotEmpty ? message : 'I cannot read that kind of file.',
      429 => message.isNotEmpty ? message : 'Too many questions at once. Please wait a moment.',
      >= 500 => 'Something went wrong on the server. Please try again.',
      _ => message.isNotEmpty ? message : 'The request did not work (${r.statusCode}).',
    };
    throw ApiException(code, friendly, status: r.statusCode, requestId: rid);
  }

  Future<dynamic> get(String path, {Map<String, String>? query, Duration timeout = shortTimeout}) =>
      _send(() => _http.get(_u(path, query), headers: _headers), timeout);

  Future<dynamic> postJson(String path, Object body, {Duration timeout = shortTimeout}) => _send(
    () => _http.post(_u(path), headers: {..._headers, 'Content-Type': 'application/json'}, body: jsonEncode(body)),
    timeout,
  );

  Future<dynamic> patchJson(String path, Object body) => _send(
    () => _http.patch(_u(path), headers: {..._headers, 'Content-Type': 'application/json'}, body: jsonEncode(body)),
    shortTimeout,
  );

  Future<dynamic> postForm(
    String path,
    Map<String, String> fields, {
    List<Upload> files = const [],
    Map<String, String> headers = const {},
    Duration timeout = uploadTimeout,
  }) {
    return _send(() async {
      final req = http.MultipartRequest('POST', _u(path))
        ..headers.addAll({..._headers, ...headers})
        ..fields.addAll(fields);
      for (final f in files) {
        req.files.add(http.MultipartFile.fromBytes(f.field, f.bytes, filename: f.filename));
      }
      return http.Response.fromStream(await _http.send(req));
    }, timeout);
  }

  // ------------------------------------------------------------------ endpoints

  Future<HealthInfo> health() async => HealthInfo.from(obj(await get('/v1/health')));

  /// Health is open; this also proves the token works.
  Future<HealthInfo> testConnection(int familyId) async {
    final h = await health();
    await get('/v1/families/$familyId/profile');
    return h;
  }

  /// Starts an ask (wait=false): returns the case id at once. The same [idempotencyKey] on a resend returns the
  /// first case instead of creating a second one.
  Future<int> startAsk({
    required int familyId,
    String? text,
    Upload? audio,
    List<Upload> files = const [],
    required bool outLoud,
    required bool earphones,
    required String idempotencyKey,
    int? caseId,
  }) async {
    final body = obj(
      await postForm(
        '/v1/cases',
        {
          'family_id': '$familyId',
          if (text != null && text.trim().isNotEmpty) 'text': text.trim(),
          'wait': 'false',
          'earphones': '$earphones',
          'user_says_alone': '$outLoud',
          if (caseId != null) 'case_id': '$caseId',
        },
        files: [?audio, ...files],
        headers: {'Idempotency-Key': idempotencyKey},
        timeout: askTimeout,
      ),
    );
    if (body.containsKey('case_id') && body['status'] == null && body['verdict'] != null) {
      return integer(body['case_id']); // a replay of a finished case
    }
    final id = integer(body['case_id'], -1);
    if (id < 0) throw ApiException('bad_response', 'The server sent an answer I could not read. Please try again.');
    return id;
  }

  /// The full case bundle (result + trace + facts + arguments) for the verdict, Why and Under the hood screens.
  Future<Map<String, dynamic>> caseBundle(int caseId) async => obj(await get('/v1/cases/$caseId'));

  Future<Map<String, dynamic>> caseTrace(int caseId) async => obj(await get('/v1/cases/$caseId/trace.json'));

  /// Server-Sent Events for one case. Ends after the "done" event, or with an error the caller can ignore
  /// (the caller then polls [caseBundle]).
  Stream<CaseEvent> events(int caseId) async* {
    final req = http.Request('GET', _u('/v1/cases/$caseId/events'))..headers.addAll(_headers);
    final resp = await _http.send(req).timeout(shortTimeout);
    if (resp.statusCode != 200) throw ApiException('events', 'No live progress', status: resp.statusCode);
    var type = 'message';
    await for (final line in resp.stream.transform(utf8.decoder).transform(const LineSplitter())) {
      if (line.startsWith('event:')) {
        type = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        Map<String, dynamic> data;
        try {
          data = obj(jsonDecode(line.substring(5).trim()));
        } catch (_) {
          continue;
        }
        final t = str(data['type'], type);
        yield CaseEvent(t, data);
        if (t == 'done') return;
      } else if (line.isEmpty) {
        type = 'message';
      }
    }
  }

  Future<String> letter(int caseId, {String kind = 'cancel', String sender = ''}) async =>
      str(obj(await postJson('/v1/cases/$caseId/letter', {'kind': kind, 'sender_name': sender}))['text']);

  Future<Map<String, dynamic>> profile(int familyId) async => obj(await get('/v1/families/$familyId/profile'));

  Future<List<FamilyItem>> items(int familyId) async {
    final body = await get('/v1/families/$familyId/items');
    return objs(body is Map ? body['items'] : body).map(FamilyItem.from).toList(); // server: {"items": [...]}
  }

  Future<Proposal> extract(
    int familyId, {
    String? text,
    String? field,
    int? memberId,
    Upload? audio,
    Upload? file,
  }) async => Proposal.from(
    obj(
      await postForm(
        '/v1/families/$familyId/profile/extract',
        {'text': ?text, 'field': ?field, 'member_id': ?memberId?.toString()},
        files: [?audio, ?file],
      ),
    ),
  );

  Future<void> confirm(int familyId, List<Proposed> chosen, {int? memberId}) =>
      postJson('/v1/families/$familyId/profile/confirm', {
        'values': [for (final p in chosen.where((p) => !p.isItem)) p.confirmed()],
        'items': [for (final p in chosen.where((p) => p.isItem)) p.confirmed()],
        'member_id': ?memberId,
      });

  Future<List<Document>> documents(int familyId) async =>
      objs(obj(await get('/v1/families/$familyId/documents'))['documents']).map(Document.from).toList();

  /// The guardian's notes for Amma, newest first: [{from, note, at, case_id}].
  Future<List<Map<String, dynamic>>> notes(int familyId) async => objs(await get('/v1/families/$familyId/notes'));

  Future<List<Alert>> alerts(int familyId) async =>
      objs(await get('/v1/families/$familyId/alerts')).map(Alert.from).toList();

  Future<void> updateAlert(int id, {String? status, String? note}) =>
      patchJson('/v1/alerts/$id', {'status': ?status, 'note': ?note});

  void close() => _http.close();
}
