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


def parse_optional_number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("R$", "").replace("%", "").strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def parse_optional_int(value: object) -> int | None:
    number = parse_optional_number(value)
    if number is None:
        return None
    return int(number)


def parse_percent(value: object) -> float:
    number = parse_optional_number(value)
    if number is None:
        return 0.0
    return number / 100 if number > 1 else number


def rule_from_config(data: dict) -> AdministratorRule | None:
    administradora = str(data.get("administradora") or "").strip()
    if not administradora:
        return None
    return AdministratorRule(
        administradora=administradora,
        seguro_obrigatorio=bool(data.get("seguro_obrigatorio", False)),
        idade_maxima=parse_optional_int(data.get("idade_maxima")),
        limite_sem_comprovacao_renda=parse_optional_number(data.get("limite_sem_comprovacao_renda")),
        percentual_lance_embutido=parse_percent(data.get("percentual_lance_embutido")),
        tipo_lance_embutido=str(data.get("tipo_lance_embutido") or "Credito"),
        taxa_adm=parse_percent(data.get("taxa_adm")),
        possui_negociacao_taxa=str(data.get("possui_negociacao_taxa") or "Nao"),
        fundo_reserva=parse_percent(data.get("fundo_reserva")),
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
