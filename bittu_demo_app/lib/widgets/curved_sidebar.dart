import 'package:flutter/material.dart';

enum SidebarTab { home, messages, setting, help, password, signOut }

class CurvedSidebar extends StatelessWidget {
  const CurvedSidebar({
    super.key,
    required this.activeTab,
    required this.onSelect,
  });

  final SidebarTab activeTab;
  final ValueChanged<SidebarTab> onSelect;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 230,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        gradient: const LinearGradient(
          colors: [Color(0xFF4A57F2), Color(0xFF3E53F0)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        boxShadow: const [
          BoxShadow(
            color: Color(0x4D000000),
            blurRadius: 16,
            offset: Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        children: [
          const SizedBox(height: 20),
          _item(icon: Icons.home_outlined, label: 'Home', tab: SidebarTab.home),
          _activeTabItem(icon: Icons.chat_bubble_outline, label: 'Messages', tab: SidebarTab.messages),
          _item(icon: Icons.settings_outlined, label: 'Setting', tab: SidebarTab.setting),
          _item(icon: Icons.help_outline, label: 'Help', tab: SidebarTab.help),
          _item(icon: Icons.lock_outline, label: 'Password', tab: SidebarTab.password),
          _item(icon: Icons.logout, label: 'Sign Out', tab: SidebarTab.signOut),
          const Spacer(),
          const SizedBox(height: 18),
        ],
      ),
    );
  }

  Widget _item({required IconData icon, required String label, required SidebarTab tab}) {
    final isActive = activeTab == tab;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: InkWell(
        onTap: () => onSelect(tab),
        borderRadius: BorderRadius.circular(12),
        child: Container(
          height: 44,
          alignment: Alignment.centerLeft,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: isActive ? const Color(0x1FFFFFFF) : Colors.transparent,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Icon(icon, color: const Color(0xFFE7ECFF), size: 19),
              const SizedBox(width: 14),
              Text(
                label,
                style: const TextStyle(
                  color: Color(0xFFE9EEFF),
                  fontSize: 16,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _activeTabItem({required IconData icon, required String label, required SidebarTab tab}) {
    if (activeTab != tab) {
      return _item(icon: icon, label: label, tab: tab);
    }
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Positioned(
            right: -12,
            top: -18,
            child: Container(
              width: 24,
              height: 24,
              decoration: const BoxDecoration(
                color: Color(0xFF4255F2),
                shape: BoxShape.circle,
              ),
            ),
          ),
          Positioned(
            right: -12,
            bottom: -18,
            child: Container(
              width: 24,
              height: 24,
              decoration: const BoxDecoration(
                color: Color(0xFF4255F2),
                shape: BoxShape.circle,
              ),
            ),
          ),
          Container(
            height: 50,
            padding: const EdgeInsets.symmetric(horizontal: 14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
            ),
            child: InkWell(
              onTap: () => onSelect(tab),
              borderRadius: BorderRadius.circular(20),
              child: Row(
                children: [
                  Icon(icon, color: const Color(0xFF16223C), size: 20),
                  const SizedBox(width: 12),
                  Text(
                    label,
                    style: const TextStyle(
                      color: Color(0xFF16223C),
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
