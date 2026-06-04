from copy import deepcopy


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
    "permissoes": {
        "Administradora": {
            "visualizar_grupos": True,
            "criar_grupos": True,
            "editar_grupos": True,
            "excluir_grupos": True,
            "gerar_estudos": True,
            "exportar_dados": True,
            "configuracoes": True,
            "usuarios_permissoes": True,
        },
        "Operadora": {
            "visualizar_grupos": True,
            "criar_grupos": False,
            "editar_grupos": False,
            "excluir_grupos": False,
            "gerar_estudos": True,
            "exportar_dados": True,
            "configuracoes": False,
            "usuarios_permissoes": False,
        },
        "Visualizador": {
            "visualizar_grupos": True,
            "criar_grupos": False,
            "editar_grupos": False,
            "excluir_grupos": False,
            "gerar_estudos": False,
            "exportar_dados": False,
            "configuracoes": False,
            "usuarios_permissoes": False,
        },
    },
}

_settings = deepcopy(DEFAULT_CONFIG)


def get_configuracoes() -> dict:
    return deepcopy(_settings)


def update_configuracoes(payload: dict) -> dict:
    for section in ["empresa", "preferencias", "parametros_financeiros"]:
        if section in payload and isinstance(payload[section], dict):
            _settings[section].update(payload[section])
    return {"success": True}
