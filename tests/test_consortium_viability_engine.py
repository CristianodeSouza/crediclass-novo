import unittest
from types import SimpleNamespace

from backend.consortium_viability_engine import analyze_client_consortium_viability, map_declared_objective_to_preference
from backend.motor360_math import normalize_percent


def payload(**overrides):
    values = {
        "objetivo": "Contemplar - moderado - 12 meses",
        "credito_desejado": 950000,
        "lance_proprio": 100000,
        "fgts": 50000,
        "parcela_desejada": 6500,
        "parcela_limite": 15000,
        "renda_total": 50000,
        "tipo_bem": "",
        "tipo_bem_explicit": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def group(identifier="G1", **overrides):
    values = {
        "grupo_id": identifier,
        "grupo": identifier,
        "administradora": "ITAU",
        "tipo_bem": "Imovel",
        "status": "Ativo",
        "credito_minimo": 100000,
        "credito_maximo": 2000000,
        "prazo_restante": 300,
        "taxa_adm": "16%",
        "fundo_reserva": "3%",
        "percentual_lance_embutido": "30%",
        "lance_super_agressivo_3m": "40%",
        "lance_agressivo_6m": "30%",
        "lance_moderado_12m": "10%",
        "lance_conservador_24m": "5%",
        "lance_investidor": "2%",
        "parcela_inicial_grupo": 6000,
        "parcela_apos_lance_grupo": 5000,
        "parcela_reduzida": 3000,
        "historico_12_meses": [],
    }
    values.update(overrides)
    return values


class Motor360RfcTest(unittest.TestCase):
    def test_filtros_de_lance_embutido_e_parcela_reduzida(self):
        result = analyze_client_consortium_viability(payload(
            contemplacao_perfil=None,
            filtro_lance_embutido="sim",
            filtro_parcela_reduzida="sim",
        ), [
            group(modalidades_embutido="Sobre o Crédito", parcela_reduzida="500"),
            group("G2", modalidades_embutido="Não", parcela_reduzida=""),
        ])
        self.assertEqual([item["grupo"] for item in result["items"]], ["G1"])

        without_result = analyze_client_consortium_viability(payload(
            contemplacao_perfil="moderate",
            filtro_lance_embutido="nao",
        ), [group()])
        for item in without_result["items"]:
            self.assertTrue(all(scenario["id"] == "without_embedded" for scenario in item.get("cenarios", [])))
        self.assertEqual(without_result["audit"]["parameters"]["filtro_lance_embutido"], "nao")
        self.assertEqual(without_result["audit"]["parameters"]["cenarios_considerados"], ["without_embedded"])

    def test_perfil_explicito_filtra_grupo_antes_da_selecao(self):
        result = analyze_client_consortium_viability(payload(
            contemplacao_perfil="urgent",
            lance_proprio=100000,
            fgts=0,
        ), [group(lance_super_agressivo_3m="90%", lance_conservador_24m="5%")])
        self.assertEqual(result["perfil_contemplacao"], "urgent")
        self.assertEqual(result["items"], [])
        self.assertTrue(any(item.get("result") == "excluded_contemplation" for item in result["audit"]["group_results"]))

    def test_perfil_explicito_preserva_matriz_dos_demais_perfis(self):
        result = analyze_client_consortium_viability(payload(
            contemplacao_perfil="urgent",
            lance_proprio=500000,
            fgts=0,
            parcela_limite=1000000,
        ), [group(lance_super_agressivo_3m="5%", lance_conservador_24m="5%")])
        self.assertEqual(len(result["items"]), 1)
        profiles = result["items"][0]["cenarios"][0]["perfis_contemplacao"]
        self.assertTrue(any(profile["id"] == "conservative" for profile in profiles))

    def test_lista_grupo_menor_para_composicao_manual_de_ate_50_cotas(self):
        history = [
            {"mes": "2026-04", "qtd_contemplacoes": 2},
            {"mes": "2026-05", "qtd_contemplacoes": 4},
            {"mes": "2026-06", "qtd_contemplacoes": 3},
        ]
        result = analyze_client_consortium_viability(payload(credito_desejado=600000), [
            group(credito_minimo=100000, credito_maximo=300000, historico_12_meses=history),
        ])

        self.assertEqual(len(result["items"]), 1)
        self.assertTrue(result["items"][0]["requires_composition"])
        self.assertEqual(result["total_grupos_composicao"], 1)
        item = result["items"][0]
        self.assertEqual(item["cotas_minimas_sem_embutido"], 2)
        self.assertEqual(item["cotas_minimas_com_embutido"], 3)
        self.assertEqual(item["cotas_maximas"], 50)
        self.assertEqual(item["cenarios"][0]["credito_liquido_projetado"], 600000)
        self.assertTrue(item["capacidade_contemplacoes"])
        self.assertEqual(item["historico_12_meses"], history)

    def test_expoe_media_maxima_de_contemplacoes_para_controlar_cotas(self):
        history = [
            {"mes": "2026-04", "qtd_contemplacoes": 2},
            {"mes": "2026-05", "qtd_contemplacoes": 4},
            {"mes": "2026-06", "qtd_contemplacoes": 3},
        ]
        result = analyze_client_consortium_viability(payload(objetivo="Contemplar - rapido - 6 meses"), [
            group(historico_12_meses=history),
        ])

        capacity = result["items"][0]["capacidade_contemplacoes_selecionada"]
        self.assertEqual(capacity["perfil"], "Rapido - 6 meses")
        self.assertEqual(capacity["janela_meses"], 6)
        self.assertEqual(capacity["media_contemplacoes"], 3.0)
        self.assertEqual(capacity["limite_cotas"], 3)
        self.assertEqual(result["items"][0]["historico_12_meses"], history)

    def test_official_scenarios_preserve_credit_and_do_not_share_values(self):
        result = analyze_client_consortium_viability(payload(), [group()])
        scenarios = result["items"][0]["cenarios"]
        without = next(item for item in scenarios if item["id"] == "without_embedded")
        embedded = next(item for item in scenarios if item["id"] == "with_embedded")

        self.assertEqual(without["credito_contratado"], 950000.0)
        self.assertEqual(without["taxa_administracao"], 152000.0)
        self.assertEqual(without["fundo_reserva"], 28500.0)
        self.assertEqual(without["saldo_devedor"], 1130500.0)
        self.assertEqual(without["lance_total"], 150000.0)
        self.assertEqual(without["lance_cliente_total"], 150000.0)
        self.assertAlmostEqual(without["percentual_lance_cliente"], 150000 / 950000, places=6)
        self.assertEqual(without["saldo_apos_lance"], 980500.0)
        self.assertEqual(without["parcela_pos_contemplacao"], 3266.66)
        self.assertEqual(
            without["parcela_pos_contemplacao_formula"],
            "(saldo devedor - parcela inicial - lance total ofertado) / (prazo remanescente - 1)",
        )
        self.assertEqual(without["prazo_inicial_desejada_meses"], 174)
        self.assertEqual(without["prazo_apos_lance_limite_renda_meses"], 66)
        self.assertTrue(without["liquidez_preservada"])

        self.assertEqual(embedded["credito_contratado"], 1357142.86)
        self.assertEqual(embedded["valor_lance_embutido"], 407142.86)
        self.assertEqual(embedded["taxa_administracao"], 217142.86)
        self.assertEqual(embedded["fundo_reserva"], 40714.29)
        self.assertEqual(embedded["saldo_devedor"], 1615000.0)
        self.assertEqual(embedded["lance_total"], 557142.86)
        self.assertEqual(embedded["lance_cliente_total"], 150000.0)
        self.assertAlmostEqual(embedded["percentual_lance_cliente"], 150000 / 1357142.86, places=6)
        self.assertEqual(embedded["saldo_apos_lance"], 1057857.14)
        self.assertEqual(embedded["parcela_pos_contemplacao"], 3519.98)
        self.assertEqual(embedded["prazo_apos_lance_limite_renda_meses"], 71)
        self.assertTrue(embedded["liquidez_preservada"])
        item = result["items"][0]
        self.assertEqual(item["parcela_inicial_sem_embutido"], 3768.33)
        self.assertEqual(item["parcela_inicial_com_embutido"], 5383.33)

    def test_null_percentage_remains_null_and_only_embedded_scenario_is_not_created(self):
        result = analyze_client_consortium_viability(payload(), [group(percentual_lance_embutido=None)])
        scenarios = result["items"][0]["cenarios"]
        without = next(item for item in scenarios if item["id"] == "without_embedded")
        embedded = next(item for item in scenarios if item["id"] == "with_embedded")
        self.assertTrue(without["eligible"])
        self.assertEqual(embedded["creation_status"], "not_created")
        self.assertEqual(embedded["creation_reason"], "percentual_x_ausente")
        self.assertIsNone(embedded["credito_contratado"])

    def test_credit_range_uses_nominal_contracted_credit_not_debt(self):
        result = analyze_client_consortium_viability(payload(fgts=0), [
            group("outside", credito_minimo=100000, credito_maximo=949999),
            group("inside", credito_minimo=900000, credito_maximo=1100000, percentual_lance_embutido=None, lance_moderado_12m="5%"),
        ])
        self.assertEqual({item["grupo"] for item in result["items"]}, {"outside", "inside"})
        self.assertEqual(result["items"][0]["cenarios"][0]["saldo_devedor"], 1130500.0)

    def test_remaining_term_requires_initial_and_after_bid_income_terms(self):
        result = analyze_client_consortium_viability(payload(), [
            group("enough", prazo_restante=76, percentual_lance_embutido=None),
            group("short", prazo_restante=75, percentual_lance_embutido=None),
        ])
        self.assertEqual({item["grupo"] for item in result["items"]}, {"enough", "short"})

    def test_credit_stage_remains_visible_when_later_rules_reject_group(self):
        result = analyze_client_consortium_viability(payload(), [
            group("credit-only", prazo_restante=1, percentual_lance_embutido=None),
        ])
        self.assertEqual([item["grupo"] for item in result["items"]], ["credit-only"])
        self.assertEqual(result["total_grupos_credito_compativeis"], 1)
        scenario = result["items"][0]["cenarios"][0]
        self.assertFalse(scenario["term_compatible"])

    def test_objective_is_priority_not_an_exclusion_rule(self):
        result = analyze_client_consortium_viability(payload(objetivo="Contemplar - urgente - 3 meses"), [
            group(percentual_lance_embutido=None, lance_super_agressivo_3m="90%", lance_agressivo_6m="80%", lance_moderado_12m="10%"),
        ])
        item = result["items"][0]
        self.assertIn("moderate", item["compatible_contemplation_strategies"])
        self.assertFalse(item["destaque_preferencia"])

    def test_embedded_bid_reduces_required_client_resources_and_counts_in_profile(self):
        result = analyze_client_consortium_viability(
            payload(
                credito_desejado=600000,
                lance_proprio=100000,
                fgts=100000,
                parcela_desejada=6000,
                parcela_limite=12000,
                renda_total=40000,
            ),
            [group(
                percentual_lance_embutido="30%",
                lance_super_agressivo_3m="99%",
                lance_agressivo_6m="99%",
                lance_moderado_12m="25%",
                lance_conservador_24m="99%",
                lance_investidor="99%",
            )],
        )
        scenarios = result["items"][0]["cenarios"]
        without = next(item for item in scenarios if item["id"] == "without_embedded")
        embedded = next(item for item in scenarios if item["id"] == "with_embedded")

        self.assertEqual(without["lance_cliente_total"], 200000.0)
        self.assertAlmostEqual(without["percentual_lance_cliente"], 200000 / 600000, places=6)
        self.assertEqual(embedded["lance_cliente_total"], 200000.0)
        self.assertAlmostEqual(embedded["percentual_lance_cliente"], 200000 / (600000 / 0.7), places=6)
        self.assertEqual(embedded["lance_embutido"], 257142.86)
        self.assertEqual(embedded["lance_total_cenario"], 457142.86)
        self.assertAlmostEqual(embedded["percentual_lance_efetivo"], 457142.86 / (600000 / 0.7), places=6)
        self.assertIn("moderate", without["compatible_contemplation_strategies"])
        self.assertIn("moderate", embedded["compatible_contemplation_strategies"])
        moderate = next(profile for profile in without["perfis_contemplacao"] if profile["id"] == "moderate")
        self.assertEqual(moderate["percentual_referencia"], 0.25)
        self.assertEqual(moderate["lance_ideal"], 150000.0)
        self.assertEqual(moderate["falta_para_ideal"], 0)
        embedded_moderate = next(profile for profile in embedded["perfis_contemplacao"] if profile["id"] == "moderate")
        self.assertEqual(embedded_moderate["lance_ideal_total"], 214285.72)
        self.assertEqual(embedded_moderate["lance_embutido"], 257142.86)
        self.assertEqual(embedded_moderate["lance_ideal"], 0.0)
        self.assertEqual(embedded_moderate["falta_para_ideal"], 0.0)

    def test_contemplation_never_eliminates_a_credit_and_term_preselected_group(self):
        result = analyze_client_consortium_viability(payload(), [
            group(
                percentual_lance_embutido=None,
                lance_super_agressivo_3m="99%",
                lance_agressivo_6m="99%",
                lance_moderado_12m="99%",
                lance_conservador_24m="99%",
                lance_investidor="99%",
            ),
        ])
        self.assertEqual(result["total_grupos_credito_compativeis"], 1)
        self.assertEqual(result["total_grupos_preselecionados"], 1)
        self.assertEqual(result["items"][0]["selection_stage"], "matrix")

    def test_golden_matrix_list_keeps_credit_and_term_as_operator_indicators(self):
        approved = ["40112", "40174", "40105", "40098", "40090", "40086", "1820", "1038", "1031", "1026", "1019"]
        term_rejected = ["1176", "1011", "1770", "1006"]
        groups = [group(identifier, prazo_restante=240, percentual_lance_embutido=None) for identifier in approved]
        groups.extend(group(identifier, prazo_restante=1, percentual_lance_embutido=None) for identifier in term_rejected)
        result = analyze_client_consortium_viability(
            payload(credito_desejado=600000, lance_proprio=100000, fgts=100000, renda_total=40000, parcela_desejada=6000, parcela_limite=12000),
            groups,
        )
        self.assertEqual(result["total_grupos_credito_compativeis"], 15)
        self.assertEqual(result["total_grupos_preselecionados"], 15)
        self.assertEqual({item["grupo"] for item in result["items"]}, set(approved + term_rejected))
        self.assertEqual(result["audit"]["summary"]["total_term_income_rejected"], 4)

    def test_term_rejection_keeps_only_the_consolidated_term_reason(self):
        result = analyze_client_consortium_viability(payload(), [
            group("1770", credito_minimo=400000, credito_maximo=1100000, prazo_restante=1),
        ])
        audit_entry = result["audit"]["group_results"][0]
        self.assertEqual(audit_entry["result"], "matrix_approved")
        self.assertEqual(audit_entry["justification"], [])

    def test_audit_reports_raw_identifier_source_row_and_decision_usage(self):
        result = analyze_client_consortium_viability(payload(), [
            group("I176", source_row=148, grupo_raw="I176", percentual_lance_embutido=None),
        ])
        entry = result["audit"]["group_results"][0]
        self.assertEqual(entry["source_row"], 148)
        self.assertEqual(entry["grupo_raw"], "I176")
        tipo_column = next(column for column in result["audit"]["columns_used"] if column["column"] == "C")
        self.assertTrue(tipo_column["loaded"])
        self.assertFalse(tipo_column["used_in_decision"])

    def test_contemplation_classification_ignores_credit_incompatible_scenario(self):
        result = analyze_client_consortium_viability(payload(), [
            group(
                credito_minimo=100000,
                credito_maximo=1100000,
                lance_super_agressivo_3m="30%",
                lance_agressivo_6m="30%",
                lance_moderado_12m="30%",
                lance_conservador_24m="30%",
                lance_investidor="30%",
            ),
        ])
        self.assertTrue(result["items"][0]["matrix_approved"])
        self.assertTrue(next(s for s in result["items"][0]["cenarios"] if s["id"] == "without_embedded")["credit_compatible"])

    def test_missing_operational_data_excludes_instead_of_becoming_zero(self):
        result = analyze_client_consortium_viability(payload(), [group(taxa_adm=None)])
        self.assertEqual(len(result["items"]), 1)
        self.assertFalse(result["items"][0]["financial_data_complete"])

    def test_status_and_explicit_type_are_eligibility_filters(self):
        result = analyze_client_consortium_viability(payload(tipo_bem="Auto", tipo_bem_explicit=True), [
            group("inactive", status="Inativo"),
            group("wrong-type", tipo_bem="Imovel"),
            group("auto", tipo_bem="Auto"),
        ])
        self.assertEqual([item["grupo"] for item in result["items"]], ["auto"])

    def test_orders_matrix_groups_by_compatible_scenario_before_admin(self):
        result = analyze_client_consortium_viability(payload(
            credito_desejado=600000,
            lance_proprio=460000,
            fgts=0,
            parcela_desejada=4500,
            parcela_limite=12000,
            renda_total=40000,
            contemplacao_perfil="urgent",
        ), [
            group("900", administradora="ZETA", credito_maximo=900000, lance_super_agressivo_3m="70%"),
            group("100", administradora="ALFA", credito_maximo=300000, lance_super_agressivo_3m="70%"),
        ])

        self.assertEqual([item["grupo"] for item in result["items"]], ["900", "100"])
        self.assertEqual(result["audit"]["final_ordering"]["rules"][:3], [
            "Cenário sem lance embutido com crédito, prazo/renda e contemplação compatíveis",
            "Cenário com lance embutido com crédito, prazo/renda e contemplação compatíveis",
            "Demais grupos aprovados na matriz para análise do operador",
        ])

    def test_participant_resources_are_used_when_manual_field_is_zero(self):
        result = analyze_client_consortium_viability(
            payload(
                lance_proprio=100000,
                lance_proprio_participantes=100000,
                lance_proprio_manual=0,
                own_resources_source="participants",
            ),
            [group(percentual_lance_embutido=None)],
        )
        self.assertEqual(result["cliente"]["own_resources_total"], 100000.0)

    def test_percent_normalization_preserves_null_and_accepts_brazilian_formats(self):
        self.assertIsNone(normalize_percent(None))
        self.assertEqual(float(normalize_percent("52,25")), 0.5225)
        self.assertEqual(float(normalize_percent("52,25%")), 0.5225)
        self.assertEqual(float(normalize_percent("0,5225")), 0.5225)
        self.assertIsNone(normalize_percent("101%"))

    def test_audit_records_rfc_version_calculations_and_group_columns(self):
        result = analyze_client_consortium_viability(payload(), [group()])
        audit = result["audit"]
        self.assertEqual(audit["metadata"]["engine_version"], "4.0.138")
        self.assertEqual(audit["metadata"]["rules_version"], "RFC-001-architecture-v4.0")
        self.assertIn("Y", [item["column"] for item in audit["columns_used"]])
        self.assertIn("BL", [item["column"] for item in audit["columns_used"]])
        self.assertEqual(len(audit["group_results"]), 1)

    def test_regression_real_administrators_duplicate_group_and_effective_bid_audit(self):
        result = analyze_client_consortium_viability(payload(
            credito_desejado=600000,
            lance_proprio=481000,
            lance_proprio_declarado=470000,
            lance_simulado=481000,
            contemplacao_perfil="urgent",
            fgts=0,
            parcela_limite=100000,
        ), [
            group("40174", administradora="ITAÚ", lance_super_agressivo_3m="70%", percentual_lance_embutido=None),
            group("1045", administradora="CNP", lance_super_agressivo_3m="70%", percentual_lance_embutido=None),
            group("1049", administradora="CNP", lance_super_agressivo_3m="90%", percentual_lance_embutido=None),
            group("1151", administradora="PORTO", lance_super_agressivo_3m="70%", percentual_lance_embutido=None),
            group("40174", administradora="AUTO-ITAÚ", lance_super_agressivo_3m="70%", percentual_lance_embutido=None),
        ])

        self.assertEqual(set(result["administradoras_analisadas"]), {"ITAÚ", "CNP", "PORTO", "AUTO-ITAÚ"})
        self.assertEqual(len([item for item in result["items"] if item["grupo"] == "40174"]), 2)
        fields = {item["technical_name"]: item["normalized_value"] for item in result["audit"]["client_snapshot"]["raw_fields"]}
        self.assertEqual(fields["fonte_lance_efetivo"], "simulado")
        self.assertEqual(fields["lance_efetivo"], 481000.0)

    def test_regression_profile_can_be_approved_only_with_or_only_without_embedded(self):
        common = dict(
            credito_desejado=600000, lance_proprio=100000, fgts=0, renda_total=40000,
            parcela_desejada=6000, parcela_limite=100000, contemplacao_perfil="urgent",
        )
        only_embedded = analyze_client_consortium_viability(payload(**common), [group(
            "EMBUTIDO", lance_super_agressivo_3m="35%", percentual_lance_embutido="30%",
        )])
        only_without = analyze_client_consortium_viability(payload(**common), [group(
            "SEM-EMBUTIDO", lance_super_agressivo_3m="15%", percentual_lance_embutido="30%",
        )])
        embedded_scenarios = {entry["id"]: entry for entry in only_embedded["items"][0]["cenarios"]}
        without_scenarios = {entry["id"]: entry for entry in only_without["items"][0]["cenarios"]}
        self.assertFalse(next(profile for profile in embedded_scenarios["without_embedded"]["perfis_contemplacao"] if profile["id"] == "super_aggressive")["atinge_perfil"])
        self.assertTrue(next(profile for profile in embedded_scenarios["with_embedded"]["perfis_contemplacao"] if profile["id"] == "super_aggressive")["atinge_perfil"])
        self.assertTrue(next(profile for profile in without_scenarios["without_embedded"]["perfis_contemplacao"] if profile["id"] == "super_aggressive")["atinge_perfil"])

    def test_audit_mapping_reports_missing_term_when_payload_lacks_it(self):
        item = group("SEM-PRAZO", prazo_restante=None, percentual_lance_embutido=None)
        item["mapeamento_origem"] = {"prazo_restante": {"source": "ausente", "header": ""}}
        result = analyze_client_consortium_viability(payload(), [item])
        mapping = result["audit"]["data_source"]["mapping_by_administrator"]["ITAU"]["prazo_restante"]
        self.assertEqual(mapping["missing_rows"], 1)
        self.assertEqual(result["audit"]["group_results"][0]["result"], "matrix_approved")

    def test_composition_requires_minimum_quota_to_fit_the_income_limit(self):
        result = analyze_client_consortium_viability(payload(
            credito_desejado=600000, parcela_limite=12000, renda_total=40000,
        ), [group(
            "PARCELA-ALTA", credito_maximo=300000, prazo_restante=30,
            percentual_lance_embutido=None,
        )])
        self.assertEqual(len(result["items"]), 1)
        self.assertTrue(result["items"][0]["requires_composition"])

    def test_invalid_source_identity_is_audited_but_never_reaches_matrix(self):
        result = analyze_client_consortium_viability(payload(), [
            group("", administradora=""),
            group("40174", administradora="ITAÚ", percentual_lance_embutido=None),
        ])
        self.assertEqual(len(result["matrix_items"]), 1)
        self.assertEqual(result["matrix_items"][0]["grupo"], "40174")
        self.assertEqual(result["audit"]["group_results"][0]["result"], "excluded_invalid_identity")

    def test_audit_refinement_steps_receive_only_the_previous_stage_output(self):
        result = analyze_client_consortium_viability(payload(contemplacao_perfil="urgent", lance_proprio=500000, parcela_limite=100000), [
            group("APROVADO", percentual_lance_embutido=None, lance_super_agressivo_3m="10%"),
            group("PERFIL", percentual_lance_embutido=None, lance_super_agressivo_3m="99%"),
        ])
        steps = {step["id"]: step for step in result["audit"]["execution_steps"]}
        self.assertEqual(steps["operator_analysis"]["input_count"], steps["matrix"]["approved_count"])
        self.assertEqual(steps["ranking"]["input_count"], steps["operator_analysis"]["approved_count"])

    def test_declared_objective_mapping_remains_specific(self):
        self.assertEqual(map_declared_objective_to_preference("Contemplar - urgente - 3 meses"), "urgent")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - rapido - 6 meses"), "fast")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - moderado - 12 meses"), "moderate")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - conservador - 24 meses"), "conservative")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - investidor - 36 meses"), "long_term")
        self.assertEqual(map_declared_objective_to_preference("Investidor - carta"), "investment")


if __name__ == "__main__":
    unittest.main()
