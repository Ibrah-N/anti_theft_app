// lib/presentation/screens/camera/fullscreen_camera_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/camera_model.dart';
import '../../../data/providers/camera_provider.dart';

/// Landscape, edge-to-edge view of the live stream. Reuses the renderer
/// owned by cameraProvider, so the existing WebRTC connection keeps
/// playing — nothing reconnects when you enter or leave.
class FullscreenCameraScreen extends ConsumerStatefulWidget {
  const FullscreenCameraScreen({super.key});

  @override
  ConsumerState<FullscreenCameraScreen> createState() =>
      _FullscreenCameraScreenState();
}

class _FullscreenCameraScreenState
    extends ConsumerState<FullscreenCameraScreen> {
  bool _controlsVisible = true;

  @override
  void initState() {
    super.initState();
    // main.dart locks the app to portrait — allow landscape only while
    // this screen is open, and hide the system bars.
    SystemChrome.setPreferredOrientations([
      DeviceOrientation.landscapeLeft,
      DeviceOrientation.landscapeRight,
    ]);
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
  }

  @override
  void dispose() {
    // Restore exactly what main.dart set up.
    SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp,
      DeviceOrientation.portraitDown,
    ]);
    SystemChrome.setEnabledSystemUIMode(
      SystemUiMode.manual,
      overlays: SystemUiOverlay.values,
    );
    super.dispose();
  }

  void _exit() => Navigator.of(context).maybePop();

  @override
  Widget build(BuildContext context) {
    final renderer = ref.watch(cameraProvider.notifier).remoteRenderer;

    // If the stream ends while we're fullscreen (device offline, session
    // timed out, connection failed) there's nothing left to show — leave
    // instead of sitting on a frozen frame.
    ref.listen<CameraModel>(cameraProvider, (previous, next) {
      if (next.status != CameraStatus.streaming) _exit();
    });

    return Scaffold(
      backgroundColor: Colors.black,
      body: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => setState(() => _controlsVisible = !_controlsVisible),
        child: Stack(
          fit: StackFit.expand,
          children: [
            // Contain (not Cover) so the whole frame is visible.
            RTCVideoView(
              renderer,
              objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitContain,
            ),
            AnimatedOpacity(
              opacity: _controlsVisible ? 1 : 0,
              duration: const Duration(milliseconds: 200),
              child: IgnorePointer(
                ignoring: !_controlsVisible,
                child: _Controls(onExit: _exit),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Controls extends StatelessWidget {
  final VoidCallback onExit;
  const _Controls({required this.onExit});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: AppColors.statusRed,
                borderRadius: BorderRadius.circular(6),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.circle, color: Colors.white, size: 8),
                  SizedBox(width: 5),
                  Text('LIVE',
                      style: TextStyle(
                          color: Colors.white,
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 1.2)),
                ],
              ),
            ),
            const Spacer(),
            Material(
              color: Colors.black54,
              shape: const CircleBorder(),
              child: IconButton(
                icon: const Icon(Icons.fullscreen_exit_rounded,
                    color: Colors.white),
                tooltip: 'Exit fullscreen',
                onPressed: onExit,
              ),
            ),
          ],
        ),
      ),
    );
  }
}