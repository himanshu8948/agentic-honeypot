import 'package:flutter/material.dart';

import '../models/chat_models.dart';

class AssetShieldGrid extends StatelessWidget {
  const AssetShieldGrid({super.key, required this.assets});

  final List<AssetStatus> assets;

  @override
  Widget build(BuildContext context) {
    return GridView.builder(
      physics: const NeverScrollableScrollPhysics(),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 10,
        mainAxisSpacing: 10,
        childAspectRatio: 2.7,
      ),
      itemCount: assets.length,
      itemBuilder: (context, index) {
        final asset = assets[index];
        final borderColor = asset.alert ? const Color(0xFFFF5A5A) : const Color(0xFF31445F);
        final glow = asset.alert ? const Color(0xFFFF5A5A).withValues(alpha: 0.22) : Colors.transparent;

        return AnimatedContainer(
          duration: const Duration(milliseconds: 280),
          decoration: BoxDecoration(
            color: const Color(0xFF121B2A),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: borderColor, width: 1.4),
            boxShadow: [
              BoxShadow(color: glow, blurRadius: 12, spreadRadius: 1),
            ],
          ),
          padding: const EdgeInsets.all(10),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                asset.name,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 3),
              Text(
                asset.state,
                style: TextStyle(
                  color: asset.alert ? const Color(0xFFFFABAB) : const Color(0xFFAFC2D9),
                  fontSize: 12,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
