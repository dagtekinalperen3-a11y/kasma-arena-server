import "./ui/style.css";

async function boot() {
  const q = new URLSearchParams(location.search);
  if (import.meta.env.DEV && q.get("icongen")) {
    const m = await import("./devtools/icongen");
    await m.icongen();
    return;
  }
  if (import.meta.env.DEV && q.get("gallery")) {
    const m = await import("./gallery");
    await m.gallery();
    return;
  }
  const { startGame } = await import("./app");
  await startGame();
}

boot();
