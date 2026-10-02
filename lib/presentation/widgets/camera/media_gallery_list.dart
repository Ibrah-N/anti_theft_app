// lib/presentation/widgets/camera/media_gallery_list.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/camera_media_model.dart';

class MediaGalleryList extends StatelessWidget {
  final AsyncValue<List<CameraMediaModel>> state;
  final void Function(CameraMediaModel) onOpen;
  final void Function(CameraMediaModel) onDownload;
  final void Function(CameraMediaModel) onDelete;

  const MediaGalleryList({
    super.key,
    required this.state,
    required this.onOpen,
    required this.onDownload,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('SAVED MEDIA',
            style: TextStyle(
                color: AppColors.labelColor,
                fontSize: 11,
                fontWeight: FontWeight.w600,
                letterSpacing: 1.5)),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: AppColors.cardBg,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              const Icon(Icons.info_outline_rounded, size: 15, color: AppColors.textMuted),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Snapshots and recordings are automatically deleted after 30 days.',
                  style: const TextStyle(color: AppColors.textMuted, fontSize: 11.5),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        state.when(
          loading: () => const Padding(
            padding: EdgeInsets.symmetric(vertical: 24),
            child: Center(child: CircularProgressIndicator()),
          ),
          error: (e, _) => const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: Text('Could not load media', style: TextStyle(color: AppColors.textMuted)),
          ),
          data: (items) {
            if (items.isEmpty) {
              return const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Center(
                  child: Text('No snapshots or recordings yet',
                      style: TextStyle(color: AppColors.textMuted)),
                ),
              );
            }
            return Column(
              children: items
                  .map((m) => _MediaTile(
                        media: m,
                        onOpen: () => onOpen(m),
                        onDownload: () => onDownload(m),
                        onDelete: () => onDelete(m),
                      ))
                  .toList(),
            );
          },
        ),
      ],
    );
  }
}

class _MediaTile extends StatelessWidget {
  final CameraMediaModel media;
  final VoidCallback onOpen;
  final VoidCallback onDownload;
  final VoidCallback onDelete;

  const _MediaTile({
    required this.media,
    required this.onOpen,
    required this.onDownload,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final isVideo = media.mediaType == CameraMediaType.recording;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.cardBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.borderColor, width: 1),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: AppColors.iconBlueBg,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(
              isVideo ? Icons.videocam_rounded : Icons.photo_camera_rounded,
              color: AppColors.accentBlue,
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(media.displayName,
                    style: const TextStyle(
                        color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                const SizedBox(height: 2),
                Text(
                  isVideo ? '${media.durationLabel} · ${media.fileSizeLabel}' : media.fileSizeLabel,
                  style: const TextStyle(color: AppColors.textMuted, fontSize: 11.5),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.open_in_full_rounded, size: 18),
            color: AppColors.textSecondary,
            onPressed: onOpen,
            tooltip: 'Open',
          ),
          IconButton(
            icon: const Icon(Icons.download_rounded, size: 18),
            color: AppColors.textSecondary,
            onPressed: onDownload,
            tooltip: 'Download',
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline_rounded, size: 18),
            color: AppColors.statusRed,
            onPressed: onDelete,
            tooltip: 'Delete',
          ),
        ],
      ),
    );
  }
}