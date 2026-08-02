// lib/data/providers/auth_provider.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/auth_service.dart';

import 'package:firebase_messaging/firebase_messaging.dart';
import '../services/api_service.dart';


// ── Auth state ────────────────────────────────────────────────────────────────
enum AuthStatus { unknown, authenticated, unauthenticated }

class AuthNotifier extends StateNotifier<AuthStatus> {
  AuthNotifier() : super(AuthStatus.unknown) {
    _checkAuth();
  }

  // ── Check on app start if token exists ────────────────────────────────────
  Future<void> _checkAuth() async {
    final loggedIn = await AuthService.instance.isLoggedIn();
    state = loggedIn
    ? AuthStatus.authenticated
    : AuthStatus.unauthenticated;
    if (loggedIn) {
    _registerFcmToken();
    }
  }

  // ── Login ─────────────────────────────────────────────────────────────────
  Future<void> login(String email, String password) async {
    await AuthService.instance.login(email, password);
    state = AuthStatus.authenticated;
    _registerFcmToken();
  }

  // ── Register this device's FCM token with the backend ─────────────────────
  Future<void> _registerFcmToken() async {
    try {
    final token = await FirebaseMessaging.instance.getToken();
    if (token != null) {
    await ApiService.instance.registerFcmToken(token);
          }
        } catch (_) {
    // non-fatal — app still works without push notifications
      }
  }

  // ── Sign out ──────────────────────────────────────────────────────────────
  Future<void> signOut() async {
    await AuthService.instance.signOut();
    state = AuthStatus.unauthenticated;
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthStatus>(
  (ref) => AuthNotifier(),
);