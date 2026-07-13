// lib/data/providers/auth_provider.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/auth_service.dart';

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
  }

  // ── Login ─────────────────────────────────────────────────────────────────
  Future<void> login(String email, String password) async {
    await AuthService.instance.login(email, password);
    state = AuthStatus.authenticated;
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