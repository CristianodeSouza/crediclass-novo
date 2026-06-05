from __future__ import annotations

from dataclasses import dataclass
import unicodedata


@dataclass(frozen=True)
class AdministratorRule:
    administradora: str
    seguro_obrigatorio: bool
    idade_maxima: int | None
    limite_sem_comprovacao_renda: float | None
    percentual_lance_embutido: float
    tipo_lance_embutido: str
    taxa_adm: float
    possui_negociacao_taxa: str
    fundo_reserva: float
    aceita_saida_fiscal: bool
    aceita_fgts: bool
    observacoes_operacionais: str = ""


def normalize_admin_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.upper().replace("CONSORCIO", "").replace("CONSORCIOS", "").split())


def rule_from_config(data: dict) -> AdministratorRule | None:
    administradora = str(data.get("administradora") or "").strip()
    if not administradora:
        return None
    return AdministratorRule(
        administradora=administradora,
        seguro_obrigatorio=bool(data.get("seguro_obrigatorio", False)),
        idade_maxima=data.get("idade_maxima"),
        limite_sem_comprovacao_renda=data.get("limite_sem_comprovacao_renda"),
        percentual_lance_embutido=float(data.get("percentual_lance_embutido") or 0),
        tipo_lance_embutido=str(data.get("tipo_lance_embutido") or "Credito"),
        taxa_adm=float(data.get("taxa_adm") or 0),
        possui_negociacao_taxa=str(data.get("possui_negociacao_taxa") or "Nao"),
        fundo_reserva=float(data.get("fundo_reserva") or 0),
        aceita_saida_fiscal=bool(data.get("aceita_saida_fiscal", False)),
        aceita_fgts=bool(data.get("aceita_fgts", False)),
        observacoes_operacionais=str(data.get("observacoes_operacionais") or ""),
    )


def rules_by_administradora(config_rules: list[dict] | None = None) -> dict[str, AdministratorRule]:
    rules: dict[str, AdministratorRule] = {}
    for item in config_rules or []:
        rule = rule_from_config(item)
        if not rule:
            continue
        rules.setdefault(normalize_admin_name(rule.administradora), rule)
    return rules


def get_rule_for_administradora(administradora: str, config_rules: list[dict] | None = None) -> AdministratorRule | None:
    normalized = normalize_admin_name(administradora)
    rules = rules_by_administradora(config_rules)
    if normalized in rules:
        return rules[normalized]
    for key, rule in rules.items():
        if key and (key in normalized or normalized in key):
            return rule
    return None
