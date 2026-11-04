// lib/data/models/camera_media_model.dart

enum CameraMediaType { snapshot, recording }

/// manual = saved by the user from the stream; event = recorded by the camera
/// itself after a suspicious event.
enum CameraMediaSource { manual, event }

class CameraMediaModel {
  final int id;
  final int sequenceNumber;
  final CameraMediaType mediaType;
  final int fileSizeBytes;
  final double? durationSeconds;
  final DateTime createdAt;
  final CameraMediaSource source;
  final String? triggerReason;

  const CameraMediaModel({
    required this.id,
    required this.sequenceNumber,
    required this.mediaType,
    required this.fileSizeBytes,
    required this.durationSeconds,
    required this.createdAt,
    this.source = CameraMediaSource.manual,
    this.triggerReason,
  });

  factory CameraMediaModel.fromJson(Map<String, dynamic> json) => CameraMediaModel(
        id:              json['id'] as int,
        sequenceNumber:  json['sequence_number'] as int,
        mediaType:       json['media_type'] == 'recording'
            ? CameraMediaType.recording
            : CameraMediaType.snapshot,
        fileSizeBytes:   json['file_size_bytes'] as int,
        durationSeconds: (json['duration_seconds'] as num?)?.toDouble(),
        createdAt:       DateTime.parse(json['created_at'] as String).toLocal(),
        source:          json['source'] == 'event'
            ? CameraMediaSource.event
            : CameraMediaSource.manual,
        triggerReason:   json['trigger_reason'] as String?,
      );

  bool get isEvent => source == CameraMediaSource.event;

  /// "door_opened" -> "Door opened"; null when there is no reason.
  String? get triggerReasonLabel {
    final r = triggerReason;
    if (r == null || r.isEmpty) return null;
    final spaced = r.replaceAll('_', ' ');
    return spaced[0].toUpperCase() + spaced.substring(1);
  }

  /// "snap_3_date_01_10_26_time_18_45" / "vid_1_date_01_10_26_time_06_54"
  String get displayName {
    String two(int n) => n.toString().padLeft(2, '0');
    final prefix = mediaType == CameraMediaType.recording ? 'vid' : 'snap';
    final d = createdAt;
    final date = '${two(d.day)}_${two(d.month)}_${two(d.year % 100)}';
    final time = '${two(d.hour)}_${two(d.minute)}';
    return '${prefix}_${sequenceNumber}_date_${date}_time_$time';
  }

  String get fileSizeLabel {
    if (fileSizeBytes < 1024) return '$fileSizeBytes B';
    if (fileSizeBytes < 1024 * 1024) return '${(fileSizeBytes / 1024).toStringAsFixed(0)} KB';
    return '${(fileSizeBytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  String get durationLabel {
    if (durationSeconds == null) return '';
    final total = durationSeconds!.round();
    final m = total ~/ 60;
    final s = total % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }
}