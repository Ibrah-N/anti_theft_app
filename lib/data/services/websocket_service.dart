// lib/data/services/websocket_service.dart

import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../../core/constants/app_constants.dart';
import 'auth_service.dart';

// ── Message types from backend ─────────────────────────────────────────────
enum WsMessageType { initialState, statusUpdate, sensorUpdate, alert, commandAck, webrtcOffer, webrtcIce, unknown }

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
      'command_ack'    => WsMessageType.commandAck,
      'webrtc_offer'   => WsMessageType.webrtcOffer,
      'webrtc_ice'     => WsMessageType.webrtcIce,
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

  // Persistent for the life of the app — created once, never replaced.
  // This is what fixes the "listener orphaned after reconnect" bug:
  // anything that subscribes to `messages` once (like cameraProvider) stays
  // correctly connected even if the underlying socket reconnects, because
  // reconnecting only ever feeds into this same controller, never replaces it.
  final StreamController<WsMessage> _controller =
      StreamController<WsMessage>.broadcast();

  bool get isConnected => _channel != null;

  Stream<WsMessage> get messages => _controller.stream;

  /// Send a message back to the backend — used for WebRTC signaling
  /// (answer + ICE candidates). Everything else on this socket has been
  /// one-directional (server → app) until now.
  void send(Map<String, dynamic> message) {
    _channel?.sink.add(jsonEncode(message));
  }

  // ── Connect ───────────────────────────────────────────────────────────────
  Future<Stream<WsMessage>> connect() async {
    await _closeChannel(); // drop any existing socket, but keep _controller alive

    final token = await AuthService.instance.getAccessToken();
    if (token == null) throw Exception('No access token found');

    final uri = Uri.parse('${AppConstants.wsUrl}?token=$token');
    _channel = WebSocketChannel.connect(uri);

    _channel!.stream.listen(
      (data) {
        try {
          final json    = jsonDecode(data as String);
          final message = WsMessage.fromJson(json);
          _controller.add(message);
        } catch (e) {
          // ignore malformed messages
        }
      },
      onDone:  () => _channel = null,
      onError: (_) => _channel = null,
    );

    return _controller.stream;
  }

  // ── Disconnect ────────────────────────────────────────────────────────────
  // Only closes the socket itself — _controller stays alive for the app's
  // lifetime so existing listeners never get silently orphaned.
  Future<void> disconnect() async {
    await _closeChannel();
  }

  Future<void> _closeChannel() async {
    await _channel?.sink.close();
    _channel = null;
  }
}