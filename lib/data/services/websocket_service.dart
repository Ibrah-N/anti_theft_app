// lib/data/services/websocket_service.dart

import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../../core/constants/app_constants.dart';
import 'auth_service.dart';

// ── Message types from backend ─────────────────────────────────────────────
enum WsMessageType { initialState, statusUpdate, sensorUpdate, alert, unknown }

class WsMessage {
  final WsMessageType type;
  final Map<String, dynamic> payload;

  const WsMessage({required this.type, required this.payload});

  factory WsMessage.fromJson(Map<String, dynamic> json) {
    final type = switch (json['type']) {
      'initial_state'  => WsMessageType.initialState,
      'status_update'  => WsMessageType.statusUpdate,
      'sensor_update'  => WsMessageType.sensorUpdate,
      'alert'          => WsMessageType.alert,
      _                => WsMessageType.unknown,
    };
    return WsMessage(
      type:    type,
      payload: Map<String, dynamic>.from(json['payload'] ?? {}),
    );
  }
}

// ── WebSocket Service ──────────────────────────────────────────────────────
class WebSocketService {
  WebSocketService._();
  static final WebSocketService instance = WebSocketService._();

  WebSocketChannel? _channel;
  StreamController<WsMessage>? _controller;

  bool get isConnected => _channel != null;

  // ── Connect ───────────────────────────────────────────────────────────────
  Future<Stream<WsMessage>> connect() async {
    await disconnect(); // clean up any existing connection

    final token = await AuthService.instance.getAccessToken();
    if (token == null) throw Exception('No access token found');

    final uri = Uri.parse('${AppConstants.wsUrl}?token=$token');
    _channel    = WebSocketChannel.connect(uri);
    _controller = StreamController<WsMessage>.broadcast();

    _channel!.stream.listen(
      (data) {
        try {
          final json    = jsonDecode(data as String);
          final message = WsMessage.fromJson(json);
          _controller!.add(message);
        } catch (e) {
          // ignore malformed messages
        }
      },
      onDone:  () => _controller?.close(),
      onError: (_) => _controller?.close(),
    );

    return _controller!.stream;
  }

  // ── Disconnect ────────────────────────────────────────────────────────────
  Future<void> disconnect() async {
    await _channel?.sink.close();
    await _controller?.close();
    _channel    = null;
    _controller = null;
  }
}