// lib/data/providers/user_location_provider.dart

import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import '../services/location_service.dart';

class UserLocationNotifier extends StateNotifier<AsyncValue<Position?>> {
  UserLocationNotifier() : super(const AsyncValue.data(null));

  StreamSubscription<Position>? _sub;
  bool isTracking = false;

  Future<void> startTracking() async {
    final granted = await LocationService.instance.ensurePermission();
    if (!granted) {
      state = AsyncValue.error(
          'Location permission denied', StackTrace.current);
      return;
    }
    isTracking = true;
    state = const AsyncValue.loading();
    _sub?.cancel();
    _sub = LocationService.instance.positionStream().listen(
      (position) => state = AsyncValue.data(position),
      onError: (e, st) => state = AsyncValue.error(e, st),
    );
  }

  void stopTracking() {
    isTracking = false;
    _sub?.cancel();
    _sub = null;
    state = const AsyncValue.data(null);
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}

final userLocationProvider =
    StateNotifierProvider<UserLocationNotifier, AsyncValue<Position?>>(
  (ref) => UserLocationNotifier(),
);