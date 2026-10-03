// lib/data/services/security_gate_service.dart

import 'package:local_auth/local_auth.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

enum SecurityGateResult { verified, failed, lockedOut, unavailable }

/// Gates sensitive actions (unlock, disarm, engine start) behind the
/// device's own biometric + passcode check — not a PIN we invent and store
/// ourselves. `authenticate(biometricOnly: false)` is a single native OS
/// prompt that tries Face ID/fingerprint first and automatically falls back
/// to the device's own lock-screen PIN/passcode/pattern if biometrics fail
/// or aren't enrolled — the same trusted credential the person already
/// uses to unlock their phone, managed and rate-limited by the OS itself.
class SecurityGateService {
  SecurityGateService._();
  static final SecurityGateService instance = SecurityGateService._();

  final LocalAuthentication _auth = LocalAuthentication();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  static const _failedAttemptsKey = 'security_gate_failed_attempts';
  static const int maxFailedAttempts = 5;

  Future<SecurityGateResult> verify(String reason) async {
    bool passed;
    try {
      passed = await _auth.authenticate(
        localizedReason: reason,
        biometricOnly: false,
      );
    } on Exception {
      // No biometrics enrolled AND no device passcode set at all — nothing
      // to verify against. Block the action; don't count this as a failed
      // attempt, since the person didn't fail a challenge — there was no
      // challenge the device could present.
      return SecurityGateResult.unavailable;
    }

    if (passed) {
      await _resetFailedAttempts();
      return SecurityGateResult.verified;
    }

    final attempts = await _incrementFailedAttempts();
    if (attempts >= maxFailedAttempts) {
      await _resetFailedAttempts();
      return SecurityGateResult.lockedOut;
    }
    return SecurityGateResult.failed;
  }

  Future<int> _incrementFailedAttempts() async {
    final current =
        int.tryParse(await _storage.read(key: _failedAttemptsKey) ?? '0') ?? 0;
    final next = current + 1;
    await _storage.write(key: _failedAttemptsKey, value: next.toString());
    return next;
  }

  Future<void> _resetFailedAttempts() async {
    await _storage.delete(key: _failedAttemptsKey);
  }
}