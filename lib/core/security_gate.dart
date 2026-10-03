// lib/core/security_gate.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/services/security_gate_service.dart';
import '../data/providers/auth_provider.dart';

/// Wraps a sensitive action behind a biometric/passcode check. Returns true
/// only if the person actually passed it — callers should bail out (not
/// proceed with the action) on false.
Future<bool> requireSecurityGate(
  BuildContext context,
  WidgetRef ref,
  String reason,
) async {
  final result = await SecurityGateService.instance.verify(reason);

  switch (result) {
    case SecurityGateResult.verified:
      return true;

    case SecurityGateResult.failed:
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Authentication failed')),
        );
      }
      return false;

    case SecurityGateResult.unavailable:
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Set a device passcode or biometric to use this feature'),
          ),
        );
      }
      return false;

    case SecurityGateResult.lockedOut:
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Too many failed attempts — signed out for security'),
          ),
        );
      }
      await ref.read(authProvider.notifier).signOut();
      return false;
  }
}