// lib/core/constants/app_constants.dart

class AppConstants {
  AppConstants._();

  // ── Backend URLs ────────────────────────────────────────────────────────────
  // Android emulator → 10.0.2.2 reaches Mac's localhost
  static const String baseUrl    = 'https://vigilx.duckdns.org';
  static const String apiUrl     = '$baseUrl/api';
  static const String wsUrl      = 'wss://vigilx.duckdns.org/ws';

  // ── Storage keys ────────────────────────────────────────────────────────────
  static const String keyAccessToken  = 'access_token';
  static const String keyRefreshToken = 'refresh_token';
}