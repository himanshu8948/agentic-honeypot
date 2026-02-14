import 'dart:convert';

import 'package:flutter/material.dart';

import 'config/app_config.dart';
import 'state/demo_controller.dart';
import 'widgets/chat_panel.dart';
import 'widgets/curved_sidebar.dart';

class BittuAgenticApp extends StatelessWidget {
  const BittuAgenticApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Bittu Agentic Arena',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        scaffoldBackgroundColor: const Color(0xFF070B13),
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF4AB0FF), brightness: Brightness.dark),
        useMaterial3: true,
      ),
      home: const BittuArenaPage(),
    );
  }
}

class BittuArenaPage extends StatefulWidget {
  const BittuArenaPage({super.key});

  @override
  State<BittuArenaPage> createState() => _BittuArenaPageState();
}

class _BittuArenaPageState extends State<BittuArenaPage> {
  final AgenticController controller = AgenticController();
  final TextEditingController _urlController = TextEditingController(text: AppConfig.defaultBaseUrl());
  final TextEditingController _apiController = TextEditingController(text: AppConfig.defaultApiKey);
  final TextEditingController _headerController = TextEditingController(text: 'VK-AAACCC');
  final TextEditingController _numberController = TextEditingController(text: '+919000000000');
  final TextEditingController _loginUserController = TextEditingController();
  final TextEditingController _loginPasswordController = TextEditingController();
  String _platform = 'sms';
  bool _inContacts = false;
  bool _rememberMe = true;
  bool _loggedIn = false;
  SidebarTab _activeTab = SidebarTab.home;

  @override
  void dispose() {
    controller.dispose();
    _urlController.dispose();
    _apiController.dispose();
    _headerController.dispose();
    _numberController.dispose();
    _loginUserController.dispose();
    _loginPasswordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        return Scaffold(
          body: Container(
            decoration: _loggedIn
                ? const BoxDecoration(
                    image: DecorationImage(
                      image: AssetImage('assets/images/hero_bg.jfif'),
                      fit: BoxFit.cover,
                    ),
                  )
                : const BoxDecoration(
                    color: Color(0xFF101A2A),
                  ),
            child: SafeArea(
              child: _loggedIn ? _buildDashboardShell() : _buildLoginScreen(),
            ),
          ),
        );
      },
    );
  }

  Widget _buildDashboardShell() {
    return Container(
      decoration: const BoxDecoration(
        image: DecorationImage(
          image: AssetImage('assets/images/dashboard_bg.jfif'),
          fit: BoxFit.cover,
        ),
      ),
      child: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [Color(0x99040A13), Color(0xA614223A), Color(0xB8152C49)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              CurvedSidebar(
                activeTab: _activeTab,
                onSelect: (tab) {
                  if (tab == SidebarTab.signOut) {
                    setState(() {
                      _loggedIn = false;
                    });
                    return;
                  }
                  setState(() {
                    _activeTab = tab;
                  });
                },
              ),
              const SizedBox(width: 14),
              Expanded(
                child: _activeTab == SidebarTab.messages
                    ? _buildMessagesWorkspace()
                    : _buildHomeWorkspace(),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildLoginScreen() {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [Color(0xC0050A13), Color(0xB30F1A2A), Color(0xB3122035)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Center(
        child: Container(
          width: 900,
          constraints: const BoxConstraints(maxWidth: 980, minHeight: 460),
          margin: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: const Color(0xFFF3F7FE),
            borderRadius: BorderRadius.circular(18),
            boxShadow: const [
              BoxShadow(
                color: Color(0x55000000),
                blurRadius: 20,
                offset: Offset(0, 12),
              ),
            ],
          ),
          child: Row(
            children: [
              Expanded(
                flex: 48,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 36, vertical: 30),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Login please',
                        style: TextStyle(color: Color(0xFF13213A), fontSize: 28, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 20),
                      TextField(
                        controller: _loginUserController,
                        style: const TextStyle(color: Color(0xFF1A2A45)),
                        decoration: const InputDecoration(
                          labelText: 'Input your user ID or Email',
                          labelStyle: TextStyle(color: Color(0xFFB7C8DC)),
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.email_outlined),
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _loginPasswordController,
                        obscureText: true,
                        style: const TextStyle(color: Color(0xFF1A2A45)),
                        decoration: const InputDecoration(
                          labelText: 'Input your password',
                          labelStyle: TextStyle(color: Color(0xFFB7C8DC)),
                          border: OutlineInputBorder(),
                          prefixIcon: Icon(Icons.lock_outline),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Checkbox(
                            value: _rememberMe,
                            onChanged: (v) {
                              setState(() {
                                _rememberMe = v ?? true;
                              });
                            },
                          ),
                          const Text('Remember me', style: TextStyle(color: Color(0xFF51617D))),
                          const Spacer(),
                          TextButton(
                            onPressed: () {},
                            child: const Text('Forgot Password?'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      ElevatedButton.icon(
                        onPressed: _handleLogin,
                        icon: const Icon(Icons.login),
                        label: const Text('LOG IN'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF1E62FF),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                        ),
                      ),
                      const SizedBox(height: 8),
                      OutlinedButton.icon(
                        onPressed: _handleRegister,
                        icon: const Icon(Icons.person_add_alt_1),
                        label: const Text('REGISTER (NEW USER)'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: const Color(0xFF9BC5FF),
                          side: const BorderSide(color: Color(0xFF4A74B8)),
                          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              Expanded(
                flex: 52,
                child: ClipRRect(
                  borderRadius: const BorderRadius.only(
                    topRight: Radius.circular(18),
                    bottomRight: Radius.circular(18),
                  ),
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      Image.asset('assets/images/login_template.jfif', fit: BoxFit.cover),
                      Container(
                        decoration: const BoxDecoration(
                          gradient: LinearGradient(
                            colors: [Color(0x660A2A7B), Color(0xAA0E3CD2)],
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                          ),
                        ),
                      ),
                      const Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text('WELCOME!', style: TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w900)),
                            SizedBox(height: 10),
                            Text(
                              'Enter your details and start journey with us',
                              style: TextStyle(color: Color(0xFFE3EDFF), fontSize: 14),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHomeWorkspace() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'HOME',
          style: TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w900),
        ),
        const SizedBox(height: 6),
        const Text(
          'Keep connection and sender metadata here. Use Messages tab for Bittu chat.',
          style: TextStyle(color: Color(0xFFC5D3E8), fontSize: 13),
        ),
        const SizedBox(height: 14),
        _buildConfigBar(),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: const Color(0xCC0E1727),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFF2A3A51)),
          ),
          child: Row(
            children: [
              Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  color: controller.backendOnline ? const Color(0xFF4CE08F) : const Color(0xFFFF7A7A),
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 10),
              Text(
                controller.backendOnline ? 'Backend Connected' : 'Backend Not Connected',
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMessagesWorkspace() {
    return Column(
      children: [
        Row(
          children: [
            const Expanded(
              child: Text(
                'MESSAGES',
                style: TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w900),
              ),
            ),
            ElevatedButton.icon(
              onPressed: _endChatAndShowPayload,
              icon: const Icon(Icons.stop_circle_outlined),
              label: const Text('END CHAT'),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFE14A4A),
                foregroundColor: Colors.white,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Expanded(
          child: ChatPanel(
            messages: controller.transcript,
            isSending: controller.isSending,
            onSend: controller.sendJudgeMessage,
            onQuickScenario: controller.runQuickScenario,
          ),
        ),
      ],
    );
  }

  Widget _buildConfigBar() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0D1522),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF2A3A51)),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _urlController,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'Backend Base URL',
                    labelStyle: TextStyle(color: Color(0xFF8DA2BE)),
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextField(
                  controller: _apiController,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'x-api-key',
                    labelStyle: TextStyle(color: Color(0xFF8DA2BE)),
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              ElevatedButton(
                onPressed: _applyConfig,
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF63D0A8), foregroundColor: const Color(0xFF072318)),
                child: const Text('Apply'),
              ),
              const SizedBox(width: 8),
              FilledButton.tonal(
                onPressed: controller.checkBackendHealth,
                child: Text(controller.backendOnline ? 'Backend Online' : 'Retry Health'),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              SizedBox(
                width: 150,
                child: DropdownButtonFormField<String>(
                  initialValue: _platform,
                  decoration: const InputDecoration(
                    labelText: 'Platform',
                    labelStyle: TextStyle(color: Color(0xFF8DA2BE)),
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  items: const [
                    DropdownMenuItem(value: 'sms', child: Text('SMS')),
                    DropdownMenuItem(value: 'whatsapp', child: Text('WhatsApp')),
                    DropdownMenuItem(value: 'telegram', child: Text('Telegram')),
                    DropdownMenuItem(value: 'email', child: Text('Email')),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _platform = value ?? 'sms';
                    });
                  },
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextField(
                  controller: _headerController,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'Sender Header (e.g. VK-AAACCC)',
                    labelStyle: TextStyle(color: Color(0xFF8DA2BE)),
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextField(
                  controller: _numberController,
                  style: const TextStyle(color: Colors.white),
                  decoration: const InputDecoration(
                    labelText: 'Sender Number',
                    labelStyle: TextStyle(color: Color(0xFF8DA2BE)),
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Row(
                children: [
                  Checkbox(
                    value: _inContacts,
                    onChanged: (value) {
                      setState(() {
                        _inContacts = value ?? false;
                      });
                    },
                  ),
                  const Text('In Contacts', style: TextStyle(color: Colors.white)),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _applyConfig() {
    controller.setEnvironment(baseUrl: _urlController.text, apiKey: _apiController.text);
    controller.setSignalContext(
      platform: _platform,
      senderHeader: _headerController.text,
      senderNumber: _numberController.text,
      inContacts: _inContacts,
    );
  }

  void _endChatAndShowPayload() {
    final payload = controller.buildFinalPayload();
    final pretty = const JsonEncoder.withIndent('  ').convert(payload);
    showDialog<void>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Final Payload (HCL/GUVI Tester Format)'),
          content: SingleChildScrollView(
            child: SelectableText(
              pretty,
              style: const TextStyle(fontFamily: 'Consolas', fontSize: 12),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
                controller.resetChatSession();
                setState(() {
                  _activeTab = SidebarTab.home;
                });
              },
              child: const Text('Close and Reset'),
            ),
          ],
        );
      },
    );
  }

  void _handleLogin() {
    if (_loginUserController.text.trim().isEmpty || _loginPasswordController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter both user/email and password.')),
      );
      return;
    }
    setState(() {
      _loggedIn = true;
    });
    _applyConfig();
  }

  void _handleRegister() {
    showDialog<void>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Register'),
          content: const Text(
            'Registration flow is UI-ready. We can now connect this to backend auth/signup API.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Close'),
            ),
          ],
        );
      },
    );
  }

}
