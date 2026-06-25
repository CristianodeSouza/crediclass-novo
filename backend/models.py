from typing import Any, Literal

from pydantic import BaseModel, Field


class GrupoResumo(BaseModel):
    grupo_id: str
    administradora_id: str = ""
    administradora: str = ""
    grupo: str = ""
    tipo_bem: str = ""
    credito_minimo: float | None = None
    credito_maximo: float | None = None
    taxa_adm: float | None = None
    prazo_total: int | None = None
    primeira_assembleia: str = ""
    ultima_assembleia: str = ""
    status: str = "Ativo"
    lance_super_conservador: float | None = None
    lance_conservador: float | None = None
    lance_moderado: float | None = None
    lance_agressivo: float | None = None
    lance_super_agressivo_3m: float | None = None
    lance_agressivo_6m: float | None = None
    lance_moderado_12m: float | None = None
    lance_conservador_24m: float | None = None


class HistoricoMensal(BaseModel):
    maior_lance: float | None = None
    menor_lance: float | None = None
    qtd_contemplacoes: int | None = None


class HistoricoUpdateRequest(BaseModel):
    mes: str = Field(pattern=r"^\d{4}-\d{2}$")
    maior_lance: float | None = Field(default=None, ge=0)
    menor_lance: float | None = Field(default=None, ge=0)
    qtd_contemplacoes: int | None = Field(default=None, ge=0)


class HistoricoBatchUpdateRequest(BaseModel):
    items: list[HistoricoUpdateRequest] = Field(default_factory=list, min_length=1)


class GrupoDetalhe(GrupoResumo):
    fundo_reserva: float | None = None
    prazo_restante: int | None = None
    data_termino: str = ""
    proxima_assembleia: str = ""
    limite_adesao: str = ""
    vencimento_primeira_parcela: str = ""
    seguro_garantia: bool | None = None
    meia_parcela: bool | None = None
    lance_embutido: bool | None = None
    fgts: bool | None = None
    categoria: str = ""
    percentual_lance_embutido: float | None = None
    percentual_lance_fixo: float | None = None
    investidor: float | None = None
    conservador: float | None = None
    moderado: float | None = None
    agressivo: float | None = None
    super_agressivo: float | None = None
    lance_investidor: float | None = None
    lance_super_conservador: float | None = None
    lance_conservador: float | None = None
    lance_moderado: float | None = None
    lance_agressivo: float | None = None
    lance_super_agressivo_3m: float | None = None
    lance_agressivo_6m: float | None = None
    lance_moderado_12m: float | None = None
    lance_conservador_24m: float | None = None
    parcela_reduzida: str = ""
    percentual_parcela_reduzida: float | None = None
    idade_maxima: int | None = None
    observacoes: str = ""
    indice_correcao: str = ""
    vencimento_parcela: str = ""
    vencimento_lance: str = ""
    regras_especiais: str = ""
    cadastrado_por: str = ""
    ultima_atualizacao: str = ""
    campos_planilha: dict[str, Any] = Field(default_factory=dict)
    historico: dict[str, HistoricoMensal] = Field(default_factory=dict)
    auditoria: list[dict[str, Any]] = Field(default_factory=list)


class GruposResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_administradoras: int = 0
    administradoras: list[str] = Field(default_factory=list)
    tipos_bem: list[str] = Field(default_factory=list)
    items: list[GrupoResumo] = Field(default_factory=list)


class GrupoCreateRequest(BaseModel):
    administradora: str = ""
    grupo: str = ""
    tipo_bem: str = ""
    credito_minimo: float | None = Field(default=None, ge=0)
    credito_maximo: float | None = Field(default=None, ge=0)
    taxa_adm: float | None = Field(default=None, ge=0)
    prazo_total: int | None = Field(default=None, ge=0)
    status: str = "Ativo"


class GrupoUpdateRequest(BaseModel):
    administradora: str | None = None
    grupo: str | None = None
    tipo_bem: str | None = None
    credito_minimo: float | None = Field(default=None, ge=0)
    credito_maximo: float | None = Field(default=None, ge=0)
    taxa_adm: float | None = Field(default=None, ge=0)
    prazo_total: int | None = Field(default=None, ge=0)
    status: str | None = None
    campos_planilha: dict[str, Any] | None = None


class SuccessResponse(BaseModel):
    success: bool = True


class GrupoCreateResponse(SuccessResponse):
    grupo_id: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: str


class AdministradoraV4(BaseModel):
    administradora_id: str
    nome: str
    status: str = "Ativo"
    possui_template: bool = False
    template_padrao_id: str = ""
    observacoes: str = ""


class ClienteV4(BaseModel):
    cliente_id: str
    nome: str = ""
    nome_conjuge: str = ""
    data_nascimento_titular: str = ""
    data_nascimento_conjuge: str = ""
    renda_titular: float = Field(default=0, ge=0)
    renda_conjuge: float = Field(default=0, ge=0)
    renda_total: float = Field(default=0, ge=0)
    fgts_titular: float = Field(default=0, ge=0)
    fgts_conjuge: float = Field(default=0, ge=0)
    fgts_total: float = Field(default=0, ge=0)
    observacoes: str = ""


class CenarioViabilidadeV4(BaseModel):
    cenario_id: str
    cliente_id: str
    objetivo: str = ""
    tipo_bem: str = ""
    estado_bem: str = ""
    credito_desejado: float = Field(gt=0)
    prazo_desejado: int = Field(gt=0)
    lance_proprio: float = Field(default=0, ge=0)
    fgts_total: float = Field(default=0, ge=0)
    recurso_total_disponivel: float = Field(default=0, ge=0)
    renda_total: float = Field(default=0, ge=0)
    parcela_maxima_desejada: float = Field(default=0, ge=0)
    perfil: str = ""
    cenario_viavel: bool = False
    created_at: str = ""


class EstrategiaV4(BaseModel):
    estrategia_id: str
    cenario_id: str
    grupo_id: str
    nome: str
    tipo: str
    percentual_lance: float = Field(default=0, ge=0)
    valor_lance: float = Field(default=0, ge=0)
    credito_contratado: float = Field(default=0, ge=0)
    lance_embutido: float = Field(default=0, ge=0)
    fgts_utilizado: float = Field(default=0, ge=0)
    recurso_proprio: float = Field(default=0, ge=0)
    credito_disponivel: float = Field(default=0, ge=0)
    parcela_estimada: float = Field(default=0, ge=0)
    prazo_estimado: int = Field(default=0, ge=0)
    chance_contemplacao: str = ""
    score: float = Field(default=0, ge=0, le=100)
    selo: str = ""
    recomendada: bool = False
    alternativa: bool = False
    aprovada: bool = False
    justificativa: list[str] = Field(default_factory=list)
    alertas: list[str] = Field(default_factory=list)
    motivos_reprovacao: list[str] = Field(default_factory=list)


class CampoTemplateV4(BaseModel):
    campo_id: str
    label: str
    tipo: str = "text"
    origem: str = ""
    classificacao: Literal["AUTO", "OPERADOR", "HIBRIDO"]
    editavel: bool = False
    obrigatorio: bool = False


class TemplateEstudoV4(BaseModel):
    template_id: str
    administradora_id: str
    nome: str
    versao: str
    status: str = "Ativo"
    campos: list[CampoTemplateV4] = Field(default_factory=list)


class TextoAdministradoraV4(BaseModel):
    texto_id: str
    administradora_id: str
    tipo: Literal[
        "Institucional",
        "Beneficio",
        "CriterioSelecao",
        "ObservacaoPadrao",
        "Alerta",
        "Rodape",
    ]
    titulo: str = ""
    conteudo: str
    status: str = "Ativo"


class EstudoFinanceiroV4(BaseModel):
    estudo_id: str
    cliente_id: str
    cenario_id: str
    grupo_id: str
    estrategia_id: str
    template_id: str
    administradora_id: str
    status: Literal[
        "Rascunho",
        "Pronto para Revisao",
        "Aprovado para Envio",
        "Enviado ao Cliente",
        "Cancelado",
    ] = "Rascunho"
    completeness: float = Field(default=0, ge=0, le=1)
    criado_por: str = ""
    created_at: str = ""
    updated_at: str = ""


class VersaoEstudoV4(BaseModel):
    versao_id: str
    estudo_id: str
    numero: int = Field(ge=1)
    dados: dict[str, Any] = Field(default_factory=dict)
    criado_por: str = ""
    created_at: str = ""


class AuditoriaV4(BaseModel):
    auditoria_id: str
    usuario_id: str
    entidade: str
    entidade_id: str
    acao: str
    campo: str = ""
    valor_anterior: Any = None
    valor_novo: Any = None
    origem: Literal["AUTO", "OPERADOR", "HIBRIDO"] | None = None
    created_at: str = ""


class ViabilidadeRequest(BaseModel):
    objetivo: str
    credito_desejado: float = Field(gt=0)
    prazo_desejado: int = Field(gt=0)
    lance_proprio: float = Field(ge=0)
    fgts: float = Field(ge=0)
    renda_total: float = Field(gt=0)
    parcela_desejada: float = Field(gt=0)
    parcela_ideal: float | None = Field(default=None, gt=0)
    parcela_limite: float | None = Field(default=None, gt=0)
    fgts_titular: float | None = Field(default=None, ge=0)
    fgts_conjuge: float | None = Field(default=None, ge=0)
    renda_titular: float | None = Field(default=None, ge=0)
    renda_conjuge: float | None = Field(default=None, ge=0)
    data_nascimento: str = ""
    data_nascimento_conjuge: str = ""
    tipo_bem: str = "Imovel"
    estado_bem: str = ""
    considerar_lance_embutido: bool = True


class ViabilidadeHistorico(BaseModel):
    media_maior_lance: float | None = None
    media_menor_lance: float | None = None
    media_qtd_contemplacoes: float | None = None
    total_contemplacoes: int = 0


class ViabilidadeGrupo(BaseModel):
    ranking: int
    grupo_aprovado: bool
    grupo_id: str
    administradora: str
    grupo: str = ""
    tipo_bem: str = ""
    credito_minimo: float | None = None
    credito_maximo: float | None = None
    credito: float
    credito_desejado: float
    credito_contratado: float
    credito_disponivel: float
    lance_embutido_utilizado: float
    fgts_utilizado: float
    lance_proprio_utilizado: float
    lance_total: float
    percentual_lance: float
    taxa_administrativa_valor: float
    fundo_reserva_valor: float
    parcela_estimada: float
    lance_sugerido_percentual: float | None = None
    lance_sugerido_valor: float | None = None
    lance_referencia_percentual: float | None = None
    perfil_prazo_operacional: str = ""
    prazo_minimo: float | None = None
    taxa_adm: float | None = None
    fundo_reserva: float | None = None
    prazo: int
    afinidade: float
    selo: str
    historico_12m: ViabilidadeHistorico
    alertas: list[str] = Field(default_factory=list)
    motivos: list[str] = Field(default_factory=list)


class ViabilidadeChecklist(BaseModel):
    idade_compativel: bool
    renda_compativel: bool
    parcela_compativel: bool
    lance_compativel: bool
    fgts_permitido: bool
    lance_embutido_permitido: bool
    prazo_compativel: bool
    tipo_bem_compativel: bool
    cenario_viavel: bool


class AdministradoraViabilidade(BaseModel):
    administradora: str
    seguro_obrigatorio: bool = False
    idade_maxima: int | None = None
    limite_sem_comprovacao_renda: float | None = None
    percentual_lance_embutido: float = 0
    tipo_lance_embutido: str = "Credito"
    credito_a_contratar: float
    lance_embutido_valor: float
    lance_proprio: float
    fgts_utilizado: float
    lance_total: float
    lance_maximo_percentual: float
    taxa_adm: float
    fundo_reserva: float
    prazo_minimo: float
    renda_compativel: bool
    idade_compativel: bool
    parcela_compativel: bool
    limite_sem_comprovacao_compativel: bool
    fgts_permitido: bool
    lance_embutido_permitido: bool
    elegivel: bool
    alertas: list[str] = Field(default_factory=list)


class ViabilidadeResponse(BaseModel):
    cenario_viavel: bool
    total_grupos_encontrados: int
    total_grupos_analisados: int
    total_grupos_compativeis: int
    total_administradoras_analisadas: int = 0
    total_administradoras_elegiveis: int = 0
    perfil: str
    perfil_prazo_operacional: str = ""
    fgts_total: float
    lance_total_disponivel: float
    renda_total: float
    estado_bem: str
    idade_titular: int | None = None
    idade_conjuge: int | None = None
    idade_validada: bool
    idade_alerta: str = ""
    cenario: str
    motivos_reprovacao: list[str] = Field(default_factory=list)
    checklist: ViabilidadeChecklist
    administradoras_viabilidade: list[AdministradoraViabilidade] = Field(default_factory=list)
    melhores_grupos: list[ViabilidadeGrupo] = Field(default_factory=list)


class EstudoCliente(BaseModel):
    nome: str = ""
    nome_conjuge: str = ""
    tipo_contratacao: str = ""
    titulares: dict[str, Any] = Field(default_factory=dict)
    credito_desejado: float = Field(gt=0)
    objetivo: str = ""
    prazo_desejado: int | None = Field(default=None, gt=0)
    lance_proprio: float | None = Field(default=None, ge=0)
    fgts: float | None = Field(default=None, ge=0)
    renda_total: float | None = Field(default=None, ge=0)
    parcela_desejada: float | None = Field(default=None, ge=0)
    data_nascimento: str = ""
    data_nascimento_conjuge: str = ""
    estado_bem: str = ""


class EstudoRequest(BaseModel):
    cliente: EstudoCliente
    grupo_id: str
    cenario: dict[str, Any] | None = None
    template_campos: dict[str, str] = Field(default_factory=dict)


class EstudoCreateResponse(BaseModel):
    estudo_id: str
    success: bool = True


class EstudoResumo(BaseModel):
    estudo_id: str
    criado_em: str
    cliente: dict = Field(default_factory=dict)
    grupo: dict = Field(default_factory=dict)
    financeiro: dict = Field(default_factory=dict)
    estrategia: str = "Lance Total"
    status: str = "Em andamento"
    operador: str = "Joyce"


class EstudosResponse(BaseModel):
    total: int
    items: list[EstudoResumo] = Field(default_factory=list)
