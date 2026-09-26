import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/camera_model.dart';
import '../../../data/providers/camera_provider.dart';
import '../../widgets/camera/stream_viewer.dart';
import '../../widgets/camera/camera_control_row.dart';
import '../../widgets/camera/device_info_card.dart';

class CameraScreen extends ConsumerStatefulWidget {
  final bool standalone;
  const CameraScreen({super.key, this.standalone = true});

  @override
  ConsumerState<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends ConsumerState<CameraScreen> {
  bool _isRecording = false;

  Future<void> _toggleStream(CameraModel camera) async {
    if (camera.status == CameraStatus.streaming ||
        camera.status == CameraStatus.connecting) {
      await ref.read(cameraProvider.notifier).stopStream();
      setState(() => _isRecording = false);
      return;
    }
    await ref.read(cameraProvider.notifier).startStream();
  }

  void _onSnapshot() {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: const Text('Snapshot saved'),
      backgroundColor: AppColors.statusGreenBg,
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
    ));
  }

  void _onRecord() => setState(() => _isRecording = !_isRecording);

  @override
  Widget build(BuildContext context) {
    final camera = ref.watch(cameraProvider);
    final renderer = ref.watch(cameraProvider.notifier).remoteRenderer;
    final bool isStreaming  = camera.status == CameraStatus.streaming;
    final bool isConnecting = camera.status == CameraStatus.connecting;

    final content = SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 20, 16, 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(camera),
            const SizedBox(height: 20),
            StreamViewer(status: camera.status, renderer: renderer),
            const SizedBox(height: 16),
            _buildStreamButton(camera, isStreaming, isConnecting),
            const SizedBox(height: 12),
            CameraControlRow(
              status: camera.status,
              isRecording: _isRecording,
              onSnapshot: _onSnapshot,
              onRecord: _onRecord,
            ),
            const SizedBox(height: 20),
            DeviceInfoCard(camera: camera),
          ],
        ),
      ),
    );

    if (widget.standalone) {
      return Scaffold(backgroundColor: AppColors.scaffoldBg, body: content);
    }
    return content;
  }

  Widget _buildHeader(CameraModel camera) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Camera',
                  style: TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 28,
                      fontWeight: FontWeight.w800)),
              const SizedBox(height: 4),
              Text('${camera.moduleId} · ${camera.channelLabel}',
                  style: const TextStyle(
                      color: AppColors.textSecondary, fontSize: 13)),
            ],
          ),
        ),
        if (_isRecording)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: AppColors.statusRedBg,
              borderRadius: BorderRadius.circular(20),
              border:
                  Border.all(color: AppColors.statusRed.withValues(alpha: 0.4)),
            ),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Container(
                  width: 7, height: 7,
                  decoration: const BoxDecoration(
                      color: AppColors.statusRed, shape: BoxShape.circle)),
              const SizedBox(width: 6),
              const Text('REC',
                  style: TextStyle(
                      color: AppColors.statusRed,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.0)),
            ]),
          ),
      ],
    );
  }

  Widget _buildStreamButton(CameraModel camera, bool isStreaming, bool isConnecting) {
    return SizedBox(
      width: double.infinity,
      height: 56,
      child: ElevatedButton.icon(
        onPressed: isConnecting ? null : () => _toggleStream(camera),
        icon: isConnecting
            ? const SizedBox(
                width: 18, height: 18,
                child: CircularProgressIndicator(
                    strokeWidth: 2, color: Colors.white))
            : Icon(isStreaming
                ? Icons.stop_circle_outlined
                : Icons.photo_camera_outlined,
                size: 20),
        label: Text(
          isConnecting ? 'CONNECTING…' : isStreaming ? 'STOP STREAM' : 'START STREAM',
          style: const TextStyle(
              fontSize: 15, fontWeight: FontWeight.w700, letterSpacing: 1.2),
        ),
        style: ElevatedButton.styleFrom(
          backgroundColor:
              isStreaming ? AppColors.statusRedBg : AppColors.primaryBlue,
          foregroundColor:
              isStreaming ? AppColors.statusRed : Colors.white,
          disabledBackgroundColor: AppColors.inputBg,
          disabledForegroundColor: AppColors.textMuted,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
            side: isStreaming
                ? BorderSide(color: AppColors.statusRed.withValues(alpha: 0.4))
                : BorderSide.none,
          ),
          elevation: 0,
        ),
      ),
    );
  }
}