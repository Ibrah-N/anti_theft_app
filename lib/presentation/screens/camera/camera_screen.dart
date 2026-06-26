
import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/camera_model.dart';
import '../../widgets/camera/stream_viewer.dart';
import '../../widgets/camera/camera_control_row.dart';
import '../../widgets/camera/device_info_card.dart';

class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  CameraModel _camera = CameraModel.mock();
  bool _isRecording = false;

  // ── Stream control ─────────────────────────────────────────────────────────
  Future<void> _toggleStream() async {
    if (_camera.status == CameraStatus.streaming) {
      // Stop stream
      setState(() {
        _camera = _camera.copyWith(status: CameraStatus.offline, latency: '--');
        _isRecording = false;
      });
      return;
    }

    // Start: show connecting state
    setState(() => _camera = _camera.copyWith(status: CameraStatus.connecting));

    // TODO Step 2: replace with real API call to start ESP32-CAM stream
    await Future.delayed(const Duration(seconds: 2));

    setState(() => _camera = _camera.copyWith(
          status: CameraStatus.streaming,
          latency: '42 ms',
        ));
  }

  void _onSnapshot() {
    // TODO Step 2: send snapshot command to device
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text('Snapshot saved'),
        backgroundColor: AppColors.statusGreenBg,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }

  void _onRecord() {
    setState(() => _isRecording = !_isRecording);
    // TODO Step 2: send start/stop record command to device
  }

  // ── Build ───────────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    final bool isStreaming = _camera.status == CameraStatus.streaming;
    final bool isConnecting = _camera.status == CameraStatus.connecting;

    return Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 20, 16, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [

              // ── Header ────────────────────────────────────────────────────
              _buildHeader(),
              const SizedBox(height: 20),

              // ── Stream viewer ─────────────────────────────────────────────
              StreamViewer(status: _camera.status),
              const SizedBox(height: 16),

              // ── START / STOP STREAM button ────────────────────────────────
              _buildStreamButton(isStreaming, isConnecting),
              const SizedBox(height: 12),

              // ── Snapshot + Record row ─────────────────────────────────────
              CameraControlRow(
                status: _camera.status,
                isRecording: _isRecording,
                onSnapshot: _onSnapshot,
                onRecord: _onRecord,
              ),
              const SizedBox(height: 20),

              // ── Device info card ──────────────────────────────────────────
              DeviceInfoCard(camera: _camera),
            ],
          ),
        ),
      ),
    );
  }

  // ── Header widget ─────────────────────────────────────────────────────────
  Widget _buildHeader() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Camera',
                style: TextStyle(
                  color: AppColors.textPrimary,
                  fontSize: 28,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '${_camera.moduleId} · ${_camera.channelLabel}',
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),

        // Recording indicator — only shown when recording
        if (_isRecording)
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: AppColors.statusRedBg,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                  color: AppColors.statusRed.withOpacity(0.4)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 7,
                  height: 7,
                  decoration: const BoxDecoration(
                    color: AppColors.statusRed,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                const Text(
                  'REC',
                  style: TextStyle(
                    color: AppColors.statusRed,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1.0,
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  // ── Stream button ──────────────────────────────────────────────────────────
  Widget _buildStreamButton(bool isStreaming, bool isConnecting) {
    return SizedBox(
      width: double.infinity,
      height: 56,
      child: ElevatedButton.icon(
        onPressed: isConnecting ? null : _toggleStream,
        icon: isConnecting
            ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white,
                ),
              )
            : Icon(
                isStreaming
                    ? Icons.stop_circle_outlined
                    : Icons.photo_camera_outlined,
                size: 20,
              ),
        label: Text(
          isConnecting
              ? 'CONNECTING…'
              : isStreaming
                  ? 'STOP STREAM'
                  : 'START STREAM',
          style: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w700,
            letterSpacing: 1.2,
          ),
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
                ? BorderSide(color: AppColors.statusRed.withOpacity(0.4))
                : BorderSide.none,
          ),
          elevation: 0,
        ),
      ),
    );
  }
}