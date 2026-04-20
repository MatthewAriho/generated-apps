package com.clearspend.clearspend;

import android.net.Uri;
import android.os.Bundle;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AppCompatActivity;

/**
 * Full-screen WebView that hosts Plaid Link.
 *
 * Extends AppCompatActivity (not Activity) so it is compatible with the
 * AppCompat theme that KivyMD applies to the application.
 *
 * Plaid fires completion events as URI redirects using the plaidlink:// scheme:
 *   plaidlink://connected?public_token=...   → success
 *   plaidlink://exit                         → user cancelled / error
 *   plaidlink://event?event_name=...         → progress events (ignored)
 *
 * Result is stored in static fields; Python reads them in on_resume() because
 * PythonActivity uses launchMode="singleTask" which breaks startActivityForResult.
 */
public class PlaidWebViewActivity extends AppCompatActivity {

    public static final String EXTRA_URL = "plaid_url";

    /** Non-null on success; null on cancel/exit. */
    public static volatile String lastPublicToken = null;
    /** True once the user finishes or exits Plaid Link. */
    public static volatile boolean completed = false;

    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        String url = getIntent().getStringExtra(EXTRA_URL);
        if (url == null || url.isEmpty()) {
            lastPublicToken = null;
            completed = true;
            finish();
            return;
        }

        webView = new WebView(this);
        setContentView(webView);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);

        webView.setWebViewClient(new WebViewClient() {

            // API 24+
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return handleUrl(request.getUrl().toString());
            }

            // API < 24 fallback
            @Override
            @SuppressWarnings("deprecation")
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return handleUrl(url);
            }
        });

        webView.loadUrl(url);
    }

    private boolean handleUrl(String url) {
        Uri uri;
        try {
            uri = Uri.parse(url);
        } catch (Exception e) {
            return false;
        }

        if (!"plaidlink".equals(uri.getScheme())) {
            return false;  // Let WebView load normal https:// pages
        }

        String action = uri.getHost();
        if ("connected".equals(action)) {
            lastPublicToken = uri.getQueryParameter("public_token");
            completed = true;
            finish();
        } else if ("exit".equals(action)) {
            lastPublicToken = null;
            completed = true;
            finish();
        }
        // Consume all plaidlink:// URLs (event, error, etc.)
        return true;
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            lastPublicToken = null;
            completed = true;
            finish();
        }
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }
}
