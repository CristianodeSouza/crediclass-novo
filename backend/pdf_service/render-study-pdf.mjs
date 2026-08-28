import React from "react";
import {
  Document,
  Font,
  Page,
  StyleSheet,
  Text,
  View,
  renderToBuffer,
} from "@react-pdf/renderer";

Font.registerHyphenationCallback((word) => [word]);

const styles = StyleSheet.create({
  page: {
    paddingTop: 32,
    paddingBottom: 36,
    paddingHorizontal: 30,
    fontSize: 10,
    color: "#24313a",
    fontFamily: "Helvetica",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 14,
  },
  brand: {
    width: "28%",
  },
  brandTitle: {
    fontSize: 22,
    letterSpacing: 1,
    marginBottom: 3,
  },
  brandSubtitle: {
    fontSize: 8,
    color: "#b6734d",
  },
  headerCenter: {
    width: "44%",
    textAlign: "center",
    fontSize: 9,
    color: "#95a1aa",
    paddingTop: 6,
  },
  headerRight: {
    width: "28%",
    textAlign: "right",
    fontSize: 9,
    color: "#95a1aa",
    paddingTop: 6,
  },
  titleBar: {
    backgroundColor: "#31424b",
    color: "#fff",
    textAlign: "center",
    fontSize: 11,
    fontWeight: 700,
    paddingVertical: 4,
    marginBottom: 10,
  },
  section: {
    marginBottom: 10,
  },
  sectionTitle: {
    backgroundColor: "#31424b",
    color: "#fff",
    textAlign: "center",
    fontSize: 10,
    fontWeight: 700,
    paddingVertical: 4,
    marginBottom: 8,
  },
  paragraph: {
    fontSize: 10,
    lineHeight: 1.45,
    marginBottom: 6,
  },
  metaGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  metaCard: {
    width: "48%",
    borderWidth: 1,
    borderColor: "#d8dde3",
    padding: 8,
    marginBottom: 8,
  },
  metaLabel: {
    fontSize: 8,
    textTransform: "uppercase",
    color: "#66707a",
    marginBottom: 3,
  },
  metaValue: {
    fontSize: 11,
    fontWeight: 700,
  },
  table: {
    display: "table",
    width: "100%",
    borderWidth: 1,
    borderColor: "#d8dde3",
  },
  row: {
    flexDirection: "row",
  },
  headCell: {
    backgroundColor: "#efefef",
    fontWeight: 700,
  },
  cell: {
    borderRightWidth: 1,
    borderBottomWidth: 1,
    borderColor: "#d8dde3",
    paddingVertical: 5,
    paddingHorizontal: 6,
    fontSize: 9,
  },
  lastCell: {
    borderRightWidth: 0,
  },
  footer: {
    position: "absolute",
    left: 30,
    right: 30,
    bottom: 18,
    flexDirection: "row",
    justifyContent: "space-between",
    fontSize: 9,
    color: "#52616b",
  },
  bullet: {
    marginBottom: 4,
    fontSize: 10,
    lineHeight: 1.35,
  },
  alert: {
    marginTop: 8,
    padding: 8,
    borderWidth: 1,
    borderColor: "#f0d7bd",
    backgroundColor: "#fff8f2",
    fontSize: 9,
    color: "#8a4b08",
  },
});

function text(value) {
  return String(value ?? "-").trim() || "-";
}

function formatDate(value) {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return text(value);
  return new Intl.DateTimeFormat("pt-BR").format(parsed);
}

function Header({ pageNumber }) {
  return React.createElement(
    View,
    { style: styles.header, fixed: true },
    React.createElement(
      View,
      { style: styles.brand },
      React.createElement(Text, { style: styles.brandTitle }, "CREDICLASS"),
      React.createElement(Text, { style: styles.brandSubtitle }, "AQUISIÇÕES INTELIGENTES"),
    ),
    React.createElement(Text, { style: styles.headerCenter }, "Estudo Financeiro | Aquisição de Imóvel"),
    React.createElement(Text, { style: styles.headerRight }, `Página ${pageNumber}`),
  );
}

function Footer({ payload, pageNumber, totalPages }) {
  return React.createElement(
    View,
    { style: styles.footer, fixed: true },
    React.createElement(Text, null, formatDate(payload.meta.generatedAt)),
    React.createElement(Text, null, `Validade: ${text(payload.meta.validityDays)} dias após o recebimento`),
    React.createElement(Text, null, `${pageNumber} de ${totalPages}`),
  );
}

function Section({ title, children }) {
  return React.createElement(
    View,
    { style: styles.section },
    React.createElement(Text, { style: styles.sectionTitle }, title),
    children,
  );
}

function SummaryTable({ rows, columns }) {
  return React.createElement(
    View,
    { style: styles.table },
    React.createElement(
      View,
      { style: styles.row },
      ...columns.map((column, index) =>
        React.createElement(
          Text,
          {
            key: column.key,
            style: [
              styles.cell,
              styles.headCell,
              { width: column.width },
              index === columns.length - 1 ? styles.lastCell : null,
            ],
          },
          column.label,
        ),
      ),
    ),
    ...rows.map((row, rowIndex) =>
      React.createElement(
        View,
        { key: `row-${rowIndex}`, style: styles.row },
        ...columns.map((column, index) =>
          React.createElement(
            Text,
            {
              key: `${rowIndex}-${column.key}`,
              style: [
                styles.cell,
                { width: column.width },
                index === columns.length - 1 ? styles.lastCell : null,
                rowIndex === rows.length - 1 ? { borderBottomWidth: 0 } : null,
              ],
            },
            text(row[column.key]),
          ),
        ),
      ),
    ),
  );
}

function StudyDocument({ payload }) {
  const pages = [
    {
      title: "ESTUDO FINANCEIRO",
      content: [
        React.createElement(Text, { key: "p1", style: styles.paragraph }, `Cliente: ${text(payload.client.name)}`),
        React.createElement(Text, { key: "p2", style: styles.paragraph }, `Objetivo: ${text(payload.client.objective)}`),
        React.createElement(Text, { key: "p3", style: styles.paragraph }, `Proposta: ${text(payload.meta.proposalId)}`),
        React.createElement(
          View,
          { key: "grid", style: styles.metaGrid },
          ...[
            ["Crédito desejado", payload.client.desiredCredit],
            ["Prazo desejado", payload.client.desiredTerm],
            ["Parcela desejada", payload.client.desiredInstallment],
            ["Renda total", payload.client.income],
            ["Administradora", payload.group.administrator],
            ["Grupo", payload.group.groupId],
            ["Estratégia recomendada", payload.financial.recommendedStrategy],
            ["Chance", payload.financial.chance],
          ].map(([label, value], index) =>
            React.createElement(
              View,
              { key: `meta-${index}`, style: styles.metaCard },
              React.createElement(Text, { style: styles.metaLabel }, label),
              React.createElement(Text, { style: styles.metaValue }, text(value)),
            ),
          ),
        ),
      ],
    },
    {
      title: "RESUMO FINANCEIRO",
      content: [
        React.createElement(
          SummaryTable,
          {
            key: "financial-table",
            columns: [
              { key: "label", label: "Indicador", width: "38%" },
              { key: "value", label: "Valor", width: "62%" },
            ],
            rows: [
              { label: "Crédito líquido", value: payload.financial.credit },
              { label: "Crédito contratado", value: payload.financial.contractedCredit },
              { label: "Recurso próprio", value: payload.financial.ownResources },
              { label: "FGTS", value: payload.financial.fgts },
              { label: "Lance embutido", value: payload.financial.embeddedBid },
              { label: "Lance total", value: payload.financial.totalBid },
              { label: "Percentual do lance", value: payload.financial.bidPercent },
              { label: "Parcela inicial", value: payload.financial.initialInstallment },
              { label: "Custo efetivo total", value: payload.financial.effectiveTotalCost },
            ],
          },
        ),
        ...(payload.financial.alerts || []).length
          ? [
              React.createElement(
                View,
                { key: "alerts", style: styles.alert },
                React.createElement(Text, null, `Alertas: ${payload.financial.alerts.join(" | ")}`),
              ),
            ]
          : [],
      ],
    },
    {
      title: "ESTRATÉGIAS OPERACIONAIS",
      content: [
        React.createElement(
          SummaryTable,
          {
            key: "strategy-table",
            columns: [
              { key: "label", label: "Estratégia", width: "22%" },
              { key: "bidPercent", label: "% Lance", width: "12%" },
              { key: "ownBid", label: "Rec. próprio", width: "18%" },
              { key: "embeddedBid", label: "Embutido", width: "15%" },
              { key: "creditAvailable", label: "Crédito", width: "18%" },
              { key: "operationalWindow", label: "Janela", width: "15%" },
            ],
            rows: payload.sections.strategyRows || [],
          },
        ),
      ],
    },
    {
      title: "HISTÓRICO E OBSERVAÇÕES",
      content: [
        React.createElement(
          SummaryTable,
          {
            key: "history-table",
            columns: [
              { key: "month", label: "Período", width: "28%" },
              { key: "lowestBid", label: "Menor lance", width: "24%" },
              { key: "highestBid", label: "Maior lance", width: "24%" },
              { key: "contemplations", label: "Contemplações", width: "24%" },
            ],
            rows: payload.sections.historyRows?.length
              ? payload.sections.historyRows
              : [{ month: "Sem histórico", lowestBid: "-", highestBid: "-", contemplations: "-" }],
          },
        ),
        ...((payload.sections.operatorNotes || []).length
          ? [
              React.createElement(
                Section,
                { key: "notes", title: "NOTAS DO OPERADOR" },
                React.createElement(
                  View,
                  null,
                  ...(payload.sections.operatorNotes || []).map((item, index) =>
                    React.createElement(Text, { key: `note-${index}`, style: styles.bullet }, `- ${text(item)}`),
                  ),
                ),
              ),
            ]
          : []),
      ],
    },
  ];
  const totalPages = pages.length;
  return React.createElement(
    Document,
    {
      title: `Estudo ${text(payload.meta.proposalId)}`,
      author: "Crediclass",
      subject: "Estudo Financeiro",
      creator: "Crediclass React-pdf Service",
      producer: "Crediclass React-pdf Service",
    },
    ...pages.map((page, index) =>
      React.createElement(
        Page,
        { key: `page-${index}`, size: "A4", style: styles.page, wrap: true },
        React.createElement(Header, { pageNumber: index + 1 }),
        React.createElement(View, { style: styles.titleBar }, React.createElement(Text, null, page.title)),
        ...page.content,
        React.createElement(Footer, { payload, pageNumber: index + 1, totalPages }),
      ),
    ),
  );
}

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString("utf8");
}

async function main() {
  const raw = await readStdin();
  const payload = JSON.parse(raw || "{}");
  const document = React.createElement(StudyDocument, { payload });
  const buffer = await renderToBuffer(document);
  process.stdout.write(buffer);
}

main().catch((error) => {
  process.stderr.write(`${error?.stack || error?.message || String(error)}\n`);
  process.exit(1);
});
