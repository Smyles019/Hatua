import 'package:google_sign_in/google_sign_in.dart';

/// OAuth "Web application" client ID. The backend checks Google ID tokens against it
/// (GOOGLE_CLIENT_IDS in backend/.env). A client ID is public, not a secret.
/// Override with --dart-define=GOOGLE_SERVER_CLIENT_ID=...
const googleServerClientId = String.fromEnvironment(
  'GOOGLE_SERVER_CLIENT_ID',
  defaultValue: '973454711610-50v84nus43ic19nb08dies3bf8f3vqmq.apps.googleusercontent.com',
);

/// The Google account chosen on the phone, and the ID token to send to the backend.
class GoogleIdToken {
  GoogleIdToken(this.idToken, this.name, this.email);
  final String idToken;
  final String name;
  final String email;
}

/// Thrown when the person closes the Google account picker. Not an error to show.
class GoogleSignInCancelled implements Exception {}

class GoogleAuth {
  GoogleAuth._();

  static bool _initialised = false;

  static Future<void> _init() async {
    if (_initialised) return;
    await GoogleSignIn.instance.initialize(serverClientId: googleServerClientId);
    _initialised = true;
  }

  /// Shows Google's account picker and returns an ID token.
  static Future<GoogleIdToken> pickAccount() async {
    await _init();
    final GoogleSignInAccount account;
    try {
      account = await GoogleSignIn.instance.authenticate();
    } on GoogleSignInException catch (e) {
      if (e.code == GoogleSignInExceptionCode.canceled ||
          e.code == GoogleSignInExceptionCode.interrupted) {
        throw GoogleSignInCancelled();
      }
      throw Exception('Google sign-in did not work. Please try again or use your phone number.');
    }
    final idToken = account.authentication.idToken;
    if (idToken == null) {
      throw Exception('Google sign-in did not work. Please try again or use your phone number.');
    }
    return GoogleIdToken(idToken, account.displayName ?? account.email, account.email);
  }

  /// Forgets the chosen Google account on this phone, so the picker shows next time.
  static Future<void> signOut() async {
    if (!_initialised) return;
    try {
      await GoogleSignIn.instance.signOut();
    } catch (_) {
      // Nothing to undo if Google had no account signed in.
    }
  }
}
