from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Histórico mensal
class HistoricoMes(BaseModel):
    mes: str
    maior_lance: Optional[float] = None
    menor_lance: Optional[float] = None
    qtd_contemplacoes: Optional[int] = None

# Dados gerais do grupo
class GrupoBase(BaseModel):
    administradora: str
    grupo: str
    tipo_bem: Optional[str] = None
    primeira_assembleia: Optional[str] = None
    data_termino: Optional[str] = None
    prazo_grupo: Optional[int] = None
    prazo_restante: Optional[int] = None
    menor_credito: Optional[float] = None
    maior_credito: Optional[float] = None
    taxa_administracao: Optional[float] = None
    fundo_reserva: Optional[float] = None
    prestacao_integral: Optional[float] = None
    categoria: Optional[str] = None
    status: Optional[str] = "Ativo"

# Grupo com histórico
class GrupoComHistorico(GrupoBase):
    grupo_id: str
    historico: Dict[str, List[HistoricoMes]] = {
        "2024": [],
        "2025": [],
        "2026": []
    }

# Grupo para resposta da API (reduzido)
class GrupoResumido(BaseModel):
    grupo_id: str
    administradora: str
    grupo: str
    tipo_bem: Optional[str] = None
    menor_credito: Optional[float] = None
    maior_credito: Optional[float] = None
    prazo_grupo: Optional[int] = None
    prestacao_integral: Optional[float] = None
    taxa_administracao: Optional[float] = None
    status: Optional[str] = None

# Request para criar/atualizar grupo
class GrupoUpdate(BaseModel):
    dados_gerais: Optional[Dict[str, Any]] = None
    historico: Optional[Dict[str, List[Dict[str, Any]]]] = None

# Response padrão
class ResponseMessage(BaseModel):
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
