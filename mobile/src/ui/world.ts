/**
 * REKORLAR > DÜNYA sekmesi: giriş / kayıt formu ve ilk 10.
 */
import { t } from "../core/i18n";
import { fmtTime } from "../core/util";
import { getSkin } from "../game/data";
import { online } from "../net/online";
import { heroPortrait } from "../render/portrait";
import { h, btn, esc, short } from "./dom";
import { icon } from "./icons";
import { Layer } from "./overlays";

let mode: "login" | "register" = "register";

export function renderWorld(el: HTMLElement) {
  el.innerHTML = "";
  const top = h("div", "world-top");
  el.append(top);
  if (online.loggedIn) {
    top.innerHTML = `<span>${icon("user", 18, "#7fd0ff")} ${esc(t("acc.signed", online.account!.username))}</span>`;
    const acts = h("div", "acc-row");
    acts.append(
      btn(esc(t("acc.logout")), "ghost mini", () => {
        online.logout();
        renderWorld(el);
      }),
      btn(esc(t("acc.delete")), "danger mini", () => deleteBox(el)),
    );
    top.append(acts);
  } else {
    el.append(accountForm(() => renderWorld(el)));
  }
  const list = h("div", "world-list");
  el.append(list);
  list.innerHTML = `<div class="empty small">${icon("globe", 36, "#4a5274")}<span>${esc(t("acc.loading"))}</span></div>`;
  online.scores().then(
    (rows) => {
      if (!list.isConnected) return;
      if (!rows.length) {
        list.innerHTML = `<div class="empty small">${icon("trophy", 36, "#4a5274")}<span>${esc(t("acc.empty"))}</span></div>`;
        return;
      }
      const me = online.account?.username?.toLowerCase();
      list.innerHTML = `<table class="rec-table"><tbody>${rows
        .map((r, i) => {
          const sk = getSkin(r.skin || "default");
          return `<tr class="${i < 3 ? "top" + (i + 1) : ""}${me && r.name?.toLowerCase() === me ? " me" : ""}"><td class="rk">${i + 1}</td><td class="pf"><img src="${heroPortrait(sk, 64)}" alt=""></td><td class="nm">${esc(r.name || "?")}</td><td class="sc">${short(r.score)}</td><td>${esc(t("hud.wave", r.wave))}</td><td>${fmtTime(r.run_time || 0)}</td><td class="mp">${esc(t("diff." + (r.diff || "normal")))}</td></tr>`;
        })
        .join("")}</tbody></table>`;
    },
    () => {
      if (!list.isConnected) return;
      list.innerHTML = `<div class="empty small">${icon("globe", 36, "#6a5274")}<span>${esc(t("acc.offline"))}</span></div>`;
      list.append(btn(esc(t("acc.retry")), "ghost small", () => renderWorld(el)));
    },
  );
}

function accountForm(done: () => void) {
  const box = h("div", "acc-box");
  const reg = mode === "register";
  box.innerHTML = `<div class="acc-need">${esc(t("acc.need"))}</div>`;
  const f = h("form", "acc-form");
  f.setAttribute("autocomplete", "on");
  const inp = (type: string, ph: string, name: string, ac: string) => {
    const i = h("input", "inp") as HTMLInputElement;
    i.type = type;
    i.placeholder = ph;
    i.name = name;
    i.autocomplete = ac as any;
    i.spellcheck = false;
    i.autocapitalize = "off";
    return i;
  };
  const user = inp("text", reg ? t("acc.user") : t("acc.user_or_mail"), "username", "username");
  const pass = inp("password", t("acc.pass"), "password", reg ? "new-password" : "current-password");
  const mail = inp("email", t("acc.email"), "email", "email");
  f.append(user, pass);
  if (reg) f.append(mail);
  const msg = h("div", "acc-msg");
  const go = btn(esc(reg ? t("acc.register") : t("acc.login")), "primary", async () => {
    msg.textContent = "…";
    go.classList.add("disabled");
    try {
      if (reg) await online.register(user.value, pass.value, mail.value);
      else await online.login(user.value, pass.value);
      done();
    } catch (e: any) {
      msg.textContent = e?.name === "AbortError" || e?.message === "Failed to fetch" ? t("acc.offline") : String(e?.message || e);
      go.classList.remove("disabled");
    }
  });
  f.addEventListener("submit", (e) => e.preventDefault());
  const sw = h("button", "link", esc(reg ? t("acc.to_login") : t("acc.to_register")));
  sw.type = "button";
  sw.addEventListener("click", () => {
    mode = reg ? "login" : "register";
    done();
  });
  const row = h("div", "acc-row");
  row.append(go, sw);
  box.append(f, row, msg);
  if (reg) box.insertAdjacentHTML("beforeend", `<div class="acc-note">${esc(t("acc.privacy"))}</div>`);
  return box;
}

function deleteBox(el: HTMLElement) {
  const host = el.closest(".ui-layer") as HTMLElement;
  const L = new Layer(host, "confirm");
  const box = h("div", "confirm-box");
  box.innerHTML = `<div class="cb-text">${esc(t("acc.delete_q"))}</div>`;
  const pw = h("input", "inp") as HTMLInputElement;
  pw.type = "password";
  pw.placeholder = t("acc.pass");
  pw.autocomplete = "current-password";
  const msg = h("div", "acc-msg");
  const row = h("div", "row");
  row.append(
    btn(esc(t("c.cancel")), "", () => L.close()),
    btn(esc(t("acc.delete")), "danger", async () => {
      msg.textContent = "…";
      try {
        await online.deleteAccount(pw.value);
        L.close(() => renderWorld(el));
      } catch (e: any) {
        msg.textContent = String(e?.message || e);
      }
    }),
  );
  box.append(pw, msg, row);
  L.el.append(box);
}
