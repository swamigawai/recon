/**
 * Recon — Main ES Module Entrypoint (main.js)
 * High-performance, modular zero-build client application layer.
 */

import { SoundEngine } from "./modules/sound.js";
import { apiRequest, apiGetJson, apiPostJson, getAuthHeaders } from "./modules/api.js";
import { ReconState } from "./modules/state.js";
import { renderTableMatchmaker } from "./modules/matcher-ui.js";

// Expose on window for interactive developer tools and hybrid compatibility
if (typeof window !== "undefined") {
  window.ReconModules = {
    SoundEngine,
    api: { apiRequest, apiGetJson, apiPostJson, getAuthHeaders },
    state: ReconState,
    matcherUi: { renderTableMatchmaker },
  };
}

console.log("[Recon] Native ES Modules initialized (v1.0.0-milestones).");
