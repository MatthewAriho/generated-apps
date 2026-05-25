export type AppTheme = "midnight" | "ocean" | "forest" | "ember" | "lavender" | "light" | "cream";

export const APP_THEMES: { id: AppTheme; label: string; preview: string }[] = [
  { id: "midnight", label: "Midnight", preview: "#1a1a2e" },
  { id: "ocean", label: "Ocean", preview: "#0d1b2a" },
  { id: "forest", label: "Forest", preview: "#1a2e1a" },
  { id: "ember", label: "Ember", preview: "#1f1410" },
  { id: "lavender", label: "Lavender", preview: "#1a1525" },
  { id: "light", label: "Light", preview: "#f5f5f5" },
  { id: "cream", label: "Cream", preview: "#faf6f0" },
];

const STORAGE_KEY = "bookworm_app_theme";

export function getAppTheme(): AppTheme {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved && APP_THEMES.some((t) => t.id === saved)) return saved as AppTheme;
  return "midnight";
}

export function setAppTheme(theme: AppTheme): void {
  localStorage.setItem(STORAGE_KEY, theme);
  applyAppTheme(theme);
}

export function applyAppTheme(theme?: AppTheme): void {
  const t = theme ?? getAppTheme();
  document.documentElement.setAttribute("data-theme", t);
  // Update meta theme-color for mobile browser chrome
  const meta = document.querySelector('meta[name="theme-color"]');
  const themeObj = APP_THEMES.find((x) => x.id === t);
  if (meta && themeObj) meta.setAttribute("content", themeObj.preview);
}
