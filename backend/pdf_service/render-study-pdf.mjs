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
    paddingTop: 26,
    paddingBottom: 28,
    paddingHorizontal: 24,
    fontSize: 8.8,
    color: "#24313a",
    fontFamily: "Helvetica",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 10,
  },
  brand: {
    width: "29%",
  },
  brandTitle: {
    fontSize: 18,
    letterSpacing: 0.9,
    color: "#2a3942",
    marginBottom: 1,
  },
  brandSubtitle: {
    fontSize: 6.6,
    color: "#b6734d",
  },
  headerCenter: {
    width: "42%",
    textAlign: "center",
    fontSize: 7.6,
    color: "#98a3ab",
    paddingTop: 5,
  },
  headerRight: {
    width: "28%",
    textAlign: "right",
    fontSize: 7.6,
    color: "#98a3ab",
    paddingTop: 5,
  },
  titleBar: {
    backgroundColor: "#31424b",
    color: "#fff",
    textAlign: "center",
    fontSize: 9.4,
    fontWeight: 700,
    paddingVertical: 3,
    marginBottom: 6,
  },
  section: {
    marginBottom: 7,
  },
  sectionTitle: {
    backgroundColor: "#31424b",
    color: "#fff",
    textAlign: "center",
    fontSize: 9.2,
    fontWeight: 700,
    paddingVertical: 3,
    marginBottom: 5,
  },
  paragraph: {
    fontSize: 8.8,
    lineHeight: 1.3,
    marginBottom: 4,
  },
  smallParagraph: {
    fontSize: 8.2,
    lineHeight: 1.22,
    marginBottom: 3,
  },
  metaGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    rowGap: 6,
    columnGap: 6,
  },
  metaCard: {
    width: "48.5%",
    borderWidth: 1,
    borderColor: "#d9e0e5",
    padding: 6,
  },
  metaLabel: {
    fontSize: 6.8,
    textTransform: "uppercase",
    color: "#66707a",
    marginBottom: 2,
  },
  metaValue: {
    fontSize: 8.9,
    fontWeight: 700,
    color: "#22313b",
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
  cell: {
    borderRightWidth: 1,
    borderBottomWidth: 1,
    borderColor: "#d8dde3",
    paddingVertical: 3.5,
    paddingHorizontal: 4.5,
    fontSize: 7.7,
    lineHeight: 1.15,
  },
  headCell: {
    backgroundColor: "#f2f4f6",
    fontWeight: 700,
  },
  leftCell: {
    fontWeight: 700,
    width: "21%",
  },
  rightCell: {
    width: "79%",
  },
  compactCell: {
    paddingVertical: 3,
    paddingHorizontal: 4,
    fontSize: 7.4,
  },
  lastCell: {
    borderRightWidth: 0,
  },
  lastRowCell: {
    borderBottomWidth: 0,
  },
  bullet: {
    fontSize: 8.4,
    lineHeight: 1.25,
    marginBottom: 3,
  },
  introBlock: {
    marginBottom: 6,
  },
  introLead: {
    fontSize: 8.8,
    fontWeight: 700,
    marginBottom: 4,
  },
  miniNote: {
    fontSize: 7.8,
    color: "#67717b",
    marginBottom: 4,
  },
  alert: {
    marginTop: 6,
    padding: 6,
    borderWidth: 1,
    borderColor: "#f0d7bd",
    backgroundColor: "#fff8f2",
    fontSize: 7.8,
    color: "#8a4b08",
  },
  subsectionLabel: {
    fontSize: 8.4,
    fontWeight: 700,
    marginBottom: 4,
  },
  emphasis: {
    fontWeight: 700,
  },
  historyGroupCell: {
    width: "16%",
  },
  footer: {
    position: "absolute",
    left: 24,
    right: 24,
    bottom: 12,
    flexDirection: "row",
    justifyContent: "space-between",
    fontSize: 7.6,
    color: "#52616b",
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
      React.createElement(Text, { style: styles.brandSubtitle }, "AQUISICOES INTELIGENTES"),
    ),
    React.createElement(Text, { style: styles.headerCenter }, "Estudo Financeiro | Aquisicao de Imovel"),
    React.createElement(Text, { style: styles.headerRight, render: ({ pageNumber: currentPage }) => `Pagina ${currentPage}` }),
  );
}

function Footer({ payload }) {
  return React.createElement(
    View,
    { style: styles.footer, fixed: true },
    React.createElement(Text, null, formatDate(payload.meta.generatedAt)),
    React.createElement(Text, null, `Validade: ${text(payload.meta.validityDays)} dias apos o recebimento`),
    React.createElement(Text, { render: ({ pageNumber, totalPages }) => `${pageNumber} de ${totalPages}` }),
  );
}

function Section({ title, children }) {
  return React.createElement(
    View,
    { style: styles.section, wrap: false },
    React.createElement(Text, { style: styles.sectionTitle }, title),
    children,
  );
}

function Table({ columns, rows, compact = false }) {
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
            key: `head-${column.key}`,
            style: [
              styles.cell,
              styles.headCell,
              compact ? styles.compactCell : null,
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
                compact ? styles.compactCell : null,
                { width: column.width },
                index === columns.length - 1 ? styles.lastCell : null,
                rowIndex === rows.length - 1 ? styles.lastRowCell : null,
              ],
            },
            text(row[column.key]),
          ),
        ),
      ),
    ),
  );
}

function IntroSection({ payload }) {
  return React.createElement(
    Section,
    { title: "ESTUDO FINANCEIRO" },
    React.createElement(
      View,
      { style: styles.introBlock },
      React.createElement(Text, { style: styles.introLead }, "Prezado,"),
      ...(payload.sections.introNotes || []).map((item, index) =>
        React.createElement(Text, { key: `intro-${index}`, style: styles.paragraph }, text(item)),
      ),
    ),
    React.createElement(
      View,
      { style: styles.metaGrid },
      ...[
        ["Cliente", payload.client.name],
        ["Objetivo", payload.client.objective],
        ["Proposta", payload.meta.proposalId],
        ["Administradora", payload.group.administrator],
        ["Grupo", payload.group.groupId],
        ["Credito desejado", payload.client.desiredCredit],
        ["Prazo desejado", `${text(payload.client.desiredTerm)} meses`],
        ["Parcela desejada", payload.client.desiredInstallment],
        ["Renda total", payload.client.income],
        ["Estrategia recomendada", payload.financial.recommendedStrategy],
      ].map(([label, value], index) =>
        React.createElement(
          View,
          { key: `meta-${index}`, style: styles.metaCard },
          React.createElement(Text, { style: styles.metaLabel }, label),
          React.createElement(Text, { style: styles.metaValue }, text(value)),
        ),
      ),
    ),
  );
}

function CompositionGroupSection({ group }) {
  return React.createElement(
    Section,
    { title: `COMPARATIVO AUDITADO — GRUPO ${text(group.groupId)}` },
    React.createElement(Text, { style: styles.miniNote }, `${text(group.administrator)} · ${text(group.quotas)} cota(s) · estratégia: ${text(group.strategy)}`),
    React.createElement(Table, {
      compact: true,
      columns: [
        { key: "label", label: "Cenário", width: "18%" },
        { key: "liquidCredit", label: "Crédito líquido", width: "20%" },
        { key: "contractedCredit", label: "Crédito contratado", width: "20%" },
        { key: "embeddedBid", label: "Lance embutido", width: "15%" },
        { key: "installment", label: "Parcela inicial", width: "14%" },
        { key: "balance", label: "Saldo devedor", width: "13%" },
      ],
      rows: [group.withoutEmbedded || {}, group.withEmbedded || {}],
    }),
  );
}

function InvestmentSection({ payload }) {
  return React.createElement(
    Section,
    { title: "SIMULACAO DE INVESTIMENTO" },
    React.createElement(
      Text,
      { style: styles.miniNote },
      "Simulacao dinamica usando o estudo atual e o grupo em destaque.",
    ),
    React.createElement(Table, {
      compact: true,
      columns: [
        { key: "resource", label: "Uso de Recurso Proprio", width: "24%" },
        { key: "baseValue", label: "Valor base", width: "18%" },
        { key: "initialInstallment", label: "Parcela inicial", width: "18%" },
        { key: "term", label: "Prazo em Meses", width: "12%" },
        { key: "periodCost", label: "Saldo / custo no periodo", width: "28%" },
      ],
      rows: [
        {
          resource: "A Vista",
          baseValue: payload.financial.ownResources,
          initialInstallment: "-",
          term: "1",
          periodCost: "-",
        },
        {
          resource: "Consorcio selecionado",
          baseValue: payload.financial.contractedCredit,
          initialInstallment: payload.financial.initialInstallment,
          term: payload.group.remainingTerm,
          periodCost: payload.financial.effectiveTotalCost,
        },
      ],
    }),
  );
}

function EditorialRowsSection({ payload }) {
  const sections = [
    {
      label: "Criterios de selecao",
      paragraphs: [
        "Os grupos apresentados foram selecionados a partir de criterios tecnicos definidos pela Crediclass, considerando indicadores historicos e condicoes disponiveis na data da analise.",
        ...(payload.sections.selectionCriteria || []),
      ],
    },
    {
      label: "Como funciona",
      paragraphs: payload.sections.howItWorks || [],
    },
    {
      label: "Contemplacoes Mensais",
      paragraphs: payload.sections.monthlyContemplations || [],
    },
    {
      label: "Uso da Carta de Credito",
      paragraphs: payload.sections.creditUses || [],
    },
  ];
  return React.createElement(
    Section,
    { title: "SIMULACAO MELHORES CONSORCIOS" },
    React.createElement(
      Text,
      { style: styles.paragraph },
      `Administradora selecionada: ${text(payload.group.administrator)}`,
    ),
    React.createElement(
      View,
      { style: styles.table },
      ...sections.flatMap((item, rowIndex) => [
        React.createElement(
          View,
          { key: `row-${rowIndex}`, style: styles.row },
          React.createElement(
            View,
            {
              style: [
                styles.cell,
                styles.leftCell,
                rowIndex === sections.length - 1 ? styles.lastRowCell : null,
              ],
            },
            React.createElement(Text, null, item.label),
          ),
          React.createElement(
            View,
            {
              style: [
                styles.cell,
                styles.rightCell,
                styles.lastCell,
                rowIndex === sections.length - 1 ? styles.lastRowCell : null,
              ],
            },
            ...(item.paragraphs || []).map((paragraph, index) =>
              React.createElement(
                Text,
                {
                  key: `${rowIndex}-${index}`,
                  style: index === item.paragraphs.length - 1 ? styles.smallParagraph : styles.smallParagraph,
                },
                text(paragraph),
              ),
            ),
          ),
        ),
      ]),
    ),
  );
}

function SpecialistsSection({ payload }) {
  return React.createElement(
    Section,
    { title: "ESPECIALISTAS EM TODA JORNADA" },
    React.createElement(
      View,
      { style: styles.table },
      ...(payload.sections.specialists || []).map((item, index, array) =>
        React.createElement(
          View,
          { key: `specialist-${index}`, style: styles.row },
          React.createElement(
            Text,
            {
              style: [
                styles.cell,
                styles.leftCell,
                index === array.length - 1 ? styles.lastRowCell : null,
              ],
            },
            `${text(item.label)}:`,
          ),
          React.createElement(
            Text,
            {
              style: [
                styles.cell,
                styles.rightCell,
                styles.lastCell,
                index === array.length - 1 ? styles.lastRowCell : null,
              ],
            },
            text(item.text),
          ),
        ),
      ),
    ),
  );
}

function BenefitsSection({ payload }) {
  return React.createElement(
    Section,
    { title: `${text(payload.group.administrator).toUpperCase()}\nPRINCIPAIS BENEFICIOS` },
    React.createElement(
      View,
      null,
      ...(payload.sections.benefits || []).map((item, index) =>
        React.createElement(Text, { key: `benefit-${index}`, style: styles.bullet }, `- ${text(item)}`),
      ),
    ),
  );
}

function ContractSection({ payload }) {
  return React.createElement(
    Section,
    { title: "CONTRATACAO" },
    React.createElement(Table, {
      compact: true,
      columns: [
        { key: "group", label: "Grupo", width: "22%" },
        { key: "credit", label: "Credito", width: "22%" },
        { key: "installment", label: "Parcelas (s/ seguro)", width: "24%" },
        { key: "term", label: "Prazo", width: "10%" },
        { key: "rateTotal", label: "Tx ADM Total", width: "12%" },
        { key: "rateYear", label: "Tx ADM ao Ano", width: "10%" },
      ],
      rows: payload.sections.contractRows || [],
    }),
  );
}

function StrategySection() {
  return React.createElement(
    Section,
    { title: "ESTRATEGIAS DE CONTEMPLACAO" },
    React.createElement(
      View,
      null,
      React.createElement(
        Text,
        { style: styles.paragraph },
        "Para sua comodidade, oferecemos o servico de consultoria, oferta de lance e acompanhamento mensal de contemplacao, conforme as estrategias sugeridas abaixo:",
      ),
      React.createElement(
        Text,
        { style: styles.bullet },
        "Estrategia 1) Investidor -> Sorteio + leitura da evolucao historica do grupo para preservar caixa e liquidez.",
      ),
      React.createElement(
        Text,
        { style: styles.bullet },
        "Estrategia 2) Conservadora -> Sorteio + lance livre conservador, observando um patamar que ja apareceu na serie historica.",
      ),
      React.createElement(
        Text,
        { style: styles.bullet },
        "Estrategia 3) Moderada -> Sorteio + lance livre moderado, aproximando a operacao do perfil classificado no estudo atual.",
      ),
      React.createElement(
        Text,
        { style: styles.smallParagraph },
        "As estrategias apresentadas possuem carater meramente ilustrativo e foram desenvolvidas com base em dados historicos dos grupos analisados.",
      ),
    ),
  );
}

function HistorySection({ payload }) {
  const matrix = payload.sections.historyMatrix || { months: [], rows: [] };
  const monthCount = Math.max(1, matrix.months?.length || 0);
  const monthWidth = `${84 / monthCount}%`;
  const columns = [
    { key: "group", label: "Grupo", width: "16%" },
    ...(matrix.months || []).map((month, index) => ({ key: `m${index}`, label: month, width: monthWidth })),
  ];
  const rows = (matrix.rows || []).map((row) => {
    const item = {
      group: `${text(row.group)}\n${text(row.administrator)}`,
    };
    (row.cells || []).forEach((cell, index) => {
      item[`m${index}`] = `${text(cell.value)}\n${text(cell.detail)}`;
    });
    return item;
  });
  return React.createElement(
    Section,
    { title: "HISTORICO DE LANCES CONTEMPLADOS" },
    React.createElement(Table, {
      compact: true,
      columns,
      rows: rows.length ? rows : [{ group: "Sem historico", m0: "-" }],
    }),
  );
}

function ProjectionSection({ payload }) {
  return React.createElement(
    Section,
    { title: "PROJECAO DE CONTEMPLACAO" },
    React.createElement(Table, {
      compact: true,
      columns: [
        { key: "title", label: "Estrategia", width: "22%" },
        { key: "percent", label: "Percentual", width: "12%" },
        { key: "totalBid", label: "Lance Total", width: "16%" },
        { key: "cardPayment", label: "Pagto Carta", width: "14%" },
        { key: "ownPayment", label: "Pagto Rec Proprio", width: "14%" },
        { key: "credit", label: "Credito", width: "12%" },
        { key: "installment", label: "Parcelas", width: "10%" },
      ],
      rows: payload.sections.projectionRows || [],
    }),
  );
}

function DeadlinesSection({ payload }) {
  return React.createElement(
    Section,
    { title: "DATAS LIMITES PARA ADESAO" },
    React.createElement(Table, {
      compact: true,
      columns: [
        { key: "group", label: "Grupo", width: "17%" },
        { key: "reservationLimit", label: "Limite Adesao - Reserva Vagas Grupos", width: "21%" },
        { key: "assemblyLimit", label: "Limite Adesao - Assembleia", width: "18%" },
        { key: "firstInstallment", label: "Vencimento Primeira Parcela", width: "18%" },
        { key: "nextAssembly", label: "Proxima Assembleia", width: "13%" },
        { key: "bidPayment", label: "Vencimento Pagamento Lance", width: "13%" },
      ],
      rows: payload.sections.deadlineRows || [],
    }),
  );
}

function OperatorNotesSection({ payload }) {
  if (!(payload.sections.operatorNotes || []).length) return null;
  return React.createElement(
    Section,
    { title: "NOTAS DO OPERADOR" },
    React.createElement(
      View,
      null,
      ...(payload.sections.operatorNotes || []).map((item, index) =>
        React.createElement(Text, { key: `note-${index}`, style: styles.bullet }, `- ${text(item)}`),
      ),
    ),
  );
}

function ConsiderationsSection({ payload }) {
  return React.createElement(
    Section,
    { title: "CONSIDERACOES IMPORTANTES" },
    React.createElement(
      View,
      null,
      ...(payload.sections.considerations || []).map((item, index) =>
        React.createElement(Text, { key: `consideration-${index}`, style: styles.paragraph }, text(item)),
      ),
    ),
  );
}

function FinancialSummarySection({ payload }) {
  return React.createElement(
    Section,
    { title: "RESUMO FINANCEIRO" },
    React.createElement(Table, {
      compact: true,
      columns: [
        { key: "label", label: "Indicador", width: "38%" },
        { key: "value", label: "Valor", width: "62%" },
      ],
      rows: [
        { label: "Credito liquido", value: payload.financial.credit },
        { label: "Credito contratado", value: payload.financial.contractedCredit },
        { label: "Recurso proprio", value: payload.financial.ownResources },
        { label: "FGTS", value: payload.financial.fgts },
        { label: "Lance embutido", value: payload.financial.embeddedBid },
        { label: "Lance total", value: payload.financial.totalBid },
        { label: "Percentual do lance", value: payload.financial.bidPercent },
        { label: "Parcela inicial", value: payload.financial.initialInstallment },
        { label: "Custo efetivo total", value: payload.financial.effectiveTotalCost },
        { label: "Chance", value: payload.financial.chance },
      ],
    }),
    ...(payload.financial.alerts || []).length
      ? [
          React.createElement(
            View,
            { key: "alerts", style: styles.alert },
            React.createElement(Text, null, `Alertas: ${payload.financial.alerts.join(" | ")}`),
          ),
        ]
      : [],
  );
}

function StrategyRowsSection({ payload }) {
  return React.createElement(
    Section,
    { title: "ESTRATEGIAS OPERACIONAIS" },
    React.createElement(Table, {
      compact: true,
      columns: [
        { key: "label", label: "Estrategia", width: "22%" },
        { key: "bidPercent", label: "% Lance", width: "12%" },
        { key: "ownBid", label: "Rec. proprio", width: "18%" },
        { key: "embeddedBid", label: "Embutido", width: "15%" },
        { key: "creditAvailable", label: "Credito", width: "18%" },
        { key: "operationalWindow", label: "Janela", width: "15%" },
      ],
      rows: payload.sections.strategyRows || [],
    }),
  );
}

function StudyDocument({ payload }) {
  const compositionPages = (payload.sections.compositionGroups || []).map((group, index) => ({
    title: null,
    content: [React.createElement(CompositionGroupSection, { key: `composition-${index}`, group })],
  }));
  const pages = [
    { title: null, content: [React.createElement(IntroSection, { key: "intro", payload })] },
    ...compositionPages,
    { title: null, content: [React.createElement(EditorialRowsSection, { key: "editorial", payload }), React.createElement(SpecialistsSection, { key: "specialists", payload })] },
    { title: null, content: [React.createElement(BenefitsSection, { key: "benefits", payload }), React.createElement(ContractSection, { key: "contract", payload }), React.createElement(StrategySection, { key: "narrative" })] },
    { title: null, content: [React.createElement(HistorySection, { key: "history", payload }), React.createElement(ProjectionSection, { key: "projection", payload })].filter(Boolean) },
    { title: null, content: [React.createElement(DeadlinesSection, { key: "deadlines", payload }), React.createElement(OperatorNotesSection, { key: "notes", payload }), React.createElement(ConsiderationsSection, { key: "considerations", payload })].filter(Boolean) },
  ];
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
        ...(page.title
          ? [React.createElement(View, { key: `title-${index}`, style: styles.titleBar }, React.createElement(Text, null, page.title))]
          : []),
        ...page.content,
        React.createElement(Footer, { payload }),
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
