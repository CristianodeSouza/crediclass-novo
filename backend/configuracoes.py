from copy import deepcopy
import json
from pathlib import Path


DEFAULT_CONFIG = {
    "empresa": {
        "nome": "Crediclass",
        "cnpj": "",
        "email": "",
        "telefone": "",
        "endereco": "",
        "logo": "",
    },
    "preferencias": {
        "moeda": "BRL",
        "formato_data": "DD/MM/YYYY",
        "casas_decimais_valores": 2,
        "casas_decimais_percentuais": 2,
        "ativar_meia_parcela": True,
        "ativar_lance_embutido": True,
        "exibir_historico_36_meses": True,
        "atualizacao_automatica_minutos": 5,
        "tema": "Claro",
        "idioma": "pt-BR",
    },
    "parametros_financeiros": {
        "taxa_administracao_padrao": 0.20,
        "fundo_reserva_padrao": 0.03,
        "percentual_lance_fixo_padrao": 0.25,
        "percentual_lance_moderado_padrao": 0.35,
        "percentual_lance_agressivo_padrao": 0.50,
        "prazo_maximo": 240,
        "prazo_minimo": 12,
        "indice_correcao_anual": "INCC",
    },
    "integracoes": {
        "google_sheets": True,
        "piperun_crm": False,
        "email_smtp": False,
        "backup_automatico": False,
    },
    "usuarios": [
        {
            "nome": "Larissa",
            "email": "larissa@crediclass.local",
            "perfil": "Administradora",
            "status": "Ativo",
            "ultimo_acesso": "",
        },
        {
            "nome": "Joyce",
            "email": "joyce@crediclass.local",
            "perfil": "Operadora",
            "status": "Ativo",
            "ultimo_acesso": "",
        },
    ],
    "acesso": {
        "paineis_liberados": True,
        "descricao": "Todos os usuarios podem visualizar todos os dados dos paineis.",
    },
}

RUNTIME_DIR = Path(__file__).resolve().parent / "runtime_data"
CONFIG_FILE = RUNTIME_DIR / "configuracoes.json"


def merge_config(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if key not in result:
            continue
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key].update(value)
        else:
            result[key] = value
    return result


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return deepcopy(DEFAULT_CONFIG)
    try:
        saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return deepcopy(DEFAULT_CONFIG)
    return merge_config(DEFAULT_CONFIG, saved if isinstance(saved, dict) else {})


def save_config() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(_settings, ensure_ascii=False, indent=2), encoding="utf-8")


_settings = load_config()


def get_configuracoes() -> dict:
    return deepcopy(_settings)


def update_configuracoes(payload: dict) -> dict:
    for section in ["empresa", "preferencias", "parametros_financeiros"]:
        if section in payload and isinstance(payload[section], dict):
            _settings[section].update(payload[section])
    save_config()
    return {"success": True}
