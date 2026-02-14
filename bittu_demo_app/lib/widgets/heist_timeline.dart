import 'package:flutter/material.dart';

import '../models/chat_models.dart';

class HeistTimeline extends StatelessWidget {
  const HeistTimeline({super.key, required this.events});

  final List<TimelineEvent> events;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF121A27),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF283245)),
      ),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Heist Timeline',
            style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 16),
          ),
          const SizedBox(height: 10),
          Expanded(
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: events.length,
              separatorBuilder: (_, __) => const SizedBox(width: 10),
              itemBuilder: (context, index) {
                final event = events[index];
                return Container(
                  width: 220,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFF192232),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF32445F)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${event.symbol} ${event.title}',
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        event.description,
                        style: const TextStyle(color: Color(0xFFB9C6DA), fontSize: 12),
                      ),
                      const Spacer(),
                      Text(
                        event.timestamp.toIso8601String().substring(11, 19),
                        style: const TextStyle(color: Color(0xFF7D91AE), fontSize: 11),
                      ),
                    ],
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
