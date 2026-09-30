enum CameraStatus { offline, connecting, streaming }

class CameraModel {
  final String moduleId;
  final String channelLabel;
  final String resolution;
  final String nightMode;
  final String latency;        // "--" when offline
  final CameraStatus status;
  final String? streamUrl;     // null until backend provides it

  const CameraModel({
    required this.moduleId,
    required this.channelLabel,
    required this.resolution,
    required this.nightMode,
    required this.latency,
    required this.status,
    this.streamUrl,
  });

  /// Resolution now comes from the real video track once frames arrive
  /// (see camera_provider's onResize handler). Night mode has no real
  /// source yet — no firmware exists to report it — so it stays "—"
  /// rather than showing a fabricated capability.
  factory CameraModel.mock() => const CameraModel(
        moduleId:     'ESP32-P4',
        channelLabel: 'Channel 01',
        resolution:   '--',
        nightMode:    '—',
        latency:      '--',
        status:       CameraStatus.offline,
        streamUrl:    null,
      );

  CameraModel copyWith({
    String?       moduleId,
    String?       channelLabel,
    String?       resolution,
    String?       nightMode,
    String?       latency,
    CameraStatus? status,
    String?       streamUrl,
  }) =>
      CameraModel(
        moduleId:     moduleId     ?? this.moduleId,
        channelLabel: channelLabel ?? this.channelLabel,
        resolution:   resolution   ?? this.resolution,
        nightMode:    nightMode    ?? this.nightMode,
        latency:      latency      ?? this.latency,
        status:       status       ?? this.status,
        streamUrl:    streamUrl    ?? this.streamUrl,
      );
}