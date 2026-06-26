import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';
import '../../../data/models/location_model.dart';

class AddressBar extends StatelessWidget {
  final LocationModel location;
  final VoidCallback onNavigate;

  const AddressBar({
    super.key,
    required this.location,
    required this.onNavigate,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(12),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: AppColors.cardBg.withOpacity(0.96),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.borderColor, width: 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.4),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          // Target icon
          Container(
            width: 36, height: 36,
            decoration: BoxDecoration(
              color: AppColors.iconBlueBg,
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.my_location_rounded,
                color: AppColors.accentBlue, size: 18),
          ),
          const SizedBox(width: 12),

          // Address + distance
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(location.address,
                    style: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 14,
                        fontWeight: FontWeight.w700)),
                const SizedBox(height: 2),
                Text(
                  '${location.distanceFromHomeKm.toStringAsFixed(1)} km from home base',
                  style: const TextStyle(
                      color: AppColors.textSecondary, fontSize: 12),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),

          // Navigate button
          GestureDetector(
            onTap: onNavigate,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: AppColors.primaryBlue,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Text('Navigate',
                  style: TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w700)),
            ),
          ),
        ],
      ),
    );
  }
}