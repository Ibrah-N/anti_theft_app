import 'package:flutter/material.dart';
import '../../../core/constants/app_colors.dart';

/// A tappable control button used for door lock, mirror fold, engine start,
/// and AC controls. Shows a spinner and disables itself while [pending] is
/// true (i.e. waiting on a device ACK — see PendingCommandsNotifier).
class ControlButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool active;   // true = highlighted (e.g. locked, folded, on)
  final bool pending;
  final VoidCallback? onTap;

  const ControlButton({
    super.key,
    required this.icon,
    required this.label,
    required this.active,
    required this.pending,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final Color fg = active ? AppColors.accentBlue : AppColors.textSecondary;
    final Color bg = active ? AppColors.iconBlueBg : AppColors.cardBg;

    return Opacity(
      opacity: pending ? 0.6 : 1.0,
      child: Material(
        color: bg,
        borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: pending ? null : onTap,
          child: Container(
            height: 52,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppColors.borderColor, width: 1),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                if (pending)
                  SizedBox(
                    width: 14, height: 14,
                    child: CircularProgressIndicator(strokeWidth: 2, color: fg),
                  )
                else
                  Icon(icon, color: fg, size: 18),
                const SizedBox(width: 8),
                Flexible(
                  child: Text(
                    label,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: fg,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
