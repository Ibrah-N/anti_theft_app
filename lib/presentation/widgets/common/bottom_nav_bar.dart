import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';

class SmartGuardBottomNav extends StatelessWidget {
  final int currentIndex;
  final ValueChanged<int> onTap;

  const SmartGuardBottomNav({
    super.key,
    required this.currentIndex,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.cardBg,
        border: Border(top: BorderSide(color: AppColors.borderColor, width: 1)),
      ),
      child: BottomNavigationBar(
        currentIndex: currentIndex,
        onTap: onTap,
        backgroundColor: Colors.transparent,
        elevation: 0,
        type: BottomNavigationBarType.fixed,
        selectedItemColor: AppColors.accentBlue,
        unselectedItemColor: AppColors.textMuted,
        selectedLabelStyle: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
        unselectedLabelStyle: const TextStyle(fontSize: 11),
        items: [
          const BottomNavigationBarItem(
            icon: Icon(Icons.home_rounded), label: 'Home'),
          const BottomNavigationBarItem(
            icon: Icon(Icons.directions_car_outlined), label: 'Vehicle'),
          const BottomNavigationBarItem(
            icon: Icon(Icons.location_on_outlined), label: 'Map'),
          const BottomNavigationBarItem(
            icon: Icon(Icons.camera_alt_outlined), label: 'Camera'),
          BottomNavigationBarItem(
            icon: Stack(clipBehavior: Clip.none, children: [
              const Icon(Icons.notifications_outlined),
              Positioned(
                right: -6, top: -4,
                child: Container(
                  padding: const EdgeInsets.all(3),
                  decoration: const BoxDecoration(
                    color: AppColors.statusRed,
                    shape: BoxShape.circle,
                  ),
                  child: const Text('3',
                      style: TextStyle(color: Colors.white, fontSize: 8,
                          fontWeight: FontWeight.bold)),
                ),
              ),
            ]),
            label: 'Alerts',
          ),
          const BottomNavigationBarItem(
            icon: Icon(Icons.tune_outlined), label: 'More'),
        ],
      ),
    );
  }
}