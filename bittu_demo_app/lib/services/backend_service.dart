import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/chat_models.dart';

class BackendService {
  BackendService({required this.baseUrl, required this.apiKey, http.Client? client}) : _client = client ?? http.Client();

  final String baseUrl;
  final String apiKey;
  final http.Client _client;

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  Future<bool> checkHealth() async {
    try {
      final response = await _client.get(_uri('/health')).timeout(const Duration(seconds: 5));
      return response.statusCode >= 200 && response.statusCode < 300;
    } catch (_) {
      return false;
    }
  }

  Future<AnalyzeCallResult> analyze({
    required String sessionId,
    required ChatMessage message,
    required List<ChatMessage> history,
    String channel = 'bittu-agentic-ai',
    String platform = 'sms',
    String? senderHeader,
    String? senderNumber,
    bool? inContacts,
  }) async {
    final payload = {
      'sessionId': sessionId,
      'message': message.toJson(),
      'conversationHistory': history.map((m) => m.toJson()).toList(),
      'metadata': {
        'channel': channel,
        'language': 'English',
        'locale': 'IN',
        'platform': platform,
        'senderHeader': senderHeader,
        'senderNumber': senderNumber,
        'inContacts': inContacts,
      }
    };

    final response = await _client
        .post(
          _uri('/analyze'),
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': apiKey,
          },
          body: jsonEncode(payload),
        )
        .timeout(const Duration(seconds: 20));

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Backend error ${response.statusCode}: ${response.body}');
    }

    final jsonBody = jsonDecode(response.body) as Map<String, dynamic>;
    return AnalyzeCallResult(
      response: AnalyzeResponse.fromJson(jsonBody),
      requestPayload: payload,
      responsePayload: jsonBody,
    );
  }
}
