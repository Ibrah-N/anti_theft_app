// lib/data/providers/vehicle_provider.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/models/vehicle_model.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';

// ── Vehicle state notifier ────────────────────────────────────────────────────
class VehicleNotifier extends StateNotifier<AsyncValue<VehicleModel>> {
  VehicleNotifier() : super(const AsyncValue.loading()) {
    _init();
  }

  // ── Load initial state from REST + subscribe to WebSocket ─────────────────
  Future<void> _init() async {
    try {
      // 1. Load current state from REST
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
      case WsMessageType.unknown:
        break;
    }
  }

  // ── Engine control ────────────────────────────────────────────────────────
  Future<void> toggleEngine(bool state) async {
    final data = await ApiService.instance.controlEngine(state);
    this.state = AsyncValue.data(VehicleModel.fromJson(data));
  }

  // ── Fuel control ──────────────────────────────────────────────────────────
  Future<void> toggleFuel(bool state) async {
    final data = await ApiService.instance.controlFuel(state);
    this.state = AsyncValue.data(VehicleModel.fromJson(data));
  }
}

final vehicleProvider =
    StateNotifierProvider<VehicleNotifier, AsyncValue<VehicleModel>>(
  (ref) => VehicleNotifier(),
);