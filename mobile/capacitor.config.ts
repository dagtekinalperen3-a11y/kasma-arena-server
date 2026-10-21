import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.evolvearena.game",
  appName: "EvolveArena",
  webDir: "dist",
  backgroundColor: "#0b0d18",
  android: {
    allowMixedContent: false,
    backgroundColor: "#0b0d18",
  },
  ios: {
    contentInset: "never",
    backgroundColor: "#0b0d18",
    scrollEnabled: false,
  },
  plugins: {
    SplashScreen: {
      launchShowDuration: 600,
      launchAutoHide: true,
      backgroundColor: "#0b0d18",
      showSpinner: false,
      androidScaleType: "CENTER_CROP",
      splashFullScreen: true,
      splashImmersive: true,
    },
  },
};

export default config;
