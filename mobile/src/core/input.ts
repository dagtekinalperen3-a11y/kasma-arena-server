/**
 * Dokunmatik + klavye/fare girişi.
 *
 * Bütün dokunuşlar tek bir yerde (oyun katmanı) toplanır; düğmeler yalnızca
 * görseldir ve isabet testi burada yapılır. Böylece joystick tutulurken aynı
 * anda DASH / BONK basmak (çoklu dokunuş) sorunsuz çalışır.
 */

export interface TouchButton {
  id: string;
  x: number; // ekran px (CSS)
  y: number;
  r: number;
  visible: boolean;
  pressed: boolean;
}

export class Input {
  // hareket (analog, -1..1)
  mx = 0;
  my = 0;
  // elle nişan (sağ parmak / fare)
  aimActive = false;
  ax = 0;
  ay = 0;
  // fare dünyaya göre (masaüstü)
  mouseX = 0;
  mouseY = 0;
  mouseDown = false;
  usingMouse = false;
  // tek seferlik basışlar
  private pressedQ = new Set<string>();
  private held = new Set<string>();
  // joystick durumu (çizim için)
  joyActive = false;
  joyBaseX = 0;
  joyBaseY = 0;
  joyX = 0;
  joyY = 0;
  joyR = 62;
  aimStickActive = false;
  aimBaseX = 0;
  aimBaseY = 0;
  aimX = 0;
  aimY = 0;
  private joyId = -1;
  private aimId = -1;
  private btnIds = new Map<number, string>();
  buttons: TouchButton[] = [];
  enabled = false;
  isTouch = false;
  private keys = new Set<string>();
  leftZone = 0.45; // ekranın sol kısmı joystick
  onAnyTouch: (() => void) | null = null;

  constructor(private el: HTMLElement) {
    this.isTouch = "ontouchstart" in window || navigator.maxTouchPoints > 0;
    el.addEventListener("pointerdown", (e) => this.down(e), { passive: false });
    window.addEventListener("pointermove", (e) => this.move(e), { passive: false });
    window.addEventListener("pointerup", (e) => this.up(e), { passive: false });
    window.addEventListener("pointercancel", (e) => this.up(e), { passive: false });
    el.addEventListener("contextmenu", (e) => e.preventDefault());
    window.addEventListener("keydown", (e) => this.keyDown(e));
    window.addEventListener("keyup", (e) => this.keys.delete(e.code));
    window.addEventListener("blur", () => this.reset());
  }

  setButtons(btns: TouchButton[]) {
    this.buttons = btns;
  }

  btn(id: string) {
    return this.buttons.find((b) => b.id === id);
  }

  reset() {
    this.mx = this.my = 0;
    this.aimActive = false;
    this.joyActive = false;
    this.aimStickActive = false;
    this.joyId = this.aimId = -1;
    this.btnIds.clear();
    for (const b of this.buttons) b.pressed = false;
    this.keys.clear();
    this.held.clear();
    this.pressedQ.clear();
    this.mouseDown = false;
  }

  /** Bir eylem bu karede basıldı mı (tüketir). */
  take(id: string) {
    if (this.pressedQ.has(id)) {
      this.pressedQ.delete(id);
      return true;
    }
    return false;
  }
  isHeld(id: string) {
    return this.held.has(id);
  }
  press(id: string) {
    this.pressedQ.add(id);
  }
  clearPresses() {
    this.pressedQ.clear();
  }

  private hitButton(x: number, y: number): TouchButton | null {
    let best: TouchButton | null = null;
    let bd = 1e9;
    for (const b of this.buttons) {
      if (!b.visible) continue;
      const d = Math.hypot(x - b.x, y - b.y);
      if (d <= b.r * 1.25 && d < bd) {
        bd = d;
        best = b;
      }
    }
    return best;
  }

  private down(e: PointerEvent) {
    this.onAnyTouch?.();
    if (!this.enabled) return;
    e.preventDefault();
    const x = e.clientX, y = e.clientY;
    if (e.pointerType === "mouse") {
      this.usingMouse = true;
      this.mouseX = x;
      this.mouseY = y;
      if (e.button === 0) this.mouseDown = true;
      if (e.button === 2) this.press("bonk");
      return;
    }
    this.usingMouse = false;
    try {
      this.el.setPointerCapture(e.pointerId);
    } catch {}
    const b = this.hitButton(x, y);
    if (b) {
      b.pressed = true;
      this.btnIds.set(e.pointerId, b.id);
      this.press(b.id);
      this.held.add(b.id);
      return;
    }
    const w = window.innerWidth;
    if (x < w * this.leftZone && this.joyId < 0) {
      this.joyId = e.pointerId;
      this.joyActive = true;
      this.joyBaseX = x;
      this.joyBaseY = y;
      this.joyX = x;
      this.joyY = y;
      this.mx = this.my = 0;
      return;
    }
    if (this.aimId < 0) {
      this.aimId = e.pointerId;
      this.aimStickActive = true;
      this.aimBaseX = x;
      this.aimBaseY = y;
      this.aimX = x;
      this.aimY = y;
    }
  }

  private move(e: PointerEvent) {
    if (e.pointerType === "mouse") {
      this.mouseX = e.clientX;
      this.mouseY = e.clientY;
      return;
    }
    if (!this.enabled) return;
    const x = e.clientX, y = e.clientY;
    if (e.pointerId === this.joyId) {
      let dx = x - this.joyBaseX, dy = y - this.joyBaseY;
      const d = Math.hypot(dx, dy);
      const R = this.joyR;
      if (d > R) {
        // taban parmağı takip eder (yüzen joystick)
        const k = (d - R) / d;
        this.joyBaseX += dx * k;
        this.joyBaseY += dy * k;
        dx = x - this.joyBaseX;
        dy = y - this.joyBaseY;
      }
      this.joyX = x;
      this.joyY = y;
      const dd = Math.hypot(dx, dy);
      const dead = R * 0.12;
      if (dd < dead) {
        this.mx = this.my = 0;
      } else {
        const mag = Math.min(1, (dd - dead) / (R * 0.7 - dead));
        this.mx = (dx / dd) * mag;
        this.my = (dy / dd) * mag;
      }
      e.preventDefault();
    } else if (e.pointerId === this.aimId) {
      this.aimX = x;
      this.aimY = y;
      const dx = x - this.aimBaseX, dy = y - this.aimBaseY;
      const d = Math.hypot(dx, dy);
      if (d > 14) {
        this.aimActive = true;
        this.ax = dx / d;
        this.ay = dy / d;
      }
      if (d > 70) {
        this.aimBaseX = x - (dx / d) * 70;
        this.aimBaseY = y - (dy / d) * 70;
      }
      e.preventDefault();
    } else if (this.btnIds.has(e.pointerId)) {
      // parmak düğmeden kaydıysa bırakılmış sayılmaz (oyunlarda daha rahat)
    }
  }

  private up(e: PointerEvent) {
    if (e.pointerType === "mouse") {
      if (e.button === 0) this.mouseDown = false;
      return;
    }
    if (e.pointerId === this.joyId) {
      this.joyId = -1;
      this.joyActive = false;
      this.mx = this.my = 0;
    } else if (e.pointerId === this.aimId) {
      this.aimId = -1;
      this.aimStickActive = false;
      this.aimActive = false;
    }
    const bid = this.btnIds.get(e.pointerId);
    if (bid) {
      this.btnIds.delete(e.pointerId);
      const b = this.btn(bid);
      if (b) b.pressed = false;
      this.held.delete(bid);
    }
  }

  private keyDown(e: KeyboardEvent) {
    this.onAnyTouch?.();
    if (e.repeat) return;
    this.keys.add(e.code);
    const map: Record<string, string> = {
      Space: "dash", ShiftLeft: "dash", KeyQ: "bonk", KeyE: "use", KeyF: "use", KeyB: "shop",
      Escape: "pause", KeyP: "pause", KeyM: "map", KeyR: "reroll", Digit1: "c1", Digit2: "c2", Digit3: "c3",
    };
    const a = map[e.code];
    if (a) {
      this.press(a);
      if (a !== "pause") e.preventDefault();
    }
  }

  /** Klavye yön tuşlarını analog harekete ekler. */
  pollKeyboard() {
    if (!this.enabled) return;
    let kx = 0, ky = 0;
    if (this.keys.has("KeyA") || this.keys.has("ArrowLeft")) kx -= 1;
    if (this.keys.has("KeyD") || this.keys.has("ArrowRight")) kx += 1;
    if (this.keys.has("KeyW") || this.keys.has("ArrowUp")) ky -= 1;
    if (this.keys.has("KeyS") || this.keys.has("ArrowDown")) ky += 1;
    if (kx || ky) {
      const l = Math.hypot(kx, ky);
      this.mx = kx / l;
      this.my = ky / l;
      this.kbMove = true;
    } else if (this.kbMove) {
      this.kbMove = false;
      if (!this.joyActive) this.mx = this.my = 0;
    }
  }
  private kbMove = false;
}
