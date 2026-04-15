"""Biometric authentication helper - Android BiometricPrompt via Pyjnius.

On non-Android platforms always returns unavailable.
Requires in buildozer.spec:
    android.gradle_dependencies = androidx.biometric:biometric:1.1.0
    android.enable_androidx = True
    android.permissions = ...,USE_BIOMETRIC,USE_FINGERPRINT
"""
from __future__ import annotations


def biometric_available() -> bool:
    """Return True if device has enrolled biometric credentials ready to use.

    Note: even if this returns True, the BiometricPrompt may fail because
    Kivy's PythonActivity is not a FragmentActivity. The prompt_biometric
    function handles that failure gracefully.
    """
    try:
        from kivy.utils import platform
        if platform != "android":
            return False
        from jnius import autoclass
        PythonActivity   = autoclass("org.kivy.android.PythonActivity")
        BiometricManager = autoclass("androidx.biometric.BiometricManager")
        bm   = BiometricManager.from_(PythonActivity.mActivity)
        WEAK = BiometricManager.Authenticators.BIOMETRIC_WEAK
        return bm.canAuthenticate(WEAK) == BiometricManager.BIOMETRIC_SUCCESS
    except Exception:
        return False


def prompt_biometric(on_success, on_failure):
    """Show Android biometric prompt asynchronously.

    Args:
        on_success: callable() - called via Kivy Clock on successful auth
        on_failure: callable(str) - called on error or user cancellation
    """
    try:
        from kivy.utils import platform
        if platform != "android":
            on_failure("Biometric not available on this platform.")
            return

        from kivy.clock import Clock
        from jnius import autoclass, PythonJavaClass, java_method

        PythonActivity  = autoclass("org.kivy.android.PythonActivity")
        Executors       = autoclass("java.util.concurrent.Executors")
        BiometricPrompt = autoclass("androidx.biometric.BiometricPrompt")
        PromptInfo      = autoclass("androidx.biometric.BiometricPrompt$PromptInfo")

        activity = PythonActivity.mActivity
        executor = Executors.newSingleThreadExecutor()

        class _AuthCallback(PythonJavaClass):
            __javainterfaces__ = [
                "androidx/biometric/BiometricPrompt$AuthenticationCallback"
            ]
            __javacontext__ = "app"

            @java_method("(ILjava/lang/CharSequence;)V")
            def onAuthenticationError(self, error_code, help_string):
                msg = str(help_string) if help_string else "Authentication error"
                Clock.schedule_once(lambda *_: on_failure(msg), 0)

            @java_method("(Landroidx/biometric/BiometricPrompt$AuthenticationResult;)V")
            def onAuthenticationSucceeded(self, result):
                Clock.schedule_once(lambda *_: on_success(), 0)

            @java_method("()V")
            def onAuthenticationFailed(self):
                # A single failed attempt - the OS prompt stays open for retry
                pass

        callback = _AuthCallback()
        bp = BiometricPrompt(activity, executor, callback)

        info = (
            PromptInfo.Builder()
            .setTitle("ClearSpend")
            .setSubtitle("Verify your identity to continue")
            .setNegativeButtonText("Use PIN instead")
            .build()
        )
        bp.authenticate(info)

    except Exception as exc:
        # BiometricPrompt requires FragmentActivity but Kivy uses Activity.
        # This fails with ClassCastException on most devices.
        on_failure(f"Biometric not supported: {exc}")
