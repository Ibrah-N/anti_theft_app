// lib/presentation/screens/map/map_screen.dart
// CHANGED: removed bottomNavigationBar + _navIndex — nav lives in HomeScreen now

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';

import '../../../core/constants/app_colors.dart';
import '../../../data/models/location_model.dart';
import '../../widgets/map/car_marker.dart';
import '../../widgets/map/coordinate_card.dart';
import '../../widgets/map/location_status_card.dart';
import '../../widgets/map/address_bar.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/providers/location_provider.dart';

import 'package:geolocator/geolocator.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../data/providers/user_location_provider.dart';
import 'package:latlong2/latlong.dart';


class MapScreen extends ConsumerStatefulWidget {
  const MapScreen({super.key});

  @override
  ConsumerState<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends ConsumerState<MapScreen> {
  bool _isTracking = false;


  late final MapController _mapController;

  @override
  void initState() {
    super.initState();
    _mapController = MapController();
  }

  @override
  void dispose() {
    _mapController.dispose();
    super.dispose();
  }

  void _onTrack() async {
    setState(() => _isTracking = !_isTracking);
    if (_isTracking) {
      // Request fresh GPS from device
      await ref.read(locationProvider.notifier).requestLocation();
      final location = ref.read(locationProvider).valueOrNull;
      if (location != null) {
        _mapController.move(location.latLng, 16.5);
      }
    }
  }

  Future<void> _onNavigate(LocationModel carLocation) async {
    // Start showing the user's own live position on the map
    ref.read(userLocationProvider.notifier).startTracking();

    // Open native Maps app for turn-by-turn directions to the car
    final uri = Uri.parse(
        'geo:${carLocation.latitude},${carLocation.longitude}?q=${carLocation.latitude},${carLocation.longitude}');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  @override
  Widget build(BuildContext context) {
    final locationAsync = ref.watch(locationProvider);
    final location      = locationAsync.valueOrNull;

    if (locationAsync.hasError) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Cannot reach server — check your connection',
                style: TextStyle(color: AppColors.statusRed)),
            const SizedBox(height: 12),
            TextButton(
              onPressed: () => ref.read(locationProvider.notifier).requestLocation(),
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (location == null) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: AppColors.primaryBlue),
            SizedBox(height: 12),
            Text('Fetching GPS location...',
                style: TextStyle(color: AppColors.textPrimary, fontSize: 14)),
          ],
        ),
      );
    }

    final loc = location;

    final userPosition = ref.watch(userLocationProvider).valueOrNull;

    double? distanceKm;
    if (userPosition != null) {
      distanceKm = Geolocator.distanceBetween(
            userPosition.latitude,
            userPosition.longitude,
            loc.latitude,
            loc.longitude,
          ) /
          1000;
    }

    return SafeArea(
      child: Column(
        children: [
          // ── Header ─────────────────────────────────────────────────────
          _buildHeader(loc),

          // ── Map fills remaining space ───────────────────────────────────
          Expanded(
            child: Stack(
              children: [
                ClipRRect(
                  borderRadius: const BorderRadius.only(
                    topLeft:  Radius.circular(20),
                    topRight: Radius.circular(20),
                  ),
                  child: FlutterMap(
                    mapController: _mapController,
                    options: MapOptions(
                      initialCenter: loc.latLng,
                      initialZoom: 16.5,
                      minZoom: 10,
                      maxZoom: 19,
                      interactionOptions: const InteractionOptions(
                        flags: InteractiveFlag.pinchZoom | InteractiveFlag.drag,
                      ),
                    ),
                    children: [
                      TileLayer(
                        urlTemplate:
                          'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                        subdomains: const ['a', 'b', 'c', 'd'],
                        userAgentPackageName: 'com.smartguard.app',
                        maxZoom: 20,
                      ),
                      CircleLayer(
                        circles: [
                          CircleMarker(
                            point: loc.latLng,
                            radius: 80,
                            useRadiusInMeter: true,
                            color: AppColors.accentBlue.withValues(alpha: 0.08),
                            borderColor: AppColors.accentBlue.withValues(alpha: 0.5),
                            borderStrokeWidth: 1.5,
                          ),
                        ],
                      ),
                      MarkerLayer(
                        markers: [
                          Marker(
                            point: loc.latLng,
                            width: 48,
                            height: 64,
                            alignment: Alignment.topCenter,
                            child: CarMarkerWidget(
                              isMoving: location.status ==
                                  VehicleLocationStatus.moving,
                            ),
                          ),
                          if (userPosition != null)
                            Marker(
                              point: LatLng(
                                  userPosition.latitude, userPosition.longitude),
                              width: 24,
                              height: 24,
                              child: Container(
                                decoration: BoxDecoration(
                                  color: AppColors.accentBlue,
                                  shape: BoxShape.circle,
                                  border: Border.all(
                                      color: Colors.white, width: 2),
                                ),
                              ),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
                Positioned(
                  top: 16, left: 16,
                  child: CoordinateCard(
                    latitude:  loc.latFormatted,
                    longitude: loc.lngFormatted,
                  ),
                ),
                Positioned(
                  top: 16, right: 16,
                  child: LocationStatusCard(location: loc),
                ),
                Positioned(
                  bottom: 0, left: 0, right: 0,
                  child: AddressBar(
                    location:   loc,
                    distanceKm: distanceKm,
                    onNavigate: () => _onNavigate(loc),
                  ),
                ),
              ],
              // ── Loading overlay when requesting GPS ───────────────
              
            ),
          ),
          if (locationAsync.isLoading)
                Container(
                  color: Colors.black.withValues(alpha: 0.4),
                  child: const Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        CircularProgressIndicator(color: AppColors.primaryBlue),
                        SizedBox(height: 12),
                        Text('Requesting GPS...',
                            style: TextStyle(
                                color: AppColors.textPrimary,
                                fontSize: 14)),
                      ],
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(LocationModel location) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('GPS Tracking',
                  style: TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 26,
                      fontWeight: FontWeight.w800)),
              const SizedBox(height: 3),
              Text(location.city,
                  style: const TextStyle(
                      color: AppColors.accentBlue, fontSize: 13)),
            ],
          ),
          GestureDetector(
            onTap: _onTrack,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
              decoration: BoxDecoration(
                color: _isTracking ? AppColors.primaryBlue : AppColors.cardBg,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: _isTracking
                      ? AppColors.primaryBlue
                      : AppColors.borderColor,
                ),
              ),
              child: Row(children: [
                Icon(Icons.navigation_rounded,
                    size: 15,
                    color: _isTracking
                        ? Colors.white
                        : AppColors.textSecondary),
                const SizedBox(width: 6),
                Text(
                  _isTracking ? 'Tracking' : 'Track',
                  style: TextStyle(
                      color: _isTracking
                          ? Colors.white
                          : AppColors.textSecondary,
                      fontSize: 13,
                      fontWeight: FontWeight.w600),
                ),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}