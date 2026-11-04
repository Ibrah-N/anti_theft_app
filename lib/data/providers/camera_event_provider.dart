// lib/data/providers/camera_event_provider.dart
//
// What the camera is doing RIGHT NOW as far as event recording goes:
// idle / recording / uploading / streaming. Fed by:
//   • GET /vehicle/camera/state            (once, when this provider is created)
//   • WebSocket "camera_state" messages    (live changes)
//   • WebSocket "clip_ready" messages      (a finished event clip is in the gallery)

import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../services/websocket_service.dart';
import 'camera_media_provider.dart';

class CameraEventState {
  /// "idle" | "recording" | "uploading" | "streaming"
  final String state;
  final String? clipId;
  final String? reason;
  final double? elapsedSeconds;
  final int? segmentsUploaded;
  final int? segmentsTotal;

  /// Bumps every time a new event clip lands in the gallery, so screens can
  /// react once (e.g. show a "saved" message) with ref.listen.
  final int clipReadyCount;
  final int? lastClipMediaId;

  const CameraEventState({
    this.state = 'idle',
    this.clipId,
    this.reason,
    this.elapsedSeconds,
    this.segmentsUploaded,
    this.segmentsTotal,
    this.clipReadyCount = 0,
    this.lastClipMediaId,
  });

  bool get isRecording => state == 'recording';
  bool get isUploading => state == 'uploading';

  /// "door_opened" -> "Door opened"
  String? get reasonLabel {
    final r = reason;
    if (r == null || r.isEmpty) return null;
    final spaced = r.replaceAll('_', ' ');
    return spaced[0].toUpperCase() + spaced.substring(1);
  }

  CameraEventState copyWithReport(Map<String, dynamic> j) => CameraEventState(
        state:            (j['state'] as String?) ?? 'idle',
        clipId:           j['clip_id'] as String?,
        reason:           j['reason'] as String?,
        elapsedSeconds:   (j['elapsed_s'] as num?)?.toDouble(),
        segmentsUploaded: j['segments_uploaded'] as int?,
        segmentsTotal:    j['segments_total'] as int?,
        clipReadyCount:   clipReadyCount,
        lastClipMediaId:  lastClipMediaId,
      );

  CameraEventState withClipReady(int? mediaId) => CameraEventState(
        state:            state,
        clipId:           clipId,
        reason:           reason,
        elapsedSeconds:   elapsedSeconds,
        segmentsUploaded: segmentsUploaded,
        segmentsTotal:    segmentsTotal,
        clipReadyCount:   clipReadyCount + 1,
        lastClipMediaId:  mediaId,
      );
}

class CameraEventNotifier extends StateNotifier<CameraEventState> {
  final Ref ref;
  StreamSubscription<WsMessage>? _sub;

  CameraEventNotifier(this.ref) : super(const CameraEventState()) {
    _sub = WebSocketService.instance.messages.listen(_onWsMessage);
    _loadInitial();
  }

  Future<void> _loadInitial() async {
    try {
      final data = await ApiService.instance.getCameraState();
      final camera = data['camera'];
      if (camera is Map) {
        state = state.copyWithReport(Map<String, dynamic>.from(camera));
      }
    } catch (e) {
      debugPrint('[CameraEvent] initial state load failed: $e');
    }
  }

  void _onWsMessage(WsMessage message) {
    switch (message.type) {
      case WsMessageType.cameraState:
        state = state.copyWithReport(message.payload);
        break;
      case WsMessageType.clipReady:
        state = state.withClipReady(message.payload['media_id'] as int?);
        // Refresh the gallery quietly (no spinner) so the new clip just appears.
        ref.read(cameraMediaProvider.notifier).refresh();
        break;
      default:
        break;
    }
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}

final cameraEventProvider =
    StateNotifierProvider<CameraEventNotifier, CameraEventState>(
  (ref) => CameraEventNotifier(ref),
);