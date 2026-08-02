import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/constants/app_colors.dart';
import 'data/providers/auth_provider.dart';
import 'presentation/screens/auth/login_screen.dart';
import 'presentation/screens/home/home_screen.dart';
import 'data/services/notification_service.dart';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import 'package:firebase_messaging/firebase_messaging.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Firebase.initializeApp();
  await NotificationService.instance.init();

  // Request FCM permission and print the device token for testing
  final fcmPermission = await FirebaseMessaging.instance.requestPermission();
  // print('FCM permission status: ${fcmPermission.authorizationStatus}');

  final fcmToken = await FirebaseMessaging.instance.getToken();
  // print('FCM TOKEN: $fcmToken');

  SystemChrome.setPreferredOrientations([
  DeviceOrientation.portraitUp,
  DeviceOrientation.portraitDown,
 ]);

  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor:          Colors.transparent,
    statusBarIconBrightness: Brightness.light,
    statusBarBrightness:     Brightness.dark,
  ));

  runApp(
    // ProviderScope is required by Riverpod — wraps the entire app
    const ProviderScope(
      child: SmartGuardApp(),
    ),
  );
}

class SmartGuardApp extends ConsumerWidget {
  const SmartGuardApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authStatus = ref.watch(authProvider);

    return MaterialApp(
      title:                    'SmartGuard',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        scaffoldBackgroundColor: AppColors.scaffoldBg,
        colorScheme: ColorScheme.dark(
          primary:   AppColors.primaryBlue,
          secondary: AppColors.accentBlue,
          surface:   AppColors.cardBg,
        ),
        fontFamily: 'SF Pro Display',
      ),
      // ── Auth-based routing ─────────────────────────────────────────────────
      home: switch (authStatus) {
        AuthStatus.unknown         => const _SplashScreen(),
        AuthStatus.authenticated   => const HomeScreen(),
        AuthStatus.unauthenticated => const LoginScreen(),
      },
    );
  }
}

// ── Splash — shown for ~1 second while checking stored token ──────────────────
class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      backgroundColor: AppColors.scaffoldBg,
      body: Center(
        child: CircularProgressIndicator(
          color: AppColors.primaryBlue,
        ),
      ),
    );
  }
}