import 'package:flutter/material.dart';

class ActiveDefensePanel extends StatelessWidget {
  const ActiveDefensePanel({
    super.key,
    required this.enabled,
    required this.timeWasted,
    required this.onChanged,
  });

  final bool enabled;
  final int timeWasted;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF151320),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF3D2A45)),
      ),
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Active Defense Mode',
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
              ),
              Switch(value: enabled, onChanged: onChanged),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            enabled ? 'Bittu Interception Mode is LIVE.' : 'Interception paused.',
            style: TextStyle(
              color: enabled ? const Color(0xFF6EF4A4) : const Color(0xFFB3BDCC),
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 10),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFF0F1622),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: const Color(0xFF293548)),
            ),
            child: const Text(
              'Live feed: decoy OTP, fake account details, and safe lure responses are generated to increase attacker dwell time.',
              style: TextStyle(color: Color(0xFFC2CEE0), fontSize: 12),
            ),
          ),
          const Spacer(),
          Text(
            'Scammer Time Wasted: $timeWasted min',
            style: const TextStyle(color: Color(0xFFFFC978), fontSize: 16, fontWeight: FontWeight.w800),
          ),
        ],
      ),
    );
  }
}
