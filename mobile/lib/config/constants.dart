/// App-wide constants for the Cognimap client.
library;

class AppConstants {
  AppConstants._();

  // ── API ───────────────────────────────────────────────────
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8002',
  );

  // ── Polling / Timing ─────────────────────────────────────
  static const Duration pollIntervalInitial = Duration(milliseconds: 1500);
  static const Duration pollIntervalMax = Duration(seconds: 8);
  static const double pollBackoffMultiplier = 1.5;

  // ── Session cap ──────────────────────────────────────────
  static const int maxActiveSessions = 5;

  // ── Rate limit ───────────────────────────────────────────
  static const int writeRateLimitPerMinute = 30;

  // ── Token keys ───────────────────────────────────────────
  static const String accessTokenKey = 'cognimap_access_token';
  static const String refreshTokenKey = 'cognimap_refresh_token';
}
