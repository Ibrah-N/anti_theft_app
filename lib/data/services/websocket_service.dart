// lib/data/services/websocket_service.dart

import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
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
    if (_channel == null) {
      debugPrint('[WebRTC] WS send DROPPED (socket is null): ${message['type']}');
      return;
    }
    _channel!.sink.add(jsonEncode(message));
  }

  // ── Connect ───────────────────────────────────────────────────────────────
  Future<Stream<WsMessage>> connect() async {
    await _closeChannel(); // drop any existing socket, but keep _controller alive

    final token = await AuthService.instance.getAccessToken();
    if (token == null) throw Exception('No access token found');

    final uri = Uri.parse('${AppConstants.wsUrl}?token=$token');
    final channel = WebSocketChannel.connect(uri);
    _channel = channel;

    // IMPORTANT: each callback only clears _channel if it is STILL this same
    // channel. Without this check, the old socket's "done" event (which fires
    // late, after we reconnect) wiped out the brand-new socket, so send()
    // silently dropped every WebRTC answer and ICE candidate.
    channel.stream.listen(
      (data) {
        try {
          final json    = jsonDecode(data as String);
          final message = WsMessage.fromJson(json);
          _controller.add(message);
        } catch (e) {
          // ignore malformed messages
        }
      },
      onDone: () {
        debugPrint('[WebRTC] WS closed by server/network');
        if (identical(_channel, channel)) _channel = null;
      },
      onError: (e) {
        debugPrint('[WebRTC] WS error: $e');
        if (identical(_channel, channel)) _channel = null;
      },
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
    final old = _channel;
    _channel = null;
    await old?.sink.close();
  }
}