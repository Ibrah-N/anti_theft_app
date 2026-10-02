// lib/data/providers/camera_provider.dart

import 'dart:async';
import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:path_provider/path_provider.dart';
import '../models/camera_model.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';

// The app is the WebRTC "answerer": the device sends its offer first
// (relayed in via the backend), we answer, then ICE candidates trickle
// both ways until the connection actually establishes.
class CameraNotifier extends StateNotifier<CameraModel> {
  final Ref ref;
  CameraNotifier(this.ref) : super(CameraModel.mock()) {
    _wsSub = WebSocketService.instance.messages.listen(_onWsMessage);
  }

  RTCPeerConnection? _pc;
  final RTCVideoRenderer remoteRenderer = RTCVideoRenderer();
  bool _rendererInitialized = false;
  String? _callId;
  StreamSubscription<WsMessage>? _wsSub;
  Timer? _sessionTimeout;

  // If the connection drops before ever reaching "connected" (a transient
  // network path failure, common over flaky Wi-Fi/emulator NAT), retry the
  // whole session exactly once automatically before giving up and showing
  // "offline" to the user.
  bool _connectedOnce = false;
  bool _autoRetried = false;

  // The actual remote video track — captureFrame() and MediaRecorder both
  // need this directly; the renderer alone only knows how to paint pixels.
  MediaStreamTrack? _remoteVideoTrack;

  MediaRecorder? _recorder;
  String? _recordingPath;
  DateTime? _recordingStartedAt;
  bool get isRecording => _recorder != null;

  Future<void> _ensureRenderer() async {
    if (!_rendererInitialized) {
      await remoteRenderer.initialize();
      remoteRenderer.onResize = () {
        final w = remoteRenderer.videoWidth;
        final h = remoteRenderer.videoHeight;
        if (w > 0 && h > 0) {
          state = state.copyWith(resolution: '${w}x$h');
        }
      };
      _rendererInitialized = true;
    }
  }

  Future<void> startStream({bool isRetry = false}) async {
    if (state.status != CameraStatus.offline) return;
    if (!isRetry) _autoRetried = false; // fresh budget for a new user-initiated attempt
    _connectedOnce = false;
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
          _remoteVideoTrack = event.track;
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
          _connectedOnce = true;
          state = state.copyWith(status: CameraStatus.streaming, latency: 'live');
        } else if (connState == RTCPeerConnectionState.RTCPeerConnectionStateFailed ||
                   connState == RTCPeerConnectionState.RTCPeerConnectionStateClosed) {
          final shouldRetry = !_connectedOnce && !_autoRetried;
          _teardown();
          if (shouldRetry) {
            _autoRetried = true;
            Future.delayed(const Duration(milliseconds: 600), () => startStream(isRetry: true));
          }
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

    Future<void> takeSnapshot() async {
    final track = _remoteVideoTrack;
    if (state.status != CameraStatus.streaming || track == null) {
      throw Exception('No active stream to capture');
    }
    final bytes = (await track.captureFrame()).asUint8List();
    await ApiService.instance.uploadSnapshot(bytes);
  }

  Future<void> startRecording() async {
    final track = _remoteVideoTrack;
    if (state.status != CameraStatus.streaming || track == null) {
      throw Exception('No active stream to record');
    }
    if (_recorder != null) return; // already recording

    final tempDir = await getTemporaryDirectory();
    final path =
        '${tempDir.path}/vigilx_${DateTime.now().millisecondsSinceEpoch}.mp4';

    // albumName: null — write only to our own temp path, don't also save
    // a copy into the device's photo gallery.
    final recorder = MediaRecorder(albumName: null);
    await recorder.start(path, videoTrack: track);

    _recorder = recorder;
    _recordingPath = path;
    _recordingStartedAt = DateTime.now();
  }

  Future<void> stopRecording() async {
    final recorder = _recorder;
    final path = _recordingPath;
    final startedAt = _recordingStartedAt;
    _recorder = null;
    _recordingPath = null;
    _recordingStartedAt = null;

    if (recorder == null || path == null) return;

    try {
      await recorder.stop();
      final file = File(path);
      final bytes = await file.readAsBytes();
      final duration = startedAt == null
          ? 0.0
          : DateTime.now().difference(startedAt).inMilliseconds / 1000.0;

      await ApiService.instance.uploadRecording(bytes, duration);
      await file.delete();
    } catch (e) {
      // Best-effort cleanup of the local file even if the upload failed —
      // no point leaving a half-finished recording sitting in temp storage.
      try {
        await File(path).delete();
      } catch (_) {}
      rethrow;
    }
  }

  Future<void> _teardown() async {
    _sessionTimeout?.cancel();
    _sessionTimeout = null;

    // A dropped connection mid-recording shouldn't leave a dangling
    // recorder/file behind — best-effort stop, ignore any upload failure
    // since the connection is already gone anyway.
    if (_recorder != null) {
      try {
        await stopRecording();
      } catch (_) {}
    }

    await _pc?.close();
    _pc = null;
    _callId = null;
    _remoteVideoTrack = null;
    remoteRenderer.srcObject = null;
    state = state.copyWith(
      status: CameraStatus.offline,
      latency: '--',
      resolution: '--',
    );
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