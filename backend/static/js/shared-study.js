(function () {
  "use strict";

  function escapeMarkup(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[character]);
  }

  function prepareInvestmentCards(root = document) {
    const table = root.querySelector(".financial-study-part2-table");
    let cards = root.querySelector(".financial-study-part2-mobile");
    const rows = [...(table?.tBodies?.[0]?.rows || [])];
    const headings = [...(table?.tHead?.rows?.[0]?.cells || [])].map((cell) => cell.textContent.trim());
    if (!table || !rows.length || headings.length < 5) return;
    if (!cards) {
      cards = document.createElement("div");
      cards.className = "financial-study-part2-mobile";
      cards.setAttribute("aria-label", "Simulação de investimento em cartões");
      table.closest(".financial-study-part2-table-wrap")?.after(cards);
    }
    if (!cards) return;

    const firstCells = [...rows[0].cells];
    const resourceUse = firstCells[0]?.textContent.trim() || "";
    const redemption = firstCells[1]?.textContent.trim() || "";
    const annualReturn = firstCells[2]?.textContent.trim() || "";
    cards.innerHTML = rows.map((row, index) => {
      const cells = [...row.cells];
      const termCell = index === 0 ? cells[3] : cells[0];
      const costCell = index === 0 ? cells[4] : cells[1];
      const values = [
        [headings[0], resourceUse],
        [headings[1], redemption],
        [headings[2], annualReturn],
        [headings[3], termCell?.textContent.trim() || ""],
        [headings[4], costCell?.textContent.trim() || ""],
      ];
      return `<article class="financial-study-part2-card"><h3>${escapeMarkup(resourceUse)} · ${escapeMarkup(termCell?.textContent.trim() || "")}</h3><dl>${values.map(([label, value]) => `<div><dt>${escapeMarkup(label)}</dt><dd>${escapeMarkup(value)}</dd></div>`).join("")}</dl></article>`;
    }).join("");
    if (cards.childElementCount) {
      cards.dataset.ready = "true";
      table.closest(".financial-study-part2-table-wrap")?.classList.add("has-mobile-cards");
    }
  }

  function annotateMissingValues(root = document) {
    const study = root.matches?.(".financial-study-document") ? root : root.querySelector(".financial-study-document");
    if (!study) return;
    study.querySelectorAll("td, dd, span").forEach((element) => {
      const value = element.textContent.trim();
      if (value !== "-" && !/^não informado$/i.test(value)) return;
      element.classList.add("financial-study-missing-value");
      element.setAttribute("aria-label", "Dado não informado");
    });
  }

  function buildPublicStudyNavigation() {
    const documentNode = document.querySelector(".financial-study-document");
    const nav = document.getElementById("sharedStudyNavigation");
    if (!documentNode || !nav) return;

    const sections = [...documentNode.querySelectorAll(":scope > .financial-study-part")];
    nav.innerHTML = `<strong class="shared-study-navigation-label">Navegar pelo estudo</strong><div class="shared-study-navigation-links">${sections.map((section, index) => {
      const heading = section.querySelector("h1, h2, h3");
      if (!heading) return "";
      if (!heading.id) heading.id = `shared-study-section-${index + 1}`;
      return `<a class="shared-study-navigation-button" href="#${escapeMarkup(heading.id)}" aria-label="Ir para ${escapeMarkup(heading.textContent.trim())}">${escapeMarkup(heading.textContent.trim())}</a>`;
    }).join("")}</div>`;
    const links = [...nav.querySelectorAll(".shared-study-navigation-button")];
    const markActive = (activeLink) => {
      links.forEach((link) => {
        if (link === activeLink) {
          link.setAttribute("aria-current", "location");
          if (window.matchMedia("(max-width: 760px)").matches) link.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
        } else {
          link.removeAttribute("aria-current");
        }
      });
    };
    links.forEach((link) => link.addEventListener("click", () => markActive(link)));
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver((entries) => {
        const visible = entries.filter((entry) => entry.isIntersecting).sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
        if (!visible) return;
        const activeLink = links.find((link) => link.hash === `#${visible.target.id}`);
        if (activeLink) markActive(activeLink);
      }, { rootMargin: "-15% 0px -70% 0px", threshold: [0, 0.15, 0.4] });
      sections.forEach((section) => observer.observe(section));
    }

  }

  window.prepareFinancialStudyMobileViews = function (root = document) {
    prepareInvestmentCards(root);
    annotateMissingValues(root);
  };

  document.addEventListener("DOMContentLoaded", () => {
    prepareInvestmentCards();
    annotateMissingValues();
    buildPublicStudyNavigation();
    document.getElementById("printSharedStudy")?.addEventListener("click", () => window.print());
  });
})();
