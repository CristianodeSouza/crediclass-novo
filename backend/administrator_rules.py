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


DEFAULT_ADMINISTRATOR_RULES = [
    AdministratorRule("ITAÚ", False, 80, None, 0.30, "Credito", 0.20, "Sim, consultar regras", 0.03, True, True),
    AdministratorRule("CAIXA", False, 75, None, 0.30, "Credito", 0.20, "Sim", 0.02, True, True),
    AdministratorRule("PORTO", False, 70, None, 0.30, "Credito", 0.16, "Sim", 0.005, False, True),
    AdministratorRule("PORTO SEGURO", False, 70, None, 0.30, "Credito", 0.16, "Sim", 0.005, False, True),
    AdministratorRule("CNP", False, 75, 3_000_000, 0.30, "Credito", 0.18, "Sim", 0.05, False, True),
    AdministratorRule("CAOA", False, 75, 1_000_000, 0.30, "Credito", 0.15, "Sim", 0.05, True, True),
    AdministratorRule("EMBRACON", True, 75, None, 0.25, "Credito", 0.20, "Sim", 0.02, True, True),
    AdministratorRule("RODOBENS", False, 70, None, 0.30, "Credito", 0.20, "Sim", 0.02, True, True),
    AdministratorRule("SANTANDER", False, 75, None, 0.30, "Credito", 0.20, "Sim", 0.01, True, True),
    AdministratorRule("BANCO DO BRASIL", False, 75, None, 0.30, "Credito", 0.20, "Sim", 0.02, True, True),
]


def normalize_admin_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.upper().replace("CONSORCIO", "").replace("CONSORCIOS", "").split())


def rules_by_administradora() -> dict[str, AdministratorRule]:
    rules: dict[str, AdministratorRule] = {}
    for rule in DEFAULT_ADMINISTRATOR_RULES:
        rules.setdefault(normalize_admin_name(rule.administradora), rule)
    return rules


def get_rule_for_administradora(administradora: str) -> AdministratorRule | None:
    normalized = normalize_admin_name(administradora)
    rules = rules_by_administradora()
    if normalized in rules:
        return rules[normalized]
    for key, rule in rules.items():
        if key and (key in normalized or normalized in key):
            return rule
    return None
