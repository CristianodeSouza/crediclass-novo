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
    const quickSummary = document.getElementById("sharedStudyQuickSummary");
    if (!documentNode || !nav || !quickSummary) return;

    const sections = [...documentNode.querySelectorAll(":scope > .financial-study-part")];
    nav.innerHTML = `<strong class="shared-study-navigation-label">Neste estudo</strong><div class="shared-study-navigation-links">${sections.map((section, index) => {
      const heading = section.querySelector("h1, h2, h3");
      if (!heading) return "";
      if (!heading.id) heading.id = `shared-study-section-${index + 1}`;
      return `<a href="#${escapeMarkup(heading.id)}">${escapeMarkup(heading.textContent.trim())}</a>`;
    }).join("")}</div>`;

    const summaries = [...documentNode.querySelectorAll(".financial-study-part4-scenario-summary")];
    if (summaries.length) {
      quickSummary.innerHTML = summaries.map((summary) => {
        const title = summary.querySelector("h3")?.textContent.trim() || "Cenário";
        const values = [...summary.querySelectorAll(".financial-study-part4-overview article")];
        return `<section class="shared-study-summary-scenario"><h3>${escapeMarkup(title)}</h3><dl>${values.map((item) => `<div><dt>${escapeMarkup(item.querySelector("small")?.textContent.trim() || "")}</dt><dd>${escapeMarkup(item.querySelector("strong")?.textContent.trim() || "")}</dd></div>`).join("")}</dl></section>`;
      }).join("");
    } else {
      quickSummary.textContent = "Consulte o quadro-resumo completo na seção correspondente deste estudo.";
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
