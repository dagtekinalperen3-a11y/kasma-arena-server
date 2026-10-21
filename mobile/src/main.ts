import "./ui/style.css";

async function boot() {
  const q = new URLSearchParams(location.search);
  if (q.get("gallery")) {
    const m = await import("./gallery");
    await m.gallery();
    return;
  }
  const { startGame } = await import("./app");
  await startGame();
}

boot();
