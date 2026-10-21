/**
 * Çevrim içi özellikler (dünya sıralaması). Ağ yoksa sessizce devre dışı.
 */
import type { Save } from "../game/save";
import type { Run } from "../game/run";

class Online {
  save: Save | null = null;
  init(save: Save) {
    this.save = save;
  }
  submitRun(_s: ReturnType<Run["summary"]>) {}
  achievement(_id: string) {}
}

export const online = new Online();
