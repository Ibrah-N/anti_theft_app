// lib/data/providers/camera_media_provider.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/camera_media_model.dart';
import '../services/api_service.dart';

class CameraMediaNotifier extends StateNotifier<AsyncValue<List<CameraMediaModel>>> {
  CameraMediaNotifier() : super(const AsyncValue.loading()) {
    load();
  }

  Future<void> load() async {
    state = const AsyncValue.loading();
    try {
      final raw = await ApiService.instance.listCameraMedia();
      final items = raw.map(CameraMediaModel.fromJson).toList();
      state = AsyncValue.data(items);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> delete(int id) async {
    final current = state.valueOrNull;
    if (current == null) return;
    // Optimistic removal — reverts via a fresh load if the delete fails.
    state = AsyncValue.data(current.where((m) => m.id != id).toList());
    try {
      await ApiService.instance.deleteCameraMedia(id);
    } catch (e) {
      await load();
      rethrow;
    }
  }
}

final cameraMediaProvider =
    StateNotifierProvider<CameraMediaNotifier, AsyncValue<List<CameraMediaModel>>>(
  (ref) => CameraMediaNotifier(),
);