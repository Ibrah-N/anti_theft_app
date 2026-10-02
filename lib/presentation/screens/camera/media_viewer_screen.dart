// lib/presentation/screens/camera/media_viewer_screen.dart

import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';
import '../../../data/models/camera_media_model.dart';
import '../../../data/services/api_service.dart';

class MediaViewerScreen extends StatefulWidget {
  final CameraMediaModel media;
  const MediaViewerScreen({super.key, required this.media});

  @override
  State<MediaViewerScreen> createState() => _MediaViewerScreenState();
}

class _MediaViewerScreenState extends State<MediaViewerScreen> {
  VideoPlayerController? _controller;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    if (widget.media.mediaType == CameraMediaType.recording) {
      _initVideo();
    } else {
      _loading = false; // the image just loads directly via Image.network
    }
  }

  Future<void> _initVideo() async {
    try {
      final headers = await ApiService.instance.authHeaders();
      final url = ApiService.instance.mediaDownloadUrl(widget.media.id);
      final controller = VideoPlayerController.networkUrl(
        Uri.parse(url),
        httpHeaders: headers,
      );
      await controller.initialize();
      if (!mounted) return;
      setState(() {
        _controller = controller;
        _loading = false;
      });
      controller.play();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Could not load video';
        _loading = false;
      });
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        title: Text(widget.media.displayName, style: const TextStyle(fontSize: 14)),
      ),
      body: Center(child: _buildBody()),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const CircularProgressIndicator(color: Colors.white54);
    }
    if (_error != null) {
      return Text(_error!, style: const TextStyle(color: Colors.white70));
    }
    if (widget.media.mediaType == CameraMediaType.snapshot) {
      return FutureBuilder<Map<String, String>>(
        future: ApiService.instance.authHeaders(),
        builder: (context, snapshot) {
          if (!snapshot.hasData) {
            return const CircularProgressIndicator(color: Colors.white54);
          }
          return InteractiveViewer(
            child: Image.network(
              ApiService.instance.mediaDownloadUrl(widget.media.id),
              headers: snapshot.data,
              errorBuilder: (_, __, ___) =>
                  const Text('Could not load image', style: TextStyle(color: Colors.white70)),
            ),
          );
        },
      );
    }

    final controller = _controller!;
    return AspectRatio(
      aspectRatio: controller.value.aspectRatio,
      child: Stack(
        alignment: Alignment.center,
        children: [
          VideoPlayer(controller),
          GestureDetector(
            onTap: () => setState(() {
              controller.value.isPlaying ? controller.pause() : controller.play();
            }),
            child: AnimatedOpacity(
              opacity: controller.value.isPlaying ? 0 : 1,
              duration: const Duration(milliseconds: 200),
              child: Container(
                color: Colors.black26,
                child: const Icon(Icons.play_arrow_rounded, color: Colors.white, size: 64),
              ),
            ),
          ),
        ],
      ),
    );
  }
}