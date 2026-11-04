// Server responses, parsed defensively: a missing or wrong-typed field becomes a default, never a crash.

String str(Object? v, [String d = '']) => v is String ? v : (v == null ? d : '$v');
bool boolean(Object? v) => v == true;
int integer(Object? v, [int d = 0]) => v is int ? v : (v is num ? v.toInt() : int.tryParse('$v') ?? d);
double? number(Object? v) => v is num ? v.toDouble() : double.tryParse('${v ?? ''}');
Map<String, dynamic> obj(Object? v) => v is Map ? v.map((k, x) => MapEntry('$k', x)) : <String, dynamic>{};
List<Map<String, dynamic>> objs(Object? v) => v is List ? v.map(obj).toList() : <Map<String, dynamic>>[];
List<String> strs(Object? v) => v is List ? v.map((x) => str(x)).where((s) => s.isNotEmpty).toList() : <String>[];

class CouncilLine {
  final String speaker, text, kind;
  CouncilLine(this.speaker, this.text, this.kind);
  factory CouncilLine.from(Map<String, dynamic> j) =>
      CouncilLine(str(j['speaker'], 'alfii'), str(j['text']), str(j['kind'], 'agent'));
}

class ScreenDetail {
  final String id, label, value, kind, source;
  ScreenDetail(this.id, this.label, this.value, this.kind, this.source);
  factory ScreenDetail.from(Map<String, dynamic> j) =>
      ScreenDetail(str(j['id']), str(j['label']), str(j['value']), str(j['kind']), str(j['source']));
  bool get isNote => id.startsWith('note.');
  bool get personal => kind == 'personal';
}

class Claim {
  final String claim, status, evidence;
  Claim(this.claim, this.status, this.evidence);
  factory Claim.from(Map<String, dynamic> j) => Claim(str(j['claim']), str(j['status']), str(j['evidence']));
}

class CaseResult {
  final int caseId;
  final String caseType;
  final String? colour; // red | yellow | green | null (no verdict, e.g. out of scope)
  final String sentence;
  final List<String> questions;
  final List<String> calledAgents;
  final String shortAnswer;
  final List<CouncilLine> council;
  final List<ScreenDetail> details;
  final List<String> followups;
  final List<Claim> claims;
  final String privacyMode, language, provider, requestId;
  final bool degraded, localFallback;
  final List<String> degradedSteps;
  final double councilSeconds;

  CaseResult({
    required this.caseId,
    required this.caseType,
    required this.colour,
    required this.sentence,
    required this.questions,
    required this.calledAgents,
    required this.shortAnswer,
    required this.council,
    required this.details,
    required this.followups,
    required this.claims,
    required this.privacyMode,
    required this.language,
    required this.provider,
    required this.requestId,
    required this.degraded,
    required this.localFallback,
    required this.degradedSteps,
    required this.councilSeconds,
  });

  factory CaseResult.from(Map<String, dynamic> j) {
    final verdict = obj(j['verdict']);
    final colour = str(verdict['colour']);
    final council = objs(j['council']).map(CouncilLine.from).where((l) => l.text.isNotEmpty).toList();
    final spoken = objs(j['spoken_lines']).map(CouncilLine.from).where((l) => l.text.isNotEmpty).toList();
    final short = obj(j['short_answer']);
    return CaseResult(
      caseId: integer(j['case_id']),
      caseType: str(j['case_type'], 'unknown'),
      colour: const {'red', 'yellow', 'green'}.contains(colour) ? colour : null,
      sentence: str(verdict['sentence']),
      questions: strs(verdict['questions']),
      calledAgents: strs(j['called_agents']),
      shortAnswer: str(short['text'], str(verdict['sentence'])),
      council: council.isNotEmpty ? council : spoken,
      details: objs(j['screen_details']).map(ScreenDetail.from).toList(),
      followups: strs(j['suggested_followups']),
      claims: objs(j['claims']).map(Claim.from).toList(),
      privacyMode: str(j['privacy_mode'], 'discreet'),
      language: str(j['language'], 'en'),
      provider: str(j['provider'], 'local'),
      requestId: str(j['request_id']),
      degraded: boolean(j['degraded']),
      localFallback: boolean(j['local_fallback']),
      degradedSteps: strs(j['degraded_steps']),
      councilSeconds: number(j['council_seconds']) ?? 0,
    );
  }

  List<ScreenDetail> get notes => details.where((d) => d.isNote).toList();
  List<ScreenDetail> get numbers => details.where((d) => !d.isNote).toList();
}

/// One server event from /v1/cases/{id}/events.
class CaseEvent {
  final String type;
  final Map<String, dynamic> data;
  CaseEvent(this.type, this.data);
  String get step => str(data['step']);
  String get agent => str(data['agent']);
}

class HealthInfo {
  final String version, provider, model, stt;
  final bool cache, auth, traceExport;
  final Map<String, dynamic> spend;
  HealthInfo(
    this.version,
    this.provider,
    this.model,
    this.stt,
    this.cache,
    this.auth,
    this.spend, {
    this.traceExport = false,
  });
  factory HealthInfo.from(Map<String, dynamic> j) {
    final p = obj(j['provider']);
    return HealthInfo(
      str(j['version'], '?'),
      str(p['name'], '?'),
      str(p['model'], '?'),
      str(p['stt']),
      boolean(p['cache']),
      boolean(p['auth']),
      obj(p['spend_guard']),
      traceExport: boolean(obj(p['features'])['trace_export']),
    );
  }
}

class ProfileValue {
  final String field, status, source;
  final double? value;
  ProfileValue(this.field, this.status, this.value, this.source);
  factory ProfileValue.from(Map<String, dynamic> j) =>
      ProfileValue(str(j['field']), str(j['status']), number(j['value']), str(j['source']));
}

/// One person's own values, whether or not they count in the family budget.
class MemberValues {
  final int id;
  final String name, role;
  final List<MemberValue> values;
  MemberValues(this.id, this.name, this.role, this.values);
  factory MemberValues.from(Map<String, dynamic> j) => MemberValues(
    integer(j['member_id']),
    str(j['name']),
    str(j['role']),
    objs(j['values']).map(MemberValue.from).toList(),
  );
}

class MemberValue {
  final String field, source;
  final double value;
  final bool inHousehold;
  MemberValue(this.field, this.value, this.source, this.inHousehold);
  factory MemberValue.from(Map<String, dynamic> j) =>
      MemberValue(str(j['field']), number(j['value']) ?? 0, str(j['source']), boolean(j['in_household']));
}

class FamilyItem {
  final int id;
  final String kind, name, frequency, source;
  final double amount;
  final int? memberId;
  final double? units;
  FamilyItem(this.id, this.kind, this.name, this.amount, this.frequency, this.source, {this.memberId, this.units});
  factory FamilyItem.from(Map<String, dynamic> j) => FamilyItem(
    integer(j['id']),
    str(j['kind'], 'other'),
    str(j['name']),
    number(j['amount']) ?? 0,
    str(j['frequency'], 'monthly'),
    str(j['source'], 'typed'),
    memberId: j['member_id'] == null ? null : integer(j['member_id']),
    units: number(j['units']),
  );
}

/// A paper the family showed, with the category the server gave it.
class Document {
  final String filename, docType;
  final int timesSeen;
  Document(this.filename, this.docType, this.timesSeen);
  factory Document.from(Map<String, dynamic> j) =>
      Document(str(j['filename']), str(j['doc_type'], 'unknown'), integer(j['times_seen'], 1));
  String get typeLabel => switch (docType) {
    'insurance_offer' || 'ulip' => 'Insurance',
    'loan_offer' => 'Loan',
    'stock_tip' || 'shares' || 'ipo' => 'Share tip',
    'sip_or_fund_question' => 'Savings',
    'chit_fund' => 'Chit fund',
    'scam_or_payment_request' => 'Scam warning',
    _ => 'Not sure yet',
  };
}

/// A value or item the server read from what the user said / typed / showed, waiting for confirmation.
class Proposed {
  final bool isItem;
  final Map<String, dynamic> raw;
  Proposed(this.isItem, this.raw);
  String get readback => str(raw['readback']);
  String get quote => str(raw['quote']);
  bool get uncertain => boolean(raw['uncertain']);
  double get amount => number(isItem ? raw['amount'] : raw['value']) ?? 0;
  String get label => isItem ? str(raw['name']) : fieldLabel(str(raw['field']));
  bool get inHousehold => boolean(raw['in_household']);
  Proposed withAmount(double v) => Proposed(isItem, {...raw, if (isItem) 'amount': v else 'value': v});
  Proposed withHousehold(bool on) => Proposed(isItem, {...raw, 'in_household': on});
  Map<String, dynamic> confirmed() => {...raw, 'confirmed': true};
}

class Proposal {
  final List<Proposed> values;
  final String heard;
  final int? memberId;
  final bool askHousehold; // not the primary member: ask whether it counts in the family budget
  Proposal(this.values, this.heard, {this.memberId, this.askHousehold = false});
  factory Proposal.from(Map<String, dynamic> j) => Proposal(
    [...objs(j['values']).map((v) => Proposed(false, v)), ...objs(j['items']).map((v) => Proposed(true, v))],
    str(j['heard']),
    memberId: j['member_id'] == null ? null : integer(j['member_id']),
    askHousehold: boolean(j['ask_household']),
  );
}

class Alert {
  final int id, caseId;
  final String status, message, colour, sentence, caseType, note; // note = the guardian's note for Amma
  final List<Map<String, dynamic>> keyFacts, agentLines;
  Alert(
    this.id,
    this.caseId,
    this.status,
    this.message,
    this.colour,
    this.sentence,
    this.caseType,
    this.note,
    this.keyFacts,
    this.agentLines,
  );
  factory Alert.from(Map<String, dynamic> j) => Alert(
    integer(j['id']),
    integer(j['case_id']),
    str(j['status'], 'new'),
    str(j['note']),
    str(j['colour']),
    str(j['sentence']),
    str(j['case_type']),
    str(j['guardian_note']),
    objs(j['key_facts']),
    objs(j['agent_lines']),
  );
}

String fieldLabel(String field) => switch (field) {
  'monthly_income' => 'Income each month',
  'monthly_expenses' => 'Household spending each month',
  'savings' => 'Savings',
  _ => field.replaceAll('_', ' '),
};

/// ₹ with Indian grouping: 1234567 -> ₹12,34,567.
String inr(double? v) {
  if (v == null) return '—';
  final neg = v < 0;
  var s = v.abs().round().toString();
  if (s.length > 3) {
    final last3 = s.substring(s.length - 3);
    var rest = s.substring(0, s.length - 3);
    final parts = <String>[];
    while (rest.length > 2) {
      parts.insert(0, rest.substring(rest.length - 2));
      rest = rest.substring(0, rest.length - 2);
    }
    if (rest.isNotEmpty) parts.insert(0, rest);
    s = '${parts.join(',')},$last3';
  }
  return '${neg ? '-' : ''}₹$s';
}
