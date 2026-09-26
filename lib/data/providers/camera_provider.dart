// lib/data/providers/camera_provider.dart

import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import '../models/camera_model.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';

// The app is the WebRTC "answerer": the device sends its offer first
// (relayed in via the backend), we answer, then ICE candidates trickle
// both ways until the connection actually establishes.
class CameraNotifier extends StateNotifier<CameraModel> {
  final Ref ref;
  CameraNotifier(this.ref) : super(CameraModel.mock()) {
    _wsSub = WebSocketService.instance.messages?.listen(_onWsMessage);
  }

  RTCPeerConnection? _pc;
  final RTCVideoRenderer remoteRenderer = RTCVideoRenderer();
  bool _rendererInitialized = false;
  String? _callId;
  StreamSubscription<WsMessage>? _wsSub;
  Timer? _sessionTimeout;

  Future<void> _ensureRenderer() async {
    if (!_rendererInitialized) {
      await remoteRenderer.initialize();
      _rendererInitialized = true;
    }
  }

  Future<void> startStream() async {
    if (state.status != CameraStatus.offline) return;
    await _ensureRenderer();
    state = state.copyWith(status: CameraStatus.connecting, latency: '--');

    try {
      final response = await ApiService.instance.startCamera();
      _callId = response['call_id'] as String;
      final iceServers = (response['ice_servers'] as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();

      _pc = await createPeerConnection({'iceServers': iceServers});

      _pc!.onTrack = (RTCTrackEvent event) {
        if (event.track.kind == 'video' && event.streams.isNotEmpty) {
          remoteRenderer.srcObject = event.streams.first;
        }
      };

      _pc!.onIceCandidate = (RTCIceCandidate candidate) {
        final id = _callId;
        if (id == null) return;
        WebSocketService.instance.send({
          'type': 'webrtc_ice',
          'payload': {
            'call_id':       id,
            'candidate':     candidate.candidate,
            'sdpMid':        candidate.sdpMid,
            'sdpMLineIndex': candidate.sdpMLineIndex,
          },
        });
      };

      _pc!.onConnectionState = (RTCPeerConnectionState connState) {
        if (connState == RTCPeerConnectionState.RTCPeerConnectionStateConnected) {
          state = state.copyWith(status: CameraStatus.streaming, latency: 'live');
        } else if (connState == RTCPeerConnectionState.RTCPeerConnectionStateFailed ||
                   connState == RTCPeerConnectionState.RTCPeerConnectionStateClosed) {
          _teardown();
        }
      };

      // If the device never answers (offline, etc.), give up rather than
      // sit on "Connecting…" forever.
      _sessionTimeout = Timer(const Duration(seconds: 15), () {
        if (state.status == CameraStatus.connecting) stopStream();
      });
    } catch (e) {
      state = state.copyWith(status: CameraStatus.offline);
      rethrow;
    }
  }

  Future<void> _onWsMessage(WsMessage message) async {
    if (_pc == null || _callId == null) return;
    if (message.payload['call_id'] != _callId) return; // stale/foreign session

    switch (message.type) {
      case WsMessageType.webrtcOffer:
        _sessionTimeout?.cancel();
        final sdp = message.payload['sdp'] as String;
        await _pc!.setRemoteDescription(RTCSessionDescription(sdp, 'offer'));
        final answer = await _pc!.createAnswer();
        await _pc!.setLocalDescription(answer);
        WebSocketService.instance.send({
          'type': 'webrtc_answer',
          'payload': {'call_id': _callId, 'sdp': answer.sdp},
        });
        break;

      case WsMessageType.webrtcIce:
        await _pc!.addCandidate(RTCIceCandidate(
          message.payload['candidate'] as String?,
          message.payload['sdpMid'] as String?,
          message.payload['sdpMLineIndex'] as int?,
        ));
        break;

      default:
        break;
    }
  }

  Future<void> stopStream() async {
    if (_callId != null) {
      try {
        await ApiService.instance.stopCamera();
      } catch (_) {
        // Best-effort — tear down locally regardless of whether this reaches the server.
      }
    }
    await _teardown();
  }

  Future<void> _teardown() async {
    _sessionTimeout?.cancel();
    _sessionTimeout = null;
    await _pc?.close();
    _pc = null;
    _callId = null;
    remoteRenderer.srcObject = null;
    state = state.copyWith(status: CameraStatus.offline, latency: '--');
  }

  @override
  void dispose() {
    _wsSub?.cancel();
    _pc?.close();
    if (_rendererInitialized) remoteRenderer.dispose();
    super.dispose();
  }
}

final cameraProvider = StateNotifierProvider<CameraNotifier, CameraModel>(
  (ref) => CameraNotifier(ref),
);