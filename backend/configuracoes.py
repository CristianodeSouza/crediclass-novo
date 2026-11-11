from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path

PIPERUN_FUNNELS = [
    {"id": 97656, "nome": "0. Mkt - Nutrição de Leads"}, {"id": 107663, "nome": "0. Mkt - Nutrição Parceiros Ativos"},
    {"id": 23643, "nome": "0. Cadastro Parceiros de Negócios"}, {"id": 96785, "nome": "0. Cadastro Bancos"},
    {"id": 108107, "nome": "0.1 Reativação"}, {"id": 4501, "nome": "1. Consultoria de Crédito (V)"},
    {"id": 4502, "nome": "2. Formalização Consórcio (V)"}, {"id": 4504, "nome": "2. Aprovação Financiamento (V)"},
    {"id": 11418, "nome": "2.1 Fechar Instituição Aprovada"}, {"id": 45077, "nome": "2. Aprovação Home Equity (V)"},
    {"id": 4505, "nome": "3. Serviços IO (V)"}, {"id": 4503, "nome": "4. Gestão da Contemplação (CS)"},
    {"id": 4506, "nome": "5. Operação IO | Consórcio (CS)"}, {"id": 4511, "nome": "5. Operação IO | Financiamento (CS)"},
    {"id": 4512, "nome": "5. Operação IO | Home Equity (CS)"}, {"id": 5080, "nome": "5. Operação IO | Portabilidade (CS)"},
    {"id": 59561, "nome": "5. Operações IO | Avulso (CS)"}, {"id": 42867, "nome": "6. Fechamento Processo I Financeiro e IO"},
    {"id": 81290, "nome": "CS) Lembrete Pagto - Caixa/ Itaú"}, {"id": 100462, "nome": "CS) Lembrete pagto - ñ contemplados"},
    {"id": 97206, "nome": "[FIN] Contas a Receber (IFI)"}, {"id": 95066, "nome": "[FIN] Contas a Pagar (PN/CN/SÓCIOS)"},
    {"id": 96872, "nome": "[RH] Recrutamento e Seleção"}, {"id": 97009, "nome": "Excluir"},
    {"id": 97787, "nome": "[RH] Registro e Controle de Ponto"}, {"id": 99211, "nome": "[ADM/FIN] Contratos Fornecedores"},
    {"id": 99207, "nome": "[ADM] Politicas e Anexos RV"}, {"id": 100166, "nome": "[ADM] Gestão de Acessos"},
    {"id": 99554, "nome": "[FIN] Planejamento Estratégico"}, {"id": 62773, "nome": "0 - Tráfego Pago (ocultar)"},
    {"id": 80973, "nome": "1.b) Vendas Canal IFR (ocultar)"}, {"id": 45075, "nome": "CS) Pós Venda Créditos (ocultar)"},
]


DEFAULT_ADMINISTRATOR_RULES = [
    {
        "administradora": "CNP",
        "tipo_bem": "Imovel",
        "status_operacional": "Ativo",
        "data_cadastro_produto": "2026-02-03",
        "responsavel_produto": "Joyce",
        "seguro_obrigatorio": False,
        "seguro_obrigatorio_texto": "Nao",
        "idade_maxima": None,
        "limite_sem_comprovacao_renda": 3000000,
        "limite_sem_comprovacao_renda_texto": "3.000.000",
        "aceita_adesao_clientes_texto": "Nao",
        "percentual_lance_embutido": 0.50,
        "tipo_lance_embutido": "Credito",
        "taxa_adm": 0,
        "possui_negociacao_taxa": "",
        "fundo_reserva": 0,
        "aceita_saida_fiscal": False,
        "aceita_saida_fiscal_texto": "",
        "aceita_fgts": True,
        "aceita_pj": True,
        "aceita_pj_texto": "Sim",
        "permite_composicao_pj_socios": True,
        "permite_composicao_pj_socios_texto": "Sim",
        "permite_cpf_socio": True,
        "permite_cpf_socio_texto": "Sim",
        "percentual_comprometimento_pj": 0.30,
        "percentual_comprometimento_cpf": 0.30,
        "observacoes_operacionais": "Limite de adesao sem comprovacao de renda: 3.000.000.",
    },
    {
        "administradora": "ITAU",
        "tipo_bem": "Imovel",
        "status_operacional": "Ativo",
        "data_cadastro_produto": "2026-02-03",
        "responsavel_produto": "Joyce",
        "seguro_obrigatorio": False,
        "seguro_obrigatorio_texto": "Nao",
        "idade_maxima": None,
        "limite_sem_comprovacao_renda": None,
        "limite_sem_comprovacao_renda_texto": "Sob consulta/Sistema Itau",
        "aceita_adesao_clientes_texto": "Sim, consultar regras",
        "percentual_lance_embutido": 0.30,
        "saldo_embutido_modo": "coerente",
        "tipo_lance_embutido": "Credito",
        "taxa_adm": 0,
        "possui_negociacao_taxa": "",
        "fundo_reserva": 0,
        "aceita_saida_fiscal": False,
        "aceita_saida_fiscal_texto": "",
        "aceita_fgts": True,
        "aceita_pj": True,
        "aceita_pj_texto": "Sim",
        "permite_composicao_pj_socios": True,
        "permite_composicao_pj_socios_texto": "Sim",
        "permite_cpf_socio": True,
        "permite_cpf_socio_texto": "Sim",
        "percentual_comprometimento_pj": 0.30,
        "percentual_comprometimento_cpf": 0.30,
        "observacoes_operacionais": "Limite sem comprovacao sob consulta no sistema Itau.",
    },
    {
        "administradora": "CAOA",
        "tipo_bem": "Imovel",
        "status_operacional": "Ativo",
        "data_cadastro_produto": "2026-02-03",
        "responsavel_produto": "Joyce",
        "seguro_obrigatorio": False,
        "seguro_obrigatorio_texto": "Nao",
        "idade_maxima": None,
        "limite_sem_comprovacao_renda": 1000000,
        "limite_sem_comprovacao_renda_texto": "1.000.000",
        "aceita_adesao_clientes_texto": "Verificar",
        "percentual_lance_embutido": 0.30,
        "tipo_lance_embutido": "Credito",
        "taxa_adm": 0,
        "possui_negociacao_taxa": "",
        "fundo_reserva": 0,
        "aceita_saida_fiscal": False,
        "aceita_saida_fiscal_texto": "",
        "aceita_fgts": True,
        "aceita_pj": True,
        "aceita_pj_texto": "Sim",
        "permite_composicao_pj_socios": True,
        "permite_composicao_pj_socios_texto": "Sim",
        "permite_cpf_socio": True,
        "permite_cpf_socio_texto": "Sim",
        "percentual_comprometimento_pj": 0.30,
        "percentual_comprometimento_cpf": 0.30,
        "observacoes_operacionais": "Aceita adesao de clientes: verificar.",
    },
    {
        "administradora": "PORTO",
        "tipo_bem": "Imovel",
        "status_operacional": "Ativo",
        "data_cadastro_produto": "2026-02-03",
        "responsavel_produto": "Joyce",
        "seguro_obrigatorio": False,
        "seguro_obrigatorio_texto": "Nao",
        "idade_maxima": None,
        "limite_sem_comprovacao_renda": 5000000,
        "limite_sem_comprovacao_renda_texto": "5.000.000",
        "aceita_adesao_clientes_texto": "Nao",
        "percentual_lance_embutido": 0.30,
        "tipo_lance_embutido": "Credito",
        "taxa_adm": 0,
        "possui_negociacao_taxa": "",
        "fundo_reserva": 0,
        "aceita_saida_fiscal": False,
        "aceita_saida_fiscal_texto": "",
        "aceita_fgts": True,
        "aceita_pj": True,
        "aceita_pj_texto": "Sim",
        "permite_composicao_pj_socios": True,
        "permite_composicao_pj_socios_texto": "Sim",
        "permite_cpf_socio": True,
        "permite_cpf_socio_texto": "Sim",
        "percentual_comprometimento_pj": 0.30,
        "percentual_comprometimento_cpf": 0.30,
        "observacoes_operacionais": "Limite de adesao sem comprovacao de renda: 5.000.000.",
    },
    {
        "administradora": "EMBRACON",
        "tipo_bem": "Imovel",
        "status_operacional": "INATIVO",
        "data_cadastro_produto": "",
        "responsavel_produto": "",
        "seguro_obrigatorio": False,
        "seguro_obrigatorio_texto": "",
        "idade_maxima": None,
        "limite_sem_comprovacao_renda": None,
        "limite_sem_comprovacao_renda_texto": "",
        "aceita_adesao_clientes_texto": "Verificar",
        "percentual_lance_embutido": 0.25,
        "tipo_lance_embutido": "Credito",
        "taxa_adm": 0,
        "possui_negociacao_taxa": "",
        "fundo_reserva": 0,
        "aceita_saida_fiscal": False,
        "aceita_saida_fiscal_texto": "",
        "aceita_fgts": True,
        "aceita_pj": True,
        "aceita_pj_texto": "Sim",
        "permite_composicao_pj_socios": True,
        "permite_composicao_pj_socios_texto": "Sim",
        "permite_cpf_socio": True,
        "permite_cpf_socio_texto": "Sim",
        "percentual_comprometimento_pj": 0.30,
        "percentual_comprometimento_cpf": 0.30,
        "observacoes_operacionais": "Produto inativo na regra da planilha.",
    },
    {
        "administradora": "RODOBENS",
        "tipo_bem": "Imovel",
        "status_operacional": "Ativo",
        "data_cadastro_produto": "",
        "responsavel_produto": "",
        "seguro_obrigatorio": False,
        "seguro_obrigatorio_texto": "Nao",
        "idade_maxima": None,
        "limite_sem_comprovacao_renda": None,
        "limite_sem_comprovacao_renda_texto": "Sob",
        "aceita_adesao_clientes_texto": "Sim, consultar regra",
        "percentual_lance_embutido": 0.30,
        "tipo_lance_embutido": "Credito",
        "taxa_adm": 0,
        "possui_negociacao_taxa": "",
        "fundo_reserva": 0,
        "aceita_saida_fiscal": False,
        "aceita_saida_fiscal_texto": "",
        "aceita_fgts": True,
        "aceita_pj": True,
        "aceita_pj_texto": "Sim",
        "permite_composicao_pj_socios": True,
        "permite_composicao_pj_socios_texto": "Sim",
        "permite_cpf_socio": True,
        "permite_cpf_socio_texto": "Sim",
        "percentual_comprometimento_pj": 0.30,
        "percentual_comprometimento_cpf": 0.30,
        "observacoes_operacionais": "Limite sem comprovacao: Sob. Aceita adesao: sim, consultar regra.",
    },
    {
        "administradora": "CANOPUS",
        "tipo_bem": "Imovel",
        "status_operacional": "Ativo",
        "data_cadastro_produto": "",
        "responsavel_produto": "",
        "seguro_obrigatorio": True,
        "seguro_obrigatorio_texto": "Sim",
        "idade_maxima": 70,
        "limite_sem_comprovacao_renda": None,
        "limite_sem_comprovacao_renda_texto": "Nao",
        "aceita_adesao_clientes_texto": "Sim, consultar regra",
        "percentual_lance_embutido": 0.50,
        "tipo_lance_embutido": "Credito",
        "taxa_adm": 0,
        "possui_negociacao_taxa": "",
        "fundo_reserva": 0,
        "aceita_saida_fiscal": False,
        "aceita_saida_fiscal_texto": "",
        "aceita_fgts": True,
        "aceita_pj": True,
        "aceita_pj_texto": "Sim",
        "permite_composicao_pj_socios": True,
        "permite_composicao_pj_socios_texto": "Sim",
        "permite_cpf_socio": True,
        "permite_cpf_socio_texto": "Sim",
        "percentual_comprometimento_pj": 0.30,
        "percentual_comprometimento_cpf": 0.30,
        "observacoes_operacionais": "Tem seguro obrigatorio. Idade maxima do seguro: 70 anos.",
    },
    {
        "administradora": "SANTANDER",
        "tipo_bem": "Imovel",
        "status_operacional": "Ativo",
        "data_cadastro_produto": "",
        "responsavel_produto": "",
        "seguro_obrigatorio": False,
        "seguro_obrigatorio_texto": "Nao",
        "idade_maxima": None,
        "limite_sem_comprovacao_renda": None,
        "limite_sem_comprovacao_renda_texto": "Nao",
        "aceita_adesao_clientes_texto": "Nao",
        "percentual_lance_embutido": 0.30,
        "tipo_lance_embutido": "Credito",
        "taxa_adm": 0,
        "possui_negociacao_taxa": "",
        "fundo_reserva": 0,
        "aceita_saida_fiscal": False,
        "aceita_saida_fiscal_texto": "",
        "aceita_fgts": True,
        "aceita_pj": True,
        "aceita_pj_texto": "Sim",
        "permite_composicao_pj_socios": True,
        "permite_composicao_pj_socios_texto": "Sim",
        "permite_cpf_socio": True,
        "permite_cpf_socio_texto": "Sim",
        "percentual_comprometimento_pj": 0.30,
        "percentual_comprometimento_cpf": 0.30,
        "observacoes_operacionais": "Limite sem comprovacao e adesao de clientes marcados como Nao.",
    },
    {
        "administradora": "BB",
        "tipo_bem": "Imovel",
        "status_operacional": "Ativo",
        "data_cadastro_produto": "",
        "responsavel_produto": "",
        "seguro_obrigatorio": False,
        "seguro_obrigatorio_texto": "Nao",
        "idade_maxima": None,
        "limite_sem_comprovacao_renda": None,
        "limite_sem_comprovacao_renda_texto": "",
        "aceita_adesao_clientes_texto": "Nao",
        "percentual_lance_embutido": 0.30,
        "tipo_lance_embutido": "Credito",
        "taxa_adm": 0,
        "possui_negociacao_taxa": "",
        "fundo_reserva": 0,
        "aceita_saida_fiscal": False,
        "aceita_saida_fiscal_texto": "",
        "aceita_fgts": True,
        "aceita_pj": True,
        "aceita_pj_texto": "Sim",
        "permite_composicao_pj_socios": True,
        "permite_composicao_pj_socios_texto": "Sim",
        "permite_cpf_socio": True,
        "permite_cpf_socio_texto": "Sim",
        "percentual_comprometimento_pj": 0.30,
        "percentual_comprometimento_cpf": 0.30,
        "observacoes_operacionais": "Aceita adesao de clientes: Nao.",
    },
    {
        "administradora": "SERVOPA",
        "tipo_bem": "Imovel",
        "status_operacional": "Verificar",
        "data_cadastro_produto": "",
        "responsavel_produto": "TED",
        "seguro_obrigatorio": False,
        "seguro_obrigatorio_texto": "Verificar",
        "idade_maxima": None,
        "limite_sem_comprovacao_renda": None,
        "limite_sem_comprovacao_renda_texto": "",
        "aceita_adesao_clientes_texto": "",
        "percentual_lance_embutido": 0,
        "tipo_lance_embutido": "",
        "taxa_adm": 0,
        "possui_negociacao_taxa": "",
        "fundo_reserva": 0,
        "aceita_saida_fiscal": False,
        "aceita_saida_fiscal_texto": "",
        "aceita_fgts": True,
        "aceita_pj": True,
        "aceita_pj_texto": "Sim",
        "permite_composicao_pj_socios": True,
        "permite_composicao_pj_socios_texto": "Sim",
        "permite_cpf_socio": True,
        "permite_cpf_socio_texto": "Sim",
        "percentual_comprometimento_pj": 0.30,
        "percentual_comprometimento_cpf": 0.30,
        "observacoes_operacionais": "Seguro obrigatorio e demais parametros precisam ser verificados.",
    },
]


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
    "piperun_pipelines": PIPERUN_FUNNELS,
    "piperun_owners": [
        {"nome": "Bruna Torres", "owner_id": 2602, "credito_minimo": None, "credito_maximo": 999999, "origens": [], "pipeline_ids": [4501]},
        {"nome": "Bruno Tavares", "owner_id": 2609, "credito_minimo": 1000000, "credito_maximo": None, "origens": [], "pipeline_ids": [4501]},
    ],
    "piperun_owner_distribution_enabled": False,
    "piperun_scan_schedule": {
        "days": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
        "times": ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00"],
        "timezone": "America/Sao_Paulo",
        "enabled": True,
    },
    "notificacoes": {
        "alertar_sincronizacao": True,
        "alertar_historico_atualizado": True,
        "alertar_falha_integracao": True,
    },
    "administradoras_regras": DEFAULT_ADMINISTRATOR_RULES,
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
    "regras_negocio_feedbacks": {},
}

RUNTIME_DIR = Path(__file__).resolve().parent / "runtime_data"
CONFIG_FILE = RUNTIME_DIR / "configuracoes.json"


def merge_config(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if key not in result:
            continue
        if key == "administradoras_regras" and isinstance(value, list) and not value:
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
    config = merge_config(DEFAULT_CONFIG, saved if isinstance(saved, dict) else {})
    for owner in config.get("piperun_owners", []):
        if isinstance(owner, dict) and "pipeline_ids" not in owner:
            owner["pipeline_ids"] = [4501]
    # Preserve the original Make routing rules for the two initial owners.
    for owner in config.get("piperun_owners", []):
        if owner.get("owner_id") == 2602 and owner.get("credito_minimo") is None and owner.get("credito_maximo") is None:
            owner["credito_maximo"] = 999999
        if owner.get("owner_id") == 2609 and owner.get("credito_minimo") is None and owner.get("credito_maximo") is None:
            owner["credito_minimo"] = 1000000
    return config


def save_config() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        backups_dir = RUNTIME_DIR / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        backup_name = f"configuracoes-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.json"
        try:
            (backups_dir / backup_name).write_text(CONFIG_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            pass
    CONFIG_FILE.write_text(json.dumps(_settings, ensure_ascii=False, indent=2), encoding="utf-8")


_settings = load_config()


def ensure_administrator_rules(config: dict) -> dict:
    if not isinstance(config.get("administradoras_regras"), list) or not config.get("administradoras_regras"):
        config["administradoras_regras"] = deepcopy(DEFAULT_ADMINISTRATOR_RULES)
    return config


def get_configuracoes() -> dict:
    return deepcopy(ensure_administrator_rules(_settings))


def update_configuracoes(payload: dict) -> dict:
    for section in ["empresa", "preferencias", "parametros_financeiros", "integracoes", "notificacoes"]:
        if section in payload and isinstance(payload[section], dict):
            values = dict(payload[section])
            if section == "notificacoes":
                values.pop("alertar_estudo_salvo", None)
            _settings[section].update(values)
    if "administradoras_regras" in payload and isinstance(payload["administradoras_regras"], list) and payload["administradoras_regras"]:
        _settings["administradoras_regras"] = payload["administradoras_regras"]
    ensure_administrator_rules(_settings)
    if "usuarios" in payload and isinstance(payload["usuarios"], list):
        _settings["usuarios"] = payload["usuarios"]
    if "regras_negocio_feedbacks" in payload and isinstance(payload["regras_negocio_feedbacks"], dict):
        _settings["regras_negocio_feedbacks"] = payload["regras_negocio_feedbacks"]
    if "piperun_owners" in payload and isinstance(payload["piperun_owners"], list):
        for owner in payload["piperun_owners"]:
            if isinstance(owner, dict):
                owner["pipeline_ids"] = [int(value) for value in owner.get("pipeline_ids", []) if str(value).isdigit()]
                owner.pop("origens", None)
        _settings["piperun_owners"] = payload["piperun_owners"]
    if "piperun_owner_distribution_enabled" in payload:
        _settings["piperun_owner_distribution_enabled"] = bool(payload["piperun_owner_distribution_enabled"])
    if "piperun_scan_schedule" in payload and isinstance(payload["piperun_scan_schedule"], dict):
        schedule = payload["piperun_scan_schedule"]
        allowed_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
        days = [day for day in schedule.get("days", []) if day in allowed_days]
        import re
        times = sorted({time for time in schedule.get("times", []) if isinstance(time, str) and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time)})
        if days and times:
            _settings["piperun_scan_schedule"] = {
                "days": days,
                "times": times,
                "timezone": "America/Sao_Paulo",
                "enabled": bool(schedule.get("enabled", True)),
            }
    save_config()
    return {"success": True}

