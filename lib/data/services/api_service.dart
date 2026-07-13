// lib/data/services/api_service.dart

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../core/constants/app_constants.dart';

class ApiService {
  ApiService._();
  static final ApiService instance = ApiService._();

  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  late final Dio _dio = Dio(
    BaseOptions(
      baseUrl:        AppConstants.apiUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
      headers: {'Content-Type': 'application/json'},
    ),
  )..interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        // Attach JWT token to every request automatically
        final token = await _storage.read(key: AppConstants.keyAccessToken);
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) {
        final status  = error.response?.statusCode;
        final detail  = error.response?.data?['detail'];

        String message;
        if (status == 401) {
          message = 'Invalid email or password';
        } else if (status == 422) {
          message = 'Please check your email and password';
        } else if (status == 403) {
          message = 'Account is disabled';
        } else if (status == 404) {
          message = 'Not found';
        } else if (status == 500) {
          message = 'Server error — try again later';
        } else if (error.type == DioExceptionType.connectionTimeout ||
                  error.type == DioExceptionType.receiveTimeout) {
          message = 'Connection timed out — check your network';
        } else if (error.type == DioExceptionType.connectionError) {
          message = 'Cannot reach server — check your connection';
        } else {
          message = detail?.toString() ?? 'Something went wrong';
        }

        return handler.reject(
          DioException(
            requestOptions: error.requestOptions,
            response:       error.response,
            error:          message,
            type:           error.type,
          ),
        );
      },
    ),
  );

  // ── Auth ───────────────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await _dio.post('/auth/login', data: {
      'email':    email,
      'password': password,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> register({
    required String email,
    required String fullName,
    required String password,
    String? phone,
  }) async {
    final response = await _dio.post('/auth/register', data: {
      'email':     email,
      'full_name': fullName,
      'password':  password,
      'phone': phone,
    });
    return response.data;
  }

  // ── Vehicle ────────────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> getVehicleStatus() async {
    final response = await _dio.get('/vehicle/status');
    return response.data;
  }

  Future<Map<String, dynamic>> controlEngine(bool state) async {
    final response = await _dio.post('/vehicle/engine', data: {'state': state});
    return response.data;
  }

  Future<Map<String, dynamic>> controlFuel(bool state) async {
    final response = await _dio.post('/vehicle/fuel', data: {'state': state});
    return response.data;
  }

  // ── Alerts ─────────────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> getAlerts({
    String?  category,
    bool     unreadOnly = false,
    int      limit      = 20,
    int      offset     = 0,
  }) async {
    final response = await _dio.get('/alerts/', queryParameters: {
      'category':    category,
      'unread_only': unreadOnly,
      'limit':  limit,
      'offset': offset,
    });
    return response.data;
  }

  Future<Map<String, dynamic>> markAlertRead(int alertId) async {
    final response = await _dio.patch('/alerts/$alertId/read');
    return response.data;
  }

  Future<Map<String, dynamic>> markAllAlertsRead() async {
    final response = await _dio.patch('/alerts/read-all');
    return response.data;
  }

  // ── GPS ────────────────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> requestGPS() async {
    final response = await _dio.post('/gps/request');
    return response.data;
  }

  Future<Map<String, dynamic>> getLatestGPS() async {
    final response = await _dio.get('/gps/latest');
    return response.data;
  }

  Future<Map<String, dynamic>> getGPSHistory({
    int limit  = 50,
    int offset = 0,
  }) async {
    final response = await _dio.get('/gps/history', queryParameters: {
      'limit':  limit,
      'offset': offset,
    });
    return response.data;
  }
}