import 'package:flutter/material.dart';

import '../models/chat_models.dart';

class ThoughtTracePanel extends StatelessWidget {
  const ThoughtTracePanel({super.key, required this.logs});

  final List<ThoughtLog> logs;

  Color _typeColor(String type) {
    switch (type) {
      case 'THOUGHT':
        return const Color(0xFF7EE0FF);
      case 'ACTION':
        return const Color(0xFF76F7A7);
      case 'TOOL_CALL':
        return const Color(0xFFFFC978);
      case 'VERDICT':
        return const Color(0xFFFF7A7A);
      default:
        return Colors.white70;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF0D1117),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF273247)),
      ),
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Bittu Thought-Trace',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 16),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: ListView.builder(
              reverse: false,
              itemCount: logs.length,
              itemBuilder: (context, index) {
                final log = logs[index];
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: RichText(
                    text: TextSpan(
                      style: const TextStyle(fontFamily: 'Courier', fontSize: 12),
                      children: [
                        TextSpan(
                          text: '${log.type}: ',
                          style: TextStyle(color: _typeColor(log.type), fontWeight: FontWeight.bold),
                        ),
                        TextSpan(
                          text: '"${log.message}"',
                          style: const TextStyle(color: Color(0xFFB6C2D6)),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
