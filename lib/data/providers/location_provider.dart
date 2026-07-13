// lib/data/providers/location_provider.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/models/location_model.dart';
import '../services/api_service.dart';

class LocationNotifier extends StateNotifier<AsyncValue<LocationModel?>> {
  LocationNotifier() : super(const AsyncValue.data(null));

  // ── Request live GPS from device ──────────────────────────────────────────
  Future<void> requestLocation() async {
    state = const AsyncValue.loading();
    try {
      // Tell backend to ask device for GPS
      await ApiService.instance.requestGPS();

      // Wait briefly for device to respond + backend to save
      await Future.delayed(const Duration(seconds: 3));

      // Fetch the latest saved reading
      final data = await ApiService.instance.getLatestGPS();
      state      = AsyncValue.data(LocationModel.fromJson(data));
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }
}

final locationProvider =
    StateNotifierProvider<LocationNotifier, AsyncValue<LocationModel?>>(
  (ref) => LocationNotifier(),
);