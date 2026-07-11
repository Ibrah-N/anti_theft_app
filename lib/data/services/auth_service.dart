// lib/data/services/auth_service.dart

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../core/constants/app_constants.dart';
import 'api_service.dart';

class AuthService {
  AuthService._();
  static final AuthService instance = AuthService._();

  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  // ── Login — saves tokens to secure storage ─────────────────────────────────
  Future<void> login(String email, String password) async {
    final data = await ApiService.instance.login(email, password);
    await _storage.write(
      key:   AppConstants.keyAccessToken,
      value: data['access_token'],
    );
    await _storage.write(
      key:   AppConstants.keyRefreshToken,
      value: data['refresh_token'],
    );
  }

  // ── Sign out — clears all tokens ───────────────────────────────────────────
  Future<void> signOut() async {
    await _storage.deleteAll();
  }

  // ── Check if user is already logged in ────────────────────────────────────
  Future<bool> isLoggedIn() async {
    final token = await _storage.read(key: AppConstants.keyAccessToken);
    return token != null;
  }

  // ── Get stored token (used by WebSocket service) ───────────────────────────
  Future<String?> getAccessToken() async {
    return _storage.read(key: AppConstants.keyAccessToken);
  }
}