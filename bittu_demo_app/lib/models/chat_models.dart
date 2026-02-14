class ChatMessage {
  ChatMessage({
    required this.sender,
    required this.text,
    required this.timestamp,
  });

  final String sender;
  final String text;
  final int timestamp;

  Map<String, dynamic> toJson() {
    return {
      'sender': sender,
      'text': text,
      'timestamp': timestamp,
    };
  }
}

class AnalyzeResponse {
  AnalyzeResponse({
    required this.status,
    required this.reply,
    required this.scamDetected,
    required this.shouldEngage,
    required this.extractedIntelligence,
    required this.agentNotes,
  });

  final String status;
  final String reply;
  final bool scamDetected;
  final bool shouldEngage;
  final Map<String, dynamic> extractedIntelligence;
  final String agentNotes;

  factory AnalyzeResponse.fromJson(Map<String, dynamic> json) {
    return AnalyzeResponse(
      status: (json['status'] ?? '').toString(),
      reply: (json['reply'] ?? '').toString(),
      scamDetected: json['scamDetected'] == true,
      shouldEngage: json['shouldEngage'] == true,
      extractedIntelligence: (json['extractedIntelligence'] as Map<String, dynamic>? ?? <String, dynamic>{}),
      agentNotes: (json['agentNotes'] ?? '').toString(),
    );
  }
}

class ThoughtLog {
  ThoughtLog({required this.type, required this.message, required this.timestamp});

  final String type;
  final String message;
  final DateTime timestamp;
}

class TimelineEvent {
  TimelineEvent({required this.title, required this.description, required this.symbol, required this.timestamp});

  final String title;
  final String description;
  final String symbol;
  final DateTime timestamp;
}

class AssetStatus {
  AssetStatus({required this.name, required this.state, this.alert = false});

  final String name;
  final String state;
  final bool alert;
}
