import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';

import '../config/app_config.dart';
import '../models/chat_models.dart';
import '../services/backend_service.dart';

class AgenticController extends ChangeNotifier {
  AgenticController() {
    _service = BackendService(baseUrl: _baseUrl, apiKey: _apiKey);
    _seedState();
    checkBackendHealth();
  }

  final Uuid _uuid = const Uuid();
  final Random _random = Random();

  late BackendService _service;

  String _baseUrl = AppConfig.defaultBaseUrl();
  String _apiKey = AppConfig.defaultApiKey;
  String _sessionId = '';
  String _platform = 'sms';
  String _senderHeader = '';
  String _senderNumber = '';
  bool _inContacts = false;

  bool backendOnline = false;
  bool isSending = false;
  bool honeypotEnabled = true;
  bool lastScamDetected = false;
  String lastAgentNotes = '';
  Map<String, dynamic> lastExtractedIntel = <String, dynamic>{};
  Map<String, dynamic> lastRequestPayload = <String, dynamic>{};
  Map<String, dynamic> lastResponsePayload = <String, dynamic>{};

  int riskScore = 12;
  int testsRun = 0;
  int scamsDetected = 0;
  int averageLatencyMs = 0;
  int scammerTimeWastedMinutes = 0;

  final List<ChatMessage> transcript = <ChatMessage>[];
  final List<ThoughtLog> thoughtLogs = <ThoughtLog>[];
  final List<TimelineEvent> timelineEvents = <TimelineEvent>[];
  List<AssetStatus> assets = <AssetStatus>[];

  String get baseUrl => _baseUrl;
  String get apiKey => _apiKey;
  String get sessionId => _sessionId;
  String get platform => _platform;
  String get senderHeader => _senderHeader;
  String get senderNumber => _senderNumber;
  bool get inContacts => _inContacts;

  double get detectionRate {
    if (testsRun == 0) {
      return 0;
    }
    return (scamsDetected / testsRun) * 100;
  }

  void setEnvironment({required String baseUrl, required String apiKey}) {
    _baseUrl = baseUrl.trim();
    _apiKey = apiKey.trim();
    _service = BackendService(baseUrl: _baseUrl, apiKey: _apiKey);
    checkBackendHealth();
    notifyListeners();
  }

  void setSignalContext({
    required String platform,
    required String senderHeader,
    required String senderNumber,
    required bool inContacts,
  }) {
    _platform = platform.trim().toLowerCase();
    _senderHeader = senderHeader.trim().toUpperCase();
    _senderNumber = senderNumber.trim();
    _inContacts = inContacts;
    notifyListeners();
  }

  Future<void> checkBackendHealth() async {
    backendOnline = await _service.checkHealth();
    _appendThought(
      type: 'ACTION',
      message: backendOnline
          ? 'Backend health check OK at $_baseUrl.'
          : 'Backend health check failed at $_baseUrl.',
    );
    notifyListeners();
  }

  void toggleHoneypot(bool enabled) {
    honeypotEnabled = enabled;
    _appendThought(
      type: 'ACTION',
      message: enabled
          ? 'Honeypot interception mode armed.'
          : 'Honeypot interception mode paused.',
    );
    notifyListeners();
  }

  Future<void> runQuickScenario(String text) async {
    await sendJudgeMessage(text);
  }

  Future<void> sendJudgeMessage(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty || isSending) {
      return;
    }

    if (_sessionId.isEmpty) {
      _sessionId = _uuid.v4();
      _appendTimeline('Entry', 'Session started for heist challenge.', '[ENTRY]');
    }

    final timestampMs = DateTime.now().millisecondsSinceEpoch;
    final scammerMessage = ChatMessage(
      sender: 'scammer',
      text: trimmed,
      timestamp: timestampMs,
    );

    transcript.add(scammerMessage);
    isSending = true;
    notifyListeners();

    _appendThought(
      type: 'THOUGHT',
      message: 'Judge message received. Scanning intent and urgency markers.',
    );

    final stopwatch = Stopwatch()..start();

    try {
      final call = await _service.analyze(
        sessionId: _sessionId,
        message: scammerMessage,
        history: transcript,
        platform: _platform.isEmpty ? 'sms' : _platform,
        senderHeader: _senderHeader.isEmpty ? null : _senderHeader,
        senderNumber: _senderNumber.isEmpty ? null : _senderNumber,
        inContacts: _inContacts,
      );
      final response = call.response;
      lastRequestPayload = call.requestPayload;
      lastResponsePayload = call.responsePayload;
      if (response.sessionId.isNotEmpty) {
        _sessionId = response.sessionId;
      }

      stopwatch.stop();
      _updateLatency(stopwatch.elapsedMilliseconds);

      final bittuReply = ChatMessage(
        sender: 'user',
        text: response.reply,
        timestamp: DateTime.now().millisecondsSinceEpoch,
      );
      transcript.add(bittuReply);

      testsRun += 1;
      if (response.scamDetected) {
        scamsDetected += 1;
      }
      lastScamDetected = response.scamDetected;
      lastAgentNotes = response.agentNotes;
      lastExtractedIntel = response.extractedIntelligence;

      _applyRiskModel(message: trimmed, response: response);
      _deriveTimeline(message: trimmed, response: response);
      _deriveAssets(message: trimmed, response: response);
      _deriveThoughtTrace(message: trimmed, response: response);

      if (honeypotEnabled && response.shouldEngage) {
        scammerTimeWastedMinutes += 1 + _random.nextInt(2);
        _appendThought(
          type: 'ACTION',
          message: 'Bittu sent controlled bait response to prolong attacker interaction.',
        );
      }
    } catch (error) {
      stopwatch.stop();
      _appendThought(
        type: 'VERDICT',
        message: 'Backend call failed: $error',
      );
    } finally {
      isSending = false;
      notifyListeners();
    }
  }

  Map<String, dynamic> buildFinalPayload() {
    return {
      'sessionId': _sessionId.isEmpty ? 'local-session' : _sessionId,
      'scamDetected': lastScamDetected,
      'totalMessagesExchanged': transcript.length,
      'extractedIntelligence': lastExtractedIntel,
      'agentNotes': lastAgentNotes,
    };
  }

  void resetChatSession() {
    _sessionId = '';
    transcript.clear();
    thoughtLogs.clear();
    timelineEvents.clear();
    riskScore = 12;
    scamsDetected = 0;
    testsRun = 0;
    averageLatencyMs = 0;
    scammerTimeWastedMinutes = 0;
    lastScamDetected = false;
    lastAgentNotes = '';
    lastExtractedIntel = <String, dynamic>{};
    lastRequestPayload = <String, dynamic>{};
    lastResponsePayload = <String, dynamic>{};
    _seedState();
    notifyListeners();
  }

  void _seedState() {
    assets = <AssetStatus>[
      AssetStatus(name: 'UPI Accounts', state: 'Active Protection'),
      AssetStatus(name: 'Aadhaar Data', state: 'Encrypted'),
      AssetStatus(name: 'Contacts', state: 'Monitored for Impersonation'),
      AssetStatus(name: 'Bank Wallet', state: 'Adaptive Guardrails'),
    ];

    _appendThought(
      type: 'ACTION',
      message: 'Bittu booted in Agentic Defense Arena mode.',
    );
  }

  void _deriveThoughtTrace({required String message, required AnalyzeResponse response}) {
    _appendThought(
      type: 'TOOL_CALL',
      message: 'check_bank_records(session_id="$_sessionId")',
    );

    final intent = response.scamDetected
        ? 'Potential social-engineering pattern found in incoming text.'
        : 'No hard scam indicators found in current turn.';
    _appendThought(type: 'THOUGHT', message: intent);

    if (response.agentNotes.isNotEmpty) {
      _appendThought(type: 'ACTION', message: response.agentNotes);
    }

    final verdict = response.scamDetected ? 'Potential P2P Scam detected.' : 'Message currently classified as low-risk.';
    _appendThought(type: 'VERDICT', message: verdict);

    if (message.toLowerCase().contains('otp') && honeypotEnabled) {
      final fakeOtp = 100000 + _random.nextInt(899999);
      _appendThought(
        type: 'ACTION',
        message: 'Active Defense generated decoy OTP $fakeOtp to waste attacker time.',
      );
    }
  }

  void _deriveTimeline({required String message, required AnalyzeResponse response}) {
    final lower = message.toLowerCase();
    if (lower.contains('urgent') || lower.contains('immediately')) {
      _appendTimeline('Bait', 'Urgency detected in attacker language.', '[BAIT]');
    }
    if (lower.contains('whatsapp') || lower.contains('telegram')) {
      _appendTimeline('Pivot', 'Scammer trying to move conversation channel.', '[PIVOT]');
    }
    if (lower.contains('otp') || lower.contains('pin')) {
      _appendTimeline('Intercept', 'Bittu intercepted credential request.', '[BLOCK]');
    }
    if (response.scamDetected) {
      _appendTimeline('Block', 'Risk engine escalated threat posture.', '[ALERT]');
    }
  }

  void _deriveAssets({required String message, required AnalyzeResponse response}) {
    final lower = message.toLowerCase();
    assets = assets
        .map((asset) {
          if (asset.name == 'Contacts' && (lower.contains('hi mom') || lower.contains('family'))) {
            return AssetStatus(name: asset.name, state: asset.state, alert: true);
          }
          if (asset.name == 'UPI Accounts' && response.scamDetected) {
            return AssetStatus(name: asset.name, state: 'Shield Heightened', alert: true);
          }
          if (asset.name == 'Bank Wallet' && (lower.contains('refund') || lower.contains('transfer'))) {
            return AssetStatus(name: asset.name, state: 'Transaction Trap Enabled', alert: true);
          }
          return AssetStatus(name: asset.name, state: asset.state, alert: false);
        })
        .toList(growable: false);
  }

  void _applyRiskModel({required String message, required AnalyzeResponse response}) {
    final lower = message.toLowerCase();
    var delta = 0;

    if (response.scamDetected) {
      delta += 25;
    }
    if (lower.contains('otp') || lower.contains('pin') || lower.contains('password')) {
      delta += 20;
    }
    if (lower.contains('urgent') || lower.contains('immediately')) {
      delta += 12;
    }
    if (lower.contains('link') || lower.contains('http')) {
      delta += 10;
    }

    final intel = response.extractedIntelligence;
    delta += _countList(intel['upiIds']) * 4;
    delta += _countList(intel['phoneNumbers']) * 3;
    delta += _countList(intel['phishingLinks']) * 5;

    riskScore = (riskScore + delta).clamp(0, 100);
  }

  int _countList(dynamic value) {
    if (value is List) {
      return value.length;
    }
    return 0;
  }

  void _updateLatency(int ms) {
    if (testsRun == 0) {
      averageLatencyMs = ms;
      return;
    }
    averageLatencyMs = ((averageLatencyMs * testsRun) + ms) ~/ (testsRun + 1);
  }

  void _appendThought({required String type, required String message}) {
    thoughtLogs.insert(
      0,
      ThoughtLog(type: type, message: message, timestamp: DateTime.now()),
    );
    if (thoughtLogs.length > 60) {
      thoughtLogs.removeLast();
    }
  }

  void _appendTimeline(String title, String description, String symbol) {
    timelineEvents.add(
      TimelineEvent(
        title: title,
        description: description,
        symbol: symbol,
        timestamp: DateTime.now(),
      ),
    );
    if (timelineEvents.length > 18) {
      timelineEvents.removeAt(0);
    }
  }
}
