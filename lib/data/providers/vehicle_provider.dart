// lib/data/providers/vehicle_provider.dart


// stash: Saved working directory and index state WIP on main: 919cd23 files updated
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/models/vehicle_model.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';

import '../models/alert_model.dart';
import '../services/notification_service.dart';
import 'alerts_provider.dart';


// ── Pending commands ───────────────────────────────────────────────────────────
// Tracks which ack-gated commands are currently in flight, so buttons can be
// disabled until the device confirms (or the debounce timeout clears them).
// Keys: "lock", "mirror_fl", "mirror_fr", "mirror_rl", "mirror_rr", "start",
//       "ac", "arm".
const _pendingCommandTimeout = Duration(seconds: 10);

class PendingCommandsNotifier extends StateNotifier<Set<String>> {
  PendingCommandsNotifier() : super(const {});

  final Map<String, Timer> _timeouts = {};

  void start(String cmd) {
    state = {...state, cmd};
    _timeouts[cmd]?.cancel();
    _timeouts[cmd] = Timer(_pendingCommandTimeout, () => clear(cmd));
  }

  void clear(String cmd) {
    _timeouts[cmd]?.cancel();
    _timeouts.remove(cmd);
    if (!state.contains(cmd)) return;
    state = {...state}..remove(cmd);
  }

  @override
  void dispose() {
    for (final t in _timeouts.values) {
      t.cancel();
    }
    super.dispose();
  }
}

final pendingCommandsProvider =
    StateNotifierProvider<PendingCommandsNotifier, Set<String>>(
  (ref) => PendingCommandsNotifier(),
);

// ── Vehicle state notifier ────────────────────────────────────────────────────
class VehicleNotifier extends StateNotifier<AsyncValue<VehicleModel>> {
  final Ref ref;
  VehicleNotifier(this.ref) : super(const AsyncValue.loading()) {
  _init();
    }

  // ── Load initial state from REST + subscribe to WebSocket ─────────────────
  Future<void> _init() async {
  try {
    final data    = await ApiService.instance.getVehicleStatus();
      state         = AsyncValue.data(VehicleModel.fromJson(data));

      // 2. Subscribe to WebSocket for live updates
      final stream  = await WebSocketService.instance.connect();
      stream.listen(_onWsMessage);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  // ── Handle incoming WebSocket messages ────────────────────────────────────
  void _onWsMessage(WsMessage message) {
    final current = state.valueOrNull;
    if (current == null) return;

    switch (message.type) {
      case WsMessageType.initialState:
      case WsMessageType.statusUpdate:
      state = AsyncValue.data(current.copyWithJson(message.payload));
      break;
      case WsMessageType.sensorUpdate:
      state = AsyncValue.data(current.copyWithJson(message.payload));
      break;
      case WsMessageType.alert:
      _onAlertReceived(message.payload);
      break;
            case WsMessageType.commandAck:
      state = AsyncValue.data(current.copyWithJson(message.payload));
      final cmd = message.payload['cmd'] as String?;
      if (cmd != null) {
        ref.read(pendingCommandsProvider.notifier).clear(cmd);
      }
      break;
      case WsMessageType.webrtcOffer:
      case WsMessageType.webrtcIce:
      // Handled by cameraProvider's own listener on this same broadcast
      // stream — nothing for vehicleProvider to do with these.
      break;
      case WsMessageType.unknown:
      break;
          }
  }

  void _onAlertReceived(Map<String, dynamic> payload) {
    final alert = AlertModel.fromJson(payload);

    NotificationService.instance.showAlert(
    title: alert.title,
    body:  alert.description,
        );

    ref.read(alertsProvider.notifier).prependAlert(alert);
  }

  // ── Manual retry (used by error UI) ────────────────────────────────────────
  Future<void> retry() async {
    state = const AsyncValue.loading();
    await _init();
  } 

  // ── Engine control ────────────────────────────────────────────────────────
  Future<void> toggleEngine(bool state) async {
    // Just send command — state updates via WebSocket when device confirms
    await ApiService.instance.controlEngine(state);
  }

  // ── Fuel control ──────────────────────────────────────────────────────────
  Future<void> toggleFuel(bool state) async {
    // Just send command — state updates via WebSocket when device confirms
    await ApiService.instance.controlFuel(state);
  }

  // ── Ack-gated commands ─────────────────────────────────────────────────────
  // Each of these marks its command "pending" (disabling its button in the UI)
  // until the device's ACK arrives over WebSocket, or the debounce timeout
  // clears it — see PendingCommandsNotifier above.
  Future<void> _sendAckGated(String cmd, Future<void> Function() send) async {
    final pending = ref.read(pendingCommandsProvider.notifier);
    if (ref.read(pendingCommandsProvider).contains(cmd)) return; // debounce
    pending.start(cmd);
    try {
      await send();
    } catch (_) {
      // Request failed to even reach the server — clear immediately so the
      // button isn't stuck disabled until the timeout.
      pending.clear(cmd);
      rethrow;
    }
  }

  Future<void> toggleLock(bool state) =>
      _sendAckGated('lock', () => ApiService.instance.controlLock(state));

  /// [position] is one of "fl", "fr", "rl", "rr". [state] true = fold.
  Future<void> toggleMirror(String position, bool state) =>
      _sendAckGated(
        'mirror_$position',
        () => ApiService.instance.controlMirror(position, state),
      );

  Future<void> toggleStart(bool state) =>
      _sendAckGated('start', () => ApiService.instance.controlStart(state));

  Future<void> toggleAc(bool state) =>
      _sendAckGated('ac', () => ApiService.instance.controlAc(state));

  Future<void> toggleArm(bool state) =>
      _sendAckGated('arm', () => ApiService.instance.controlArm(state));
}

final vehicleProvider =
StateNotifierProvider<VehicleNotifier, AsyncValue<VehicleModel>>(
  (ref) => VehicleNotifier(ref),
);