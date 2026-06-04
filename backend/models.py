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


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
