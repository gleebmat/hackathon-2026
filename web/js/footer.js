// Page footer (main page and login): AAU links and support, how the booking works, the team with contacts.
import { t, langSwitch } from "./i18n.js";

const AAU_LINKS = [
  ["f_aau", "https://www.aau.at/"],
  ["f_campus_online", "https://campus.aau.at/"],
  ["f_moodle", "https://moodle.aau.at/"],
  ["f_map", "https://campusplan.aau.at/"],
  ["f_support", "https://servicedesk.aau.at/"],
];

const TEAM = [
  { name: "Thomas Shapiro", role: "f_role_board", email: "thomas.shapiro.study@gmail.com" },
  { name: "Gleb Matyushev", role: "f_role_backend", email: "glebsmailbox@gmail.com" },
  { name: "Martha", role: "f_role_ui", email: "pobermarta.st.at@gmail.com" },
  { name: "Arshia", role: "f_role_models", email: "" },
];

const REPO = "https://github.com/gleebmat/hackathon-2026";

export function renderFooter(el, { compact = false } = {}) {
  const links = AAU_LINKS.map(([key, href]) => `<li><a href="${href}" target="_blank" rel="noopener">${t(key)}</a></li>`).join("");
  const team = TEAM.map((p) => `<li><b>${p.name}</b><span class="muted small">${t(p.role)}</span>
    ${p.email ? `<a class="small" href="mailto:${p.email}">${p.email}</a>` : ""}</li>`).join("");
  const how = compact ? "" : `<div class="foot-col"><h4>${t("f_how")}</h4><ul class="foot-how">
      ${["f_how_1", "f_how_2", "f_how_3", "f_how_4"].map((k) => `<li>${t(k)}</li>`).join("")}</ul></div>`;
  el.innerHTML = `
    <div class="foot-grid">
      <div class="foot-col"><h4>${t("f_university")}</h4><ul class="foot-links">${links}</ul></div>
      ${how}
      <div class="foot-col"><h4>${t("f_team")}</h4><p class="muted small">${t("f_contact")}</p><ul class="foot-team">${team}</ul></div>
    </div>
    <div class="foot-bottom">
      <span class="muted small">© 2026 Campus Booking System · ${t("f_built")}</span>
      <span class="foot-actions">
        ${compact ? "" : `<button type="button" class="link-btn small" data-action="shortcuts">⌨️ ${t("f_shortcuts")}</button>`}
        <a class="small" href="${REPO}" target="_blank" rel="noopener">${t("f_source")}</a>
        <span class="lang-switch" aria-label="${t("language")}"></span>
      </span>
    </div>`;
  langSwitch(el.querySelector(".lang-switch"));
}
