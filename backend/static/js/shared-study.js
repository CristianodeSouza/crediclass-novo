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

  function repositionScenarioSummaries(root = document) {
    const content = root.querySelector("#financialStudyPart10Content, .financial-study-part10-content");
    if (!content) return;
    const directSections = [...content.children].filter((element) => element.matches(".financial-study-part10-profile"));
    const summaries = directSections.filter((section) => {
      const title = section.querySelector(":scope > h3")?.textContent.trim().toLowerCase() || "";
      return title.startsWith("resumo do cenário") || title === "recursos compartilhados";
    });
    const summaryNote = root.querySelector(".financial-study-part4-source-note");
    if (summaries.length && summaryNote?.parentElement) {
      let anchor = summaryNote;
      summaries.forEach((section) => {
        anchor.parentElement.insertBefore(section, anchor.nextSibling);
        anchor = section;
      });
      return;
    }
    const projectionStart = content.querySelector(":scope > .financial-study-part10-lottery") || directSections.find((section) => !summaries.includes(section));
    if (!summaries.length || !projectionStart) return;
    summaries.forEach((section) => content.insertBefore(section, projectionStart));
  }

  window.prepareFinancialStudyMobileViews = function (root = document) {
    prepareInvestmentCards(root);
    annotateMissingValues(root);
  };

  async function downloadSharedStudyPdf(button) {
    const token = window.location.pathname.split("/").filter(Boolean).pop();
    if (!token) throw new Error("Link público inválido.");
    const endpoint = `/estudo-compartilhado/${encodeURIComponent(token)}/pdf`;
    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = "Gerando PDF...";
    try {
      const startResponse = await fetch(endpoint, { headers: { Accept: "application/json" } });
      const startPayload = await startResponse.json();
      if (!startResponse.ok || !startPayload.job_id) {
        throw new Error(startPayload.error || "Não foi possível iniciar a geração do PDF.");
      }
      let pdfResponse;
      for (let attempt = 0; attempt < 90; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        pdfResponse = await fetch(`${endpoint}?job=${encodeURIComponent(startPayload.job_id)}`, { headers: { Accept: "application/pdf" } });
        if (pdfResponse.status === 202) continue;
        if (!pdfResponse.ok) throw new Error("Não foi possível gerar o PDF.");
        const blob = await pdfResponse.blob();
        const disposition = pdfResponse.headers.get("content-disposition") || "";
        const encodedFilename = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
        const fallbackFilename = disposition.match(/filename="([^"]+)"/i)?.[1] || "estudo-financeiro.pdf";
        const filename = encodedFilename ? decodeURIComponent(encodedFilename) : fallbackFilename;
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
        return;
      }
      throw new Error("A geração do PDF demorou mais que o esperado.");
    } finally {
      button.disabled = false;
      button.textContent = originalLabel;
    }
  }

  function setupPublicStudyAgreement() {
    const panel = document.getElementById("publicStudyAgreement");
    const checkbox = document.getElementById("publicStudyAgreementCheckbox");
    const submit = document.getElementById("publicStudyAgreementSubmit");
    const status = document.getElementById("publicStudyAgreementStatus");
    const followup = document.getElementById("publicStudyRegistration");
    if (!panel || !checkbox || !submit || !status) return;
    const showFollowup = () => { if (followup) followup.hidden = false; };
    if (panel.dataset.agreementStatus === "agreed") {
      checkbox.checked = true;
      checkbox.disabled = true;
      submit.disabled = true;
      status.textContent = "Acordo já registrado para este estudo.";
      status.classList.add("is-success");
      showFollowup();
      return;
    }
    checkbox.addEventListener("change", () => { submit.disabled = !checkbox.checked; });
    submit.addEventListener("click", async () => {
      if (!checkbox.checked) return;
      submit.disabled = true;
      checkbox.disabled = true;
      status.textContent = "Registrando acordo...";
      status.classList.remove("is-success", "is-error");
      try {
        const response = await fetch(`/api/estudo-compartilhado/${encodeURIComponent(panel.dataset.studyToken)}/acordo`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ agreed: true }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.error || "Não foi possível registrar o acordo.");
        panel.dataset.agreementStatus = "agreed";
        showFollowup();
        status.textContent = `Acordo registrado em ${new Date(payload.agreed_at).toLocaleString("pt-BR")}.`;
        status.classList.add("is-success");
      } catch (error) {
        checkbox.disabled = false;
        submit.disabled = false;
        status.textContent = error.message || "Não foi possível registrar o acordo.";
        status.classList.add("is-error");
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    repositionScenarioSummaries();
    prepareInvestmentCards();
    annotateMissingValues();
    setupPublicStudyAgreement();
    document.getElementById("printSharedStudy")?.addEventListener("click", async (event) => {
      try {
        await downloadSharedStudyPdf(event.currentTarget);
      } catch (error) {
        window.alert(error?.message || "Não foi possível baixar o PDF.");
      }
    });
  });
})();
