"""Biometric authentication helper for Android.

Uses FingerprintManagerCompat (androidx.core) which works with Kivy's plain
Activity (no FragmentActivity required). Falls back gracefully on devices
without fingerprint hardware or no enrolled fingerprints.

Requires in buildozer.spec:
    android.gradle_dependencies = androidx.core:core:1.9.0
    android.enable_androidx = True
    android.permissions = ...,USE_BIOMETRIC,USE_FINGERPRINT
"""
from __future__ import annotations


def biometric_available() -> bool:
    """Return True if device has enrolled fingerprints and hardware present."""
    try:
        from kivy.utils import platform
        if platform != "android":
            return False
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        FingerprintManagerCompat = autoclass(
            "androidx.core.hardware.fingerprint.FingerprintManagerCompat"
        )
        activity = PythonActivity.mActivity
        fm = FingerprintManagerCompat.from_(activity)
        return bool(fm.isHardwareDetected() and fm.hasEnrolledFingerprints())
    except Exception:
        return False


def prompt_biometric(on_success, on_failure):
    """Show a fingerprint prompt via FingerprintManagerCompat.

    Args:
        on_success: callable() called on successful authentication
        on_failure: callable(str) called on error or user cancellation
    """
    try:
        from kivy.utils import platform
        if platform != "android":
            on_failure("Biometric not available on this platform.")
            return

        from kivy.clock import Clock
        from jnius import autoclass, PythonJavaClass, java_method

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        FingerprintManagerCompat = autoclass(
            "androidx.core.hardware.fingerprint.FingerprintManagerCompat"
        )
        CancellationSignal = autoclass("androidx.core.os.CancellationSignal")

        activity = PythonActivity.mActivity
        fm = FingerprintManagerCompat.from_(activity)

        if not fm.isHardwareDetected():
            on_failure("No fingerprint hardware detected.")
            return
        if not fm.hasEnrolledFingerprints():
            on_failure("No fingerprints enrolled. Go to Settings to set up.")
            return

        cancel_signal = CancellationSignal()

        class _AuthCallback(PythonJavaClass):
            __javainterfaces__ = [
                "androidx/core/hardware/fingerprint/FingerprintManagerCompat$AuthenticationCallback"
            ]
            __javacontext__ = "app"

            @java_method("(ILjava/lang/CharSequence;)V")
            def onAuthenticationError(self, error_code, err_string):
                msg = str(err_string) if err_string else "Authentication error"
                Clock.schedule_once(lambda *_: on_failure(msg), 0)

            @java_method("(Landroidx/core/hardware/fingerprint/FingerprintManagerCompat$AuthenticationResult;)V")
            def onAuthenticationSucceeded(self, result):
                Clock.schedule_once(lambda *_: on_success(), 0)

            @java_method("()V")
            def onAuthenticationFailed(self):
                # Single failed scan - system shows feedback, stays open
                pass

            @java_method("(Ljava/lang/CharSequence;)V")
            def onAuthenticationHelp(self, help_string):
                pass

        callback = _AuthCallback()
        # authenticate(crypto, flags, cancel, callback, handler)
        fm.authenticate(None, 0, cancel_signal, callback, None)

    except Exception as exc:
        on_failure(f"Biometric not supported: {exc}")
