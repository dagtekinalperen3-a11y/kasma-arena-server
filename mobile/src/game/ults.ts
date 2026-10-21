/**
 * Skin özel yetenekleri (ülti) — Python fire_skin_ult / update_skin_ult.
 */
import { dist, rand, TAU, shuffle, RGB } from "../core/util";
import { GD } from "./data";
import { PlayerProjectile, Pickup } from "./objects";
import { zigzag } from "./fx";
import { DMG } from "./enemy";
import { sfx } from "../core/audio";
import { haptic } from "../core/native";
import { t, tx } from "../core/i18n";
import type { Run, Target } from "./run";

const C = GD;

export interface BlackHole {
  x: number;
  y: number;
  t: number;
  dur: number;
  r: number;
  mult: number;
  tick: number;
  view?: any;
}

function ultTargets(run: Run, radius?: number): Target[] {
  const p = run.player;
  const out: Target[] = [];
  for (const e of run.targets) {
    if (!e.alive) continue;
    if (radius === undefined || dist(p.x, p.y, e.x, e.y) <= radius) out.push(e);
  }
  return out;
}

function densestPoint(run: Run, reach: number, clusterR: number): [number, number] {
  const p = run.player;
  let cand = run.enemies.filter((e) => e.alive && dist(p.x, p.y, e.x, e.y) <= reach);
  if (!cand.length) return [p.x + p.aim_dir[0] * 220, p.y + p.aim_dir[1] * 220];
  if (cand.length > 90) cand = shuffle(cand).slice(0, 90);
  let best = cand[0], bn = -1;
  const r2 = clusterR * clusterR;
  for (const e of cand) {
    let n = 0;
    for (const o of cand) if ((e.x - o.x) ** 2 + (e.y - o.y) ** 2 <= r2) n++;
    if (n > bn) {
      bn = n;
      best = e;
    }
  }
  return [best.x, best.y];
}

function spawnNova(run: Run, n: number, mult: number, pierce = 1, homing = 0) {
  const p = run.player;
  const sk = p.skin;
  const base = Math.atan2(p.aim_dir[1], p.aim_dir[0]);
  for (let i = 0; i < n; i++) {
    const ang = base + (TAU * i) / n;
    const pr = new PlayerProjectile(p.x + Math.cos(ang) * (p.radius + 6), p.y + Math.sin(ang) * (p.radius + 6), Math.cos(ang) * 640, Math.sin(ang) * 640, p.effDmg() * mult, p.effPierceHits() + pierce, p.effCritChance(), p.effCritDmg(), homing, sk.proj, sk.color, sk.accent);
    pr.wsrc = "ult";
    run.playerProjectiles.push(pr);
  }
  p.run_shots += n;
}

function lightningFx(run: Run, x: number, y: number, col: RGB | number[]) {
  run.fx.bolt(zigzag(x, y - 320, x, y, 6, 22), col, 0.3, 3);
  run.fx.shockwave(x, y, 46, col, 0.25, 3);
}

function banner(run: Run, text: string, col: RGB | number[]) {
  const p = run.player;
  run.fx.popup(p.x, p.y - 58, text, col, 24, 1.1, true);
  run.onEvent("ult", { name: text, color: col });
}

export function updateSkinUlt(run: Run, dt: number) {
  const p = run.player;
  if (!p.ult || !p.alive) return;
  DMG.src = "ult";
  if (p.ult_trigger) {
    const k = p.ult_trigger;
    p.ult_trigger = null;
    fireSkinUlt(run, k);
  } else if ((p.ult.mode ?? "auto") === "auto" && p.ultReady()) {
    p.startUltCooldown();
    fireSkinUlt(run, p.ult.kind);
  }
  // kara delikler
  if (run.blackHoles.length) {
    const keep: BlackHole[] = [];
    for (const bh of run.blackHoles) {
      bh.t += dt;
      for (const e of run.targets) {
        if (!e.alive) continue;
        const dx = bh.x - e.x, dy = bh.y - e.y;
        const d = Math.hypot(dx, dy);
        if (d > bh.r || d < 6) continue;
        const pull = (90 + 360 * (1 - d / bh.r)) * (e.isBoss ? 0.18 : 1);
        const st = Math.min(d - 4, pull * dt);
        e.x += (dx / d) * st;
        e.y += (dy / d) * st;
      }
      bh.tick -= dt;
      if (bh.tick <= 0) {
        bh.tick = 0.3;
        for (const e of run.targets) if (e.alive && dist(bh.x, bh.y, e.x, e.y) <= bh.r * 0.55) run.ultHit(e, p.effDmg() * 0.22);
      }
      if (bh.t >= bh.dur) {
        for (const e of run.targets) if (e.alive && dist(bh.x, bh.y, e.x, e.y) <= bh.r * 0.8) run.ultHit(e, p.effDmg() * bh.mult, true);
        run.fx.flash([200, 180, 255], 0.3);
        run.fx.shake(10, 0.4);
        for (let k = 0; k < 3; k++) run.fx.shockwave(bh.x, bh.y, bh.r * (0.5 + 0.3 * k), [180, 150, 255], 0.45 + 0.1 * k, 7 - 2 * k);
        run.fx.burst(bh.x, bh.y, [200, 180, 255], 46, 420, 0.7, 5);
        sfx("explosion", 1);
      } else keep.push(bh);
    }
    run.blackHoles = keep;
  }
  if (p.thorn_field_t > 0) {
    p.thorn_field_t -= dt;
    p.thorn_field_tick -= dt;
    if (p.thorn_field_tick <= 0) {
      p.thorn_field_tick = 0.5;
      for (const e of ultTargets(run, p.thorn_field_r)) {
        run.ultHit(e, p.effDmg() * 0.35);
        e.applySlow(0.7, 0.8);
      }
      run.fx.shockwave(p.x, p.y, p.thorn_field_r, [120, 220, 140], 0.3, 3);
    }
  }
  DMG.src = "other";
}

export function fireSkinUlt(run: Run, kind: string) {
  const p = run.player;
  const u = p.ult!;
  const col = u.color;
  run.timeStop = Math.max(run.timeStop, C.ULT_FREEZE_ON_CAST);
  run.fx.ring(p.x, p.y, col, 22, 260, 0.45, 3.5);
  run.fx.shake(5, 0.2);
  haptic("medium");
  p.ult_fx_t = 0.5;
  const name = tx("ult." + p.skin.id, u.name);
  switch (kind) {
    case "guard":
      p.shield_charges += 2;
      p.heal(p.max_hp * 0.15);
      run.fx.shockwave(p.x, p.y, 120, col, 0.4, 5);
      banner(run, name, col);
      sfx("shield", 1);
      break;
    case "sprint":
      p.addTempBuff(6, { run_spd_mult: 0.35, run_aspd_mult: 0.25 });
      p.dash_cd_timer = 0;
      banner(run, name, col);
      sfx("dash", 1);
      break;
    case "nova":
      spawnNova(run, u.n ?? 14, u.mult ?? 0.85, u.pierce ?? 1);
      banner(run, name, col);
      sfx("ult", 0.8);
      break;
    case "salvo":
      spawnNova(run, u.n ?? 9, u.mult ?? 0.95, 1, 2);
      banner(run, name, col);
      sfx("ult", 0.8);
      break;
    case "star_fall": {
      const tg = shuffle(ultTargets(run));
      for (const e of tg.slice(0, u.n ?? 7)) {
        run.ultHit(e, p.effDmg() * (u.mult ?? 1.35), false, 90);
        run.fx.burst(e.x, e.y, col, 10, 150, 0.4, 3);
        run.fx.shockwave(e.x, e.y, 54, col, 0.3, 3);
      }
      banner(run, name, col);
      sfx("levelup", 0.8);
      break;
    }
    case "chain_storm": {
      const bossDmg = p.effDmg() * (0.9 + 0.35 * 3);
      for (const e of ultTargets(run)) {
        if (e.isBoss) run.ultHit(e, bossDmg);
        else run.ultHit(e, Math.max(1, e.max_hp * 0.2));
        lightningFx(run, e.x, e.y, col);
      }
      run.fx.flash(col, 0.3);
      banner(run, name, col);
      sfx("lightning", 1);
      break;
    }
    case "death_defy": {
      const dur = u.duration ?? 5;
      run.timeStop = Math.max(run.timeStop, dur);
      p.hp = Math.max(1, p.hp);
      p.invuln = Math.max(p.invuln, dur + 0.4);
      run.fx.flash(col, 0.45);
      for (let k = 0; k < 3; k++) run.fx.shockwave(p.x, p.y, 200 + k * 180, col, 0.6, 6 - k);
      banner(run, name + " — " + t("fx.time_stop"), col);
      sfx("second", 1);
      break;
    }
    case "fire_ring": {
      const rad = u.radius ?? 330;
      for (const e of ultTargets(run, rad)) {
        run.ultHit(e, p.effDmg() * 1.1, false, 140);
        e.applyBurn(10, 4);
      }
      for (let k = 0; k < 3; k++) run.fx.shockwave(p.x, p.y, rad * (0.5 + k * 0.28), col, 0.45, 6 - k);
      run.fx.burst(p.x, p.y, col, 26, 280, 0.6, 4);
      banner(run, name, col);
      sfx("explosion", 1);
      break;
    }
    case "midas": {
      const rad = u.radius ?? 340;
      for (const e of ultTargets(run, rad)) {
        run.ultHit(e, p.effDmg() * 0.9);
        if (e.alive) run.pickups.push(new Pickup(e.x + rand(-10, 10), e.y + rand(-10, 10), "coin", Math.max(2, Math.floor(e.coin * 0.6))));
        run.fx.spark(e.x, e.y, [232, 186, 90], 0, -40, 0.5, 3);
      }
      run.fx.shockwave(p.x, p.y, rad, [232, 186, 90], 0.45, 5);
      banner(run, name, [232, 186, 90]);
      sfx("coin", 1);
      break;
    }
    case "ambush": {
      const dur = u.duration ?? 4;
      p.invuln = Math.max(p.invuln, dur);
      p.crit_forced = Math.max(p.crit_forced, dur);
      p.addTempBuff(dur, { run_spd_mult: 0.2 });
      banner(run, name, col);
      sfx("dash", 1);
      break;
    }
    case "ice_age": {
      const fr = u.freeze ?? 2.5;
      run.timeStop = Math.max(run.timeStop, fr);
      for (const e of ultTargets(run)) {
        run.ultHit(e, p.effDmg() * 0.7);
        e.applySlow(0.45, fr + 5);
      }
      run.fx.flash(col, 0.3);
      run.fx.shockwave(p.x, p.y, 520, col, 0.6, 6);
      banner(run, name, col);
      sfx("shield", 1);
      break;
    }
    case "blood_rite": {
      const rad = u.radius ?? 320;
      let drained = 0;
      for (const e of ultTargets(run, rad)) {
        const before = e.hp;
        run.ultHit(e, e.max_hp * 0.1 + p.effDmg() * 0.5);
        drained += Math.max(0, before - Math.max(0, e.hp));
        run.fx.bolt([[e.x, e.y], [p.x, p.y]], [235, 70, 100], 0.25, 2);
      }
      if (drained > 0) p.lifesteal(drained * 0.5, false);
      run.fx.shockwave(p.x, p.y, rad, col, 0.45, 5);
      banner(run, name, col);
      sfx("hurt", 0.8);
      break;
    }
    case "bulwark": {
      const dur = u.duration ?? 6;
      p.addTempBuff(dur, { dmg_taken_mult: -0.55 });
      p.shield_charges += 1;
      for (const e of ultTargets(run, 260)) run.ultHit(e, p.effDmg() * 0.6, false, 420);
      run.fx.shockwave(p.x, p.y, 260, col, 0.45, 6);
      banner(run, name, col);
      sfx("shield", 1);
      break;
    }
    case "thunder": {
      const tg = shuffle(ultTargets(run));
      for (const e of tg.slice(0, u.n ?? 6)) {
        run.ultHit(e, p.effDmg() * (u.mult ?? 1.6));
        lightningFx(run, e.x, e.y, col);
      }
      run.fx.flash(col, 0.25);
      banner(run, name, col);
      sfx("lightning", 1);
      break;
    }
    case "thorn_field":
      p.thorn_field_t = u.duration ?? 6;
      p.thorn_field_r = u.radius ?? 240;
      p.thorn_field_tick = 0;
      run.fx.shockwave(p.x, p.y, p.thorn_field_r, col, 0.45, 5);
      banner(run, name, col);
      sfx("buy", 0.8);
      break;
    case "frenzy_rush": {
      const dur = u.duration ?? 7;
      p.addTempBuff(dur, { run_dmg_mult: 0.4, run_aspd_mult: 0.3 });
      p.frenzy_stacks = Math.max(p.frenzy_stacks, 4);
      p.frenzy_timer = Math.max(p.frenzy_timer, dur);
      run.fx.flash(col, 0.2);
      banner(run, name, col);
      sfx("bonk", 0.9);
      break;
    }
    case "orbit_shield":
      p.addTempBuff(u.duration ?? 8, { orbit_level: 3 });
      p.shield_charges += 1;
      run.fx.shockwave(p.x, p.y, 120, col, 0.4, 5);
      banner(run, name, col);
      sfx("shield", 1);
      break;
    case "web_trap": {
      const rad = u.radius ?? 360;
      for (const e of ultTargets(run, rad)) {
        e.applySlow(0.12, 4);
        run.ultHit(e, p.effDmg() * 0.6);
        run.fx.bolt([[p.x, p.y], [e.x, e.y]], [240, 240, 255], 0.3, 1.5);
      }
      run.fx.shockwave(p.x, p.y, rad, col, 0.45, 5);
      banner(run, name, col);
      sfx("shoot_a", 0.8);
      break;
    }
    case "ash_spin": {
      const rad = u.radius ?? 230;
      let total = 0;
      for (const e of ultTargets(run, rad)) {
        const before = e.hp;
        run.ultHit(e, p.effDmg() * (u.mult ?? 2), false, 260);
        total += Math.max(0, before - Math.max(0, e.hp));
      }
      if (total > 0) p.lifesteal(total * 0.25, false);
      for (let k = 0; k < 3; k++) run.fx.shockwave(p.x, p.y, rad * (0.55 + k * 0.25), col, 0.4, 5 - k);
      banner(run, name, col);
      sfx("bonk", 1);
      break;
    }
    case "quake":
      for (const e of ultTargets(run)) {
        run.ultHit(e, p.effDmg() * (u.mult ?? 1.3), false, 360);
        run.fx.spark(e.x, e.y, col, 0, -50, 0.5, 3);
      }
      run.fx.shake(14, 0.5);
      for (let k = 0; k < 4; k++) run.fx.shockwave(p.x, p.y, 240 + k * 260, col, 0.55, 8 - k);
      banner(run, name, col);
      sfx("explosion", 1);
      break;
    case "black_hole": {
      const rad = u.radius ?? 430;
      const [cx, cy] = densestPoint(run, 700, 210);
      run.blackHoles.push({ x: cx, y: cy, t: 0, dur: u.duration ?? 3, r: rad, mult: u.mult ?? 2.6, tick: 0 });
      run.fx.shockwave(cx, cy, rad, col, 0.5, 4);
      banner(run, name, col);
      sfx("vortex", 1);
      break;
    }
    case "dream": {
      const rad = u.radius ?? 300, dur = u.duration ?? 6;
      p.heal(p.max_hp * 0.25);
      p.addTempBuff(dur, { run_crit_bonus: 0.25 });
      for (const e of ultTargets(run, rad)) {
        run.ultHit(e, p.effDmg() * 0.7);
        e.fearTimer = Math.max(e.fearTimer, 3);
      }
      run.fx.shockwave(p.x, p.y, rad, col, 0.5, 6);
      run.fx.burst(p.x, p.y, col, 24, 220, 0.6, 4);
      banner(run, name, col);
      sfx("levelup", 0.9);
      break;
    }
  }
}
