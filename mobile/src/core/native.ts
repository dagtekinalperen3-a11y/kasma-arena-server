/**
 * Yerel (Android / iOS) köprüsü. Capacitor yoksa (tarayıcıda) her şey
 * sessizce boşa düşer, oyun yine çalışır.
 */
import { Capacitor } from "@capacitor/core";
import { Haptics, ImpactStyle, NotificationType } from "@capacitor/haptics";
import { StatusBar } from "@capacitor/status-bar";
import { SplashScreen } from "@capacitor/splash-screen";
import { App } from "@capacitor/app";
import { Preferences } from "@capacitor/preferences";
import { ScreenOrientation } from "@capacitor/screen-orientation";

export const isNative = Capacitor.isNativePlatform();
export const platform = Capacitor.getPlatform(); // "android" | "ios" | "web"

let hapticsOn = true;
let lastHaptic = 0;
export function setHaptics(on: boolean) {
  hapticsOn = on;
}

export function haptic(kind: "light" | "medium" | "heavy" | "success" | "warning" | "error" = "light") {
  if (!hapticsOn) return;
  const now = performance.now();
  if (kind === "light" && now - lastHaptic < 60) return;
  lastHaptic = now;
  if (!isNative) {
    if ("vibrate" in navigator && kind !== "light") {
      try {
        navigator.vibrate(kind === "heavy" ? 30 : 15);
      } catch {}
    }
    return;
  }
  try {
    if (kind === "success") Haptics.notification({ type: NotificationType.Success });
    else if (kind === "warning") Haptics.notification({ type: NotificationType.Warning });
    else if (kind === "error") Haptics.notification({ type: NotificationType.Error });
    else
      Haptics.impact({
        style: kind === "heavy" ? ImpactStyle.Heavy : kind === "medium" ? ImpactStyle.Medium : ImpactStyle.Light,
      });
  } catch {}
}

export async function nativeSetup(handlers: {
  onPause: () => void;
  onResume: () => void;
  onBack: () => void;
}) {
  if (isNative) {
    try {
      await StatusBar.hide();
    } catch {}
    try {
      await ScreenOrientation.lock({ orientation: "landscape" });
    } catch {}
    try {
      App.addListener("appStateChange", ({ isActive }) => (isActive ? handlers.onResume() : handlers.onPause()));
      App.addListener("backButton", () => handlers.onBack());
    } catch {}
  } else {
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) handlers.onPause();
      else handlers.onResume();
    });
  }
}

export async function hideSplash() {
  if (!isNative) return;
  try {
    await SplashScreen.hide({ fadeOutDuration: 250 });
  } catch {}
}

export function exitApp() {
  if (isNative && platform === "android") App.exitApp();
}

// --------------------------------------------------------------------------
// KALICI DEPOLAMA: yerelde Preferences (iOS'un WebView depolamasını
// temizlemesine karşı), tarayıcıda localStorage.
// --------------------------------------------------------------------------
export async function storeGet(key: string): Promise<string | null> {
  let v: string | null = null;
  if (isNative) {
    try {
      v = (await Preferences.get({ key })).value;
    } catch {}
  }
  if (v == null) {
    try {
      v = localStorage.getItem(key);
    } catch {}
  }
  return v;
}

export async function storeSet(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {}
  if (isNative) {
    try {
      await Preferences.set({ key, value });
    } catch {}
  }
}
