import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:kanakku/core/api_client.dart';
import 'package:kanakku/core/models.dart';

void main() {
  test('a case result with missing and wrong-typed fields still parses', () {
    final r = CaseResult.from({
      'case_id': '7',
      'verdict': {'colour': 'purple', 'sentence': 5, 'questions': ['Ask this?', null]},
      'council': 'not a list',
      'spoken_lines': [
        {'speaker': 'vick', 'text': 'It rose 222 percent.'}
      ],
      'screen_details': [
        {'id': 'note.x', 'label': 'Only for you', 'kind': 'personal'},
        {'id': 'term.premium', 'label': 'Premium', 'value': '₹50,000', 'source': 'Brochure page 1 · read twice'}
      ],
    });
    expect(r.caseId, 7);
    expect(r.colour, isNull);
    expect(r.sentence, '5');
    expect(r.questions, ['Ask this?']);
    expect(r.council.single.speaker, 'vick');
    expect(r.notes.single.label, 'Only for you');
    expect(r.numbers.single.value, '₹50,000');
    expect(r.provider, 'local');
    expect(r.localFallback, isFalse);
  });

  test('an empty object parses to safe defaults', () {
    final r = CaseResult.from({});
    expect(r.caseType, 'unknown');
    expect(r.council, isEmpty);
    expect(r.shortAnswer, '');
  });

  test('the local fallback badge is read', () {
    final r = CaseResult.from({'provider': 'local fallback', 'local_fallback': true, 'verdict': {'colour': 'red'}});
    expect(r.localFallback, isTrue);
    expect(r.colour, 'red');
  });

  test('Indian grouping', () {
    expect(inr(1234567), '₹12,34,567');
    expect(inr(45000), '₹45,000');
    expect(inr(999), '₹999');
    expect(inr(null), '—');
  });

  group('standard error format', () {
    http.Response resp(int status, Object body) => http.Response(jsonEncode(body), status,
        headers: {'content-type': 'application/json', 'x-request-id': 'rid1'});

    test('413 keeps the server message and request id', () {
      try {
        ApiClient.decode(resp(413, {
          'error': {'code': 'file_too_large', 'message': 'p.png: 9.0 MB is over the 8 MB limit', 'request_id': 'abc'}
        }));
        fail('should throw');
      } on ApiException catch (e) {
        expect(e.code, 'file_too_large');
        expect(e.friendly, contains('8 MB'));
        expect(e.requestId, 'abc');
      }
    });

    test('401 tells the user where the token goes', () {
      expect(() => ApiClient.decode(resp(401, {'error': {'code': 'unauthorized', 'message': 'x'}})),
          throwsA(isA<ApiException>().having((e) => e.friendly, 'friendly', contains('Settings'))));
    });

    test('500 and garbage bodies never leak details', () {
      expect(() => ApiClient.decode(http.Response('Traceback (most recent call last)', 500)),
          throwsA(isA<ApiException>().having((e) => e.friendly, 'friendly', isNot(contains('Traceback')))));
      expect(() => ApiClient.decode(http.Response('<html>', 200)),
          throwsA(isA<ApiException>().having((e) => e.code, 'code', 'bad_response')));
    });
  });
}
