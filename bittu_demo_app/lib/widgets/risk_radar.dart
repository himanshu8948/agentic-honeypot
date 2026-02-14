import 'dart:math';

import 'package:flutter/material.dart';

class RiskRadar extends StatefulWidget {
  const RiskRadar({super.key, required this.riskScore});

  final int riskScore;

  @override
  State<RiskRadar> createState() => _RiskRadarState();
}

class _RiskRadarState extends State<RiskRadar> with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
  }

  @override
  void didUpdateWidget(covariant RiskRadar oldWidget) {
    super.didUpdateWidget(oldWidget);
    final ms = (1400 - (widget.riskScore * 10)).clamp(350, 1400);
    _pulseController.duration = Duration(milliseconds: ms);
    if (!_pulseController.isAnimating) {
      _pulseController.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  Color _riskColor(int score) {
    if (score >= 75) {
      return const Color(0xFFFF4D4D);
    }
    if (score >= 40) {
      return const Color(0xFFFFCD4D);
    }
    return const Color(0xFF45E18D);
  }

  String _riskLabel(int score) {
    if (score >= 75) {
      return 'LETHAL';
    }
    if (score >= 40) {
      return 'SUSPICIOUS';
    }
    return 'SAFE';
  }

  @override
  Widget build(BuildContext context) {
    final color = _riskColor(widget.riskScore);

    return Container(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF1D1427), Color(0xFF10151F)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFF2A3A52)),
      ),
      child: AnimatedBuilder(
        animation: _pulseController,
        builder: (context, _) {
          return CustomPaint(
            painter: _RiskRadarPainter(
              score: widget.riskScore,
              pulse: _pulseController.value,
              color: color,
            ),
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    '${widget.riskScore}',
                    style: TextStyle(color: color, fontWeight: FontWeight.w900, fontSize: 52),
                  ),
                  Text(
                    _riskLabel(widget.riskScore),
                    style: const TextStyle(color: Colors.white, letterSpacing: 1.1, fontWeight: FontWeight.w700),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class _RiskRadarPainter extends CustomPainter {
  _RiskRadarPainter({required this.score, required this.pulse, required this.color});

  final int score;
  final double pulse;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = min(size.width, size.height) * 0.38;

    final glowPaint = Paint()
      ..color = color.withValues(alpha: 0.18 + (0.2 * pulse))
      ..style = PaintingStyle.stroke
      ..strokeWidth = 22;

    final ringPaint = Paint()
      ..color = const Color(0xFF2D3D55)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 16;

    final progressPaint = Paint()
      ..shader = SweepGradient(
        startAngle: -pi / 2,
        endAngle: (3 * pi) / 2,
        colors: [color.withValues(alpha: 0.35), color],
      ).createShader(Rect.fromCircle(center: center, radius: radius))
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 16;

    canvas.drawCircle(center, radius + (9 * pulse), glowPaint);
    canvas.drawCircle(center, radius, ringPaint);

    final arcSweep = ((score.clamp(0, 100) / 100) * (2 * pi));
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -pi / 2,
      arcSweep,
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _RiskRadarPainter oldDelegate) {
    return oldDelegate.score != score || oldDelegate.pulse != pulse || oldDelegate.color != color;
  }
}
