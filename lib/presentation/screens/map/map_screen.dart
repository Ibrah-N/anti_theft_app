// lib/presentation/screens/map/map_screen.dart
// CHANGED: removed bottomNavigationBar + _navIndex — nav lives in HomeScreen now

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../../core/constants/app_colors.dart';
import '../../../data/models/location_model.dart';
import '../../widgets/map/car_marker.dart';
import '../../widgets/map/coordinate_card.dart';
import '../../widgets/map/location_status_card.dart';
import '../../widgets/map/address_bar.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  bool _isTracking = false;

  // Step 2: replace with stream from FastAPI WebSocket
  final LocationModel _location = LocationModel.mock();

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

  void _onTrack() {
    setState(() => _isTracking = !_isTracking);
    if (_isTracking) {
      _mapController.move(_location.latLng, 16.5);
    }
  }

  void _onNavigate() {
    // TODO Step 2: url_launcher → Google Maps / Apple Maps
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(
        children: [
          // ── Header ─────────────────────────────────────────────────────
          _buildHeader(),

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
                      initialCenter: _location.latLng,
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
                            point: _location.latLng,
                            radius: 80,
                            useRadiusInMeter: true,
                            color: AppColors.accentBlue.withOpacity(0.08),
                            borderColor: AppColors.accentBlue.withOpacity(0.5),
                            borderStrokeWidth: 1.5,
                          ),
                        ],
                      ),
                      MarkerLayer(
                        markers: [
                          Marker(
                            point: _location.latLng,
                            width: 48,
                            height: 64,
                            alignment: Alignment.topCenter,
                            child: CarMarkerWidget(
                              isMoving: _location.status ==
                                  VehicleLocationStatus.moving,
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
                    latitude:  _location.latFormatted,
                    longitude: _location.lngFormatted,
                  ),
                ),
                Positioned(
                  top: 16, right: 16,
                  child: LocationStatusCard(location: _location),
                ),
                Positioned(
                  bottom: 0, left: 0, right: 0,
                  child: AddressBar(
                    location:   _location,
                    onNavigate: _onNavigate,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
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
              Text(_location.city,
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