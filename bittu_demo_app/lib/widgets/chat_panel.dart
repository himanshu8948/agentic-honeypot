import 'package:flutter/material.dart';

import '../models/chat_models.dart';

class ChatPanel extends StatefulWidget {
  const ChatPanel({
    super.key,
    required this.messages,
    required this.isSending,
    required this.onSend,
    required this.onQuickScenario,
  });

  final List<ChatMessage> messages;
  final bool isSending;
  final ValueChanged<String> onSend;
  final ValueChanged<String> onQuickScenario;

  @override
  State<ChatPanel> createState() => _ChatPanelState();
}

class _ChatPanelState extends State<ChatPanel> {
  final TextEditingController _inputController = TextEditingController();

  @override
  void dispose() {
    _inputController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF101725),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF2E3A4E)),
      ),
      child: Column(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: const BoxDecoration(
              color: Color(0xFF0D1320),
              borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
            ),
            child: const Text(
              'TRY HERE TO SCAM BITTU',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
            ),
          ),
          const Padding(
            padding: EdgeInsets.fromLTRB(12, 10, 12, 0),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                'Feed scam-style messages so Bittu can generate better answers.',
                style: TextStyle(color: Color(0xFF8EA4C4), fontSize: 12),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 6),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _ScenarioChip(
                  label: 'Refund OTP Trap',
                  onTap: () => widget.onQuickScenario('Your refund is pending. Share OTP now.'),
                ),
                _ScenarioChip(
                  label: 'UPI Verification',
                  onTap: () => widget.onQuickScenario('Send your UPI and PIN for verification immediately.'),
                ),
                _ScenarioChip(
                  label: 'Hi Mom Scam',
                  onTap: () => widget.onQuickScenario('Hi Mom, this is my new number. Urgent transfer needed.'),
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: widget.messages.length,
              itemBuilder: (context, index) {
                final msg = widget.messages[index];
                final fromScammer = msg.sender == 'scammer';
                return Align(
                  alignment: fromScammer ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    constraints: const BoxConstraints(maxWidth: 380),
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: BoxDecoration(
                      color: fromScammer ? const Color(0xFF1F4B6C) : const Color(0xFF1B2D44),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      msg.text,
                      style: const TextStyle(color: Colors.white),
                    ),
                  ),
                );
              },
            ),
          ),
          if (widget.isSending)
            const Padding(
              padding: EdgeInsets.only(bottom: 6),
              child: Text('Bittu is reasoning...', style: TextStyle(color: Color(0xFF88A3C2))),
            ),
          Padding(
            padding: const EdgeInsets.all(10),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _inputController,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      hintText: 'Type as the scammer...',
                      hintStyle: const TextStyle(color: Color(0xFF7F90A9)),
                      filled: true,
                      fillColor: const Color(0xFF0E1523),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: const BorderSide(color: Color(0xFF2B3950)),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                        borderSide: const BorderSide(color: Color(0xFF2B3950)),
                      ),
                    ),
                    onSubmitted: _sendFromSubmitted,
                  ),
                ),
                const SizedBox(width: 10),
                ElevatedButton(
                  onPressed: widget.isSending
                      ? null
                      : _sendFromButton,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF3CC18A),
                    foregroundColor: const Color(0xFF08201A),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
                  ),
                  child: const Text('Send'),
                ),
              ],
            ),
          )
        ],
      ),
    );
  }

  void _sendFromButton() {
    _sendAndClear();
  }

  void _sendFromSubmitted(String _) {
    _sendAndClear();
  }

  void _sendAndClear() {
    final text = _inputController.text;
    widget.onSend(text);
    _inputController.clear();
  }
}

class _ScenarioChip extends StatelessWidget {
  const _ScenarioChip({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: const Color(0xFF1A2840),
          border: Border.all(color: const Color(0xFF395071)),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Text(
          label,
          style: const TextStyle(color: Color(0xFFC4D2E6), fontSize: 12),
        ),
      ),
    );
  }
}
