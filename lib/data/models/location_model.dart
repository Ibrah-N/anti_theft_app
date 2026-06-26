import 'package:latlong2/latlong.dart';

enum VehicleLocationStatus { parked, moving, idle, offline }

class LocationModel {
  final double latitude;
  final double longitude;
  final String address;
  final String city;
  final double distanceFromHomeKm;
  final VehicleLocationStatus status;
  final DateTime lastUpdated;

  const LocationModel({
    required this.latitude,
    required this.longitude,
    required this.address,
    required this.city,
    required this.distanceFromHomeKm,
    required this.status,
    required this.lastUpdated,
  });

  // Convenience getter for flutter_map
  LatLng get latLng => LatLng(latitude, longitude);

  String get statusLabel {
    switch (status) {
      case VehicleLocationStatus.parked:  return 'Parked';
      case VehicleLocationStatus.moving:  return 'Moving';
      case VehicleLocationStatus.idle:    return 'Idle';
      case VehicleLocationStatus.offline: return 'Offline';
    }
  }

  String get timeAgo {
    final diff = DateTime.now().difference(lastUpdated);
    if (diff.inSeconds < 60) return '${diff.inSeconds} sec ago';
    if (diff.inMinutes < 60) return '${diff.inMinutes} min ago';
    return '${diff.inHours} hr ago';
  }

  String get latFormatted =>
      '${latitude.abs().toStringAsFixed(4)}° ${latitude >= 0 ? "N" : "S"}';

  String get lngFormatted =>
      '${longitude.abs().toStringAsFixed(4)}° ${longitude >= 0 ? "E" : "W"}';

  // Step 2: replace mock() with GPS stream from FastAPI WebSocket
  static LocationModel mock() => LocationModel(
    latitude: 37.7749,
    longitude: -122.4194,
    address: '1284 Market St, San Francisco',
    city: 'San Francisco, CA',
    distanceFromHomeKm: 0.0,
    status: VehicleLocationStatus.parked,
    lastUpdated: DateTime.now().subtract(const Duration(minutes: 2)),
  );
}