package com.evolvearena.game;

import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.WindowManager;
import android.webkit.WebView;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.BridgeActivity;
import com.getcapacitor.WebViewListener;
import java.util.Locale;

/**
 * Tam ekran oyun etkinliği:
 *  - durum ve gezinme çubukları gizli (kaydırınca geçici görünür),
 *  - çizim çentiğin / kamera deliğinin altına kadar uzanır (yanlarda
 *    siyah şerit kalmaz),
 *  - güvenli alan boşlukları CSS değişkeni olarak sayfaya verilir; arayüz
 *    düğmeleri çentiğin altında kalmaz,
 *  - oyun sırasında ekran kararmaz.
 */
public class MainActivity extends BridgeActivity {
    private float insetL, insetT, insetR, insetB;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            WindowManager.LayoutParams lp = getWindow().getAttributes();
            lp.layoutInDisplayCutoutMode = Build.VERSION.SDK_INT >= Build.VERSION_CODES.R
                ? WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS
                : WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
            getWindow().setAttributes(lp);
        }
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        hideSystemBars();

        View decor = getWindow().getDecorView();
        ViewCompat.setOnApplyWindowInsetsListener(decor, (v, insets) -> {
            Insets c = insets.getInsets(WindowInsetsCompat.Type.displayCutout());
            float d = getResources().getDisplayMetrics().density;
            insetL = c.left / d;
            insetT = c.top / d;
            insetR = c.right / d;
            insetB = c.bottom / d;
            v.setPadding(0, 0, 0, 0);
            pushInsets();
            return ViewCompat.onApplyWindowInsets(v, insets);
        });

        if (bridge != null) {
            bridge.addWebViewListener(new WebViewListener() {
                @Override
                public void onPageLoaded(WebView webView) {
                    pushInsets();
                }
            });
        }
    }

    @Override
    public void onResume() {
        super.onResume();
        hideSystemBars();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemBars();
    }

    private void hideSystemBars() {
        WindowInsetsControllerCompat c = WindowCompat.getInsetsController(getWindow(), getWindow().getDecorView());
        c.hide(WindowInsetsCompat.Type.systemBars());
        c.setSystemBarsBehavior(WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
    }

    private void pushInsets() {
        if (bridge == null || bridge.getWebView() == null) return;
        final String js = String.format(Locale.US,
            "(function(){var s=document.documentElement.style;" +
            "s.setProperty('--app-inset-left','%.1fpx');s.setProperty('--app-inset-top','%.1fpx');" +
            "s.setProperty('--app-inset-right','%.1fpx');s.setProperty('--app-inset-bottom','%.1fpx');" +
            "window.dispatchEvent(new Event('appinsets'));})();",
            insetL, insetT, insetR, insetB);
        bridge.executeOnMainThread(() -> {
            if (bridge.getWebView() != null) bridge.getWebView().evaluateJavascript(js, null);
        });
    }
}
