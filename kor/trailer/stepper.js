// sahte zaman: oyunun her karesini biz ilerletiriz
module.exports = () => {
  let now = 0; const q = [];
  performance.now = () => now;
  window.requestAnimationFrame = cb => { q.push(cb); return q.length; };
  window.cancelAnimationFrame = () => {};
  window.__advance = ms => {
    now += ms;
    // CSS animasyon/geçişlerini de aynı saatle ilerlet; bitenleri bitir (yoksa birikir)
    try {
      for (const a of document.getAnimations()) {
        a.pause(); a.__t = (a.__t ?? (a.currentTime || 0)) + ms;
        const end = a.effect && a.effect.getComputedTiming().endTime;
        if (end != null && isFinite(end) && a.__t >= end) a.finish(); else a.currentTime = a.__t;
      }
    } catch (e) {}
    const cbs = q.splice(0); cbs.forEach(cb => { try { cb(now); } catch (e) { console.error(e); } });
  };
};
