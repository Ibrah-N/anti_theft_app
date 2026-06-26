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

  /// Mock — swap for real data in Step 2
  factory CameraModel.mock() => const CameraModel(
        moduleId:     'ESP32-CAM',
        channelLabel: 'Channel 01',
        resolution:   '720p HD',
        nightMode:    'Auto IR',
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