// lib/data/models/camera_media_model.dart

enum CameraMediaType { snapshot, recording }

class CameraMediaModel {
  final int id;
  final int sequenceNumber;
  final CameraMediaType mediaType;
  final int fileSizeBytes;
  final double? durationSeconds;
  final DateTime createdAt;

  const CameraMediaModel({
    required this.id,
    required this.sequenceNumber,
    required this.mediaType,
    required this.fileSizeBytes,
    required this.durationSeconds,
    required this.createdAt,
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
      );

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