import 'package:flutter/foundation.dart';

class AppConfig {
  AppConfig._();

  static const String renderBaseUrl = 'https://himanshu-agentic-honeypot.onrender.com';

  static const String localDesktopBaseUrl = 'http://127.0.0.1:8000';
  static const String localAndroidEmulatorBaseUrl = 'http://10.0.2.2:8000';

  static String defaultBaseUrl() {
    if (defaultTargetPlatform == TargetPlatform.android) {
      return localAndroidEmulatorBaseUrl;
    }
    return localDesktopBaseUrl;
  }

  static const String defaultApiKey = 'himanshu_agentic_honeypot';
}
