from pydantic import BaseModel, Field


class GrupoResumo(BaseModel):
    grupo_id: str
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


class HistoricoMensal(BaseModel):
    maior_lance: float | None = None
    menor_lance: float | None = None
    qtd_contemplacoes: int | None = None


class HistoricoUpdateRequest(BaseModel):
    mes: str = Field(pattern=r"^\d{4}-\d{2}$")
    maior_lance: float | None = Field(default=None, ge=0)
    menor_lance: float | None = Field(default=None, ge=0)
    qtd_contemplacoes: int | None = Field(default=None, ge=0)


class GrupoDetalhe(GrupoResumo):
    fundo_reserva: float | None = None
    prazo_restante: int | None = None
    data_termino: str = ""
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
    parcela_reduzida: str = ""
    indice_correcao: str = ""
    vencimento_parcela: str = ""
    vencimento_lance: str = ""
    regras_especiais: str = ""
    cadastrado_por: str = ""
    ultima_atualizacao: str = ""
    historico: dict[str, HistoricoMensal] = Field(default_factory=dict)
    auditoria: list[dict[str, str]] = Field(default_factory=list)


class GruposResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[GrupoResumo] = Field(default_factory=list)


class GrupoCreateRequest(BaseModel):
    administradora: str
    grupo: str
    tipo_bem: str
    credito_minimo: float = Field(gt=0)
    credito_maximo: float = Field(gt=0)
    taxa_adm: float = Field(ge=0)
    prazo_total: int = Field(gt=0)


class GrupoUpdateRequest(BaseModel):
    administradora: str | None = None
    grupo: str | None = None
    tipo_bem: str | None = None
    credito_minimo: float | None = Field(default=None, gt=0)
    credito_maximo: float | None = Field(default=None, gt=0)
    taxa_adm: float | None = Field(default=None, ge=0)
    prazo_total: int | None = Field(default=None, gt=0)
    status: str | None = None


class SuccessResponse(BaseModel):
    success: bool = True


class GrupoCreateResponse(SuccessResponse):
    grupo_id: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: str


class ViabilidadeRequest(BaseModel):
    objetivo: str
    credito_desejado: float = Field(gt=0)
    prazo_desejado: int = Field(gt=0)
    lance_proprio: float = Field(ge=0)
    fgts: float = Field(ge=0)
    renda_total: float = Field(gt=0)
    parcela_desejada: float = Field(gt=0)
    data_nascimento: str = ""
    tipo_bem: str = "Imovel"


class ViabilidadeGrupo(BaseModel):
    ranking: int
    grupo_id: str
    administradora: str
    grupo: str = ""
    tipo_bem: str = ""
    credito: float
    parcela_estimada: float
    lance_sugerido_percentual: float
    lance_sugerido_valor: float
    prazo: int
    afinidade: float
    selo: str
    motivos: list[str] = Field(default_factory=list)


class ViabilidadeChecklist(BaseModel):
    idade_compativel: bool
    renda_comporta_parcela: bool
    lance_proprio_suficiente: bool
    fgts_disponivel: bool
    prazo_compativel: bool
    cenario_viavel: bool


class ViabilidadeResponse(BaseModel):
    total_grupos_encontrados: int
    perfil: str
    fgts_total: float
    lance_total_disponivel: float
    renda_total: float
    cenario: str
    checklist: ViabilidadeChecklist
    melhores_grupos: list[ViabilidadeGrupo] = Field(default_factory=list)


class EstudoCliente(BaseModel):
    nome: str = ""
    credito_desejado: float = Field(gt=0)
    objetivo: str = ""
    prazo_desejado: int | None = Field(default=None, gt=0)
    lance_proprio: float | None = Field(default=None, ge=0)
    fgts: float | None = Field(default=None, ge=0)
    renda_total: float | None = Field(default=None, ge=0)
    parcela_desejada: float | None = Field(default=None, ge=0)
    data_nascimento: str = ""
    estado_bem: str = ""


class EstudoRequest(BaseModel):
    cliente: EstudoCliente
    grupo_id: str


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
