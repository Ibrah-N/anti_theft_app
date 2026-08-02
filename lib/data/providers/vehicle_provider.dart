// lib/data/providers/vehicle_provider.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/models/vehicle_model.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';

import '../models/alert_model.dart';
import '../services/notification_service.dart';
import 'alerts_provider.dart';


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
}

final vehicleProvider =
StateNotifierProvider<VehicleNotifier, AsyncValue<VehicleModel>>(
  (ref) => VehicleNotifier(ref),
);