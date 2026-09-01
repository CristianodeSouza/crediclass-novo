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
        "historico_12_meses": [
            {"mes": "2025-07", "qtd_contemplacoes": 3},
            {"mes": "2025-08", "qtd_contemplacoes": 3},
            {"mes": "2025-09", "qtd_contemplacoes": 3},
            {"mes": "2025-10", "qtd_contemplacoes": 3},
            {"mes": "2025-11", "qtd_contemplacoes": 3},
            {"mes": "2025-12", "qtd_contemplacoes": 3},
            {"mes": "2026-01", "qtd_contemplacoes": 3},
            {"mes": "2026-02", "qtd_contemplacoes": 3},
            {"mes": "2026-03", "qtd_contemplacoes": 3},
            {"mes": "2026-04", "qtd_contemplacoes": 3},
            {"mes": "2026-05", "qtd_contemplacoes": 3},
            {"mes": "2026-06", "qtd_contemplacoes": 3},
        ],
    }
    values.update(overrides)
    return values


class Motor360RfcTest(unittest.TestCase):
    def test_investidor_objective_maps_to_long_term_profile(self):
        self.assertEqual(map_declared_objective_to_preference("Investidor - 36 meses"), "long_term")

    def test_lista_grupo_menor_para_composicao_manual_de_ate_50_cotas(self):
        history = [
            {"mes": "2026-04", "qtd_contemplacoes": 2},
            {"mes": "2026-05", "qtd_contemplacoes": 4},
            {"mes": "2026-06", "qtd_contemplacoes": 3},
        ]
        result = analyze_client_consortium_viability(payload(credito_desejado=600000), [
            group(credito_minimo=100000, credito_maximo=300000, historico_12_meses=history, percentual_lance_embutido=""),
        ])

        self.assertEqual(result["items"], [])
        self.assertEqual(result["total_grupos_composicao"], 1)
        item = result["composition_items"][0]
        self.assertEqual(item["cotas_minimas_sem_embutido"], 2)
        self.assertEqual(item["cotas_maximas"], 50)
        self.assertEqual(item["cenarios"][0]["credito_liquido_projetado"], 300000)
        self.assertTrue(item["capacidade_contemplacoes"])
        self.assertEqual(item["historico_12_meses"], history)
        self.assertEqual([scenario["id"] for scenario in item["cenarios"]], ["without_embedded", "with_embedded"])
        self.assertEqual(item["cenarios"][0]["lance_cliente_total"], 150000)
        self.assertTrue(item["cenarios"][0]["initial_installment_compatible"])
        self.assertEqual(item["cenarios"][1]["creation_status"], "not_created")
        self.assertEqual(item["cenarios"][1]["creation_reason"], "percentual_x_ausente")
        self.assertEqual(item["cenarios"][1]["credito_contratado"], 300000)
        self.assertEqual(item["cenarios"][1]["credito_liquido_projetado"], 300000)
        self.assertIsNotNone(item["cenarios"][1]["parcela_inicial"])
        self.assertIsNotNone(item["cenarios"][1]["saldo_devedor"])
        self.assertEqual(item["cenarios"][1]["lance_total_cenario"], 150000)
        self.assertEqual(item["cenarios"][1]["perfis_contemplacao"][0]["percentual_referencia"], item["cenarios"][0]["perfis_contemplacao"][0]["percentual_referencia"])

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
        self.assertEqual(capacity["meses_contemplados"], 3)
        self.assertEqual(capacity["media_contemplacoes"], 3.0)
        self.assertEqual(capacity["limite_cotas"], 3)
        self.assertEqual(result["items"][0]["historico_12_meses"], history)

    def test_regra_de_contemplacao_exige_ao_menos_dois_meses_no_periodo_do_objetivo(self):
        history = [
            {"mes": "2024-01", "qtd_contemplacoes": 1},
            {"mes": "2024-02", "qtd_contemplacoes": 0},
            {"mes": "2024-03", "qtd_contemplacoes": 0},
            {"mes": "2024-04", "qtd_contemplacoes": 0},
            {"mes": "2024-05", "qtd_contemplacoes": 0},
            {"mes": "2024-06", "qtd_contemplacoes": 0},
            {"mes": "2024-07", "qtd_contemplacoes": 0},
            {"mes": "2024-08", "qtd_contemplacoes": 0},
            {"mes": "2024-09", "qtd_contemplacoes": 0},
            {"mes": "2024-10", "qtd_contemplacoes": 0},
            {"mes": "2024-11", "qtd_contemplacoes": 0},
            {"mes": "2024-12", "qtd_contemplacoes": 1},
            {"mes": "2025-01", "qtd_contemplacoes": 0},
            {"mes": "2025-02", "qtd_contemplacoes": 0},
            {"mes": "2025-03", "qtd_contemplacoes": 0},
            {"mes": "2025-04", "qtd_contemplacoes": 0},
            {"mes": "2025-05", "qtd_contemplacoes": 0},
            {"mes": "2025-06", "qtd_contemplacoes": 1},
            {"mes": "2025-07", "qtd_contemplacoes": 0},
            {"mes": "2025-08", "qtd_contemplacoes": 0},
            {"mes": "2025-09", "qtd_contemplacoes": 0},
            {"mes": "2025-10", "qtd_contemplacoes": 0},
            {"mes": "2025-11", "qtd_contemplacoes": 0},
            {"mes": "2025-12", "qtd_contemplacoes": 1},
            {"mes": "2026-01", "qtd_contemplacoes": 0},
            {"mes": "2026-02", "qtd_contemplacoes": 0},
            {"mes": "2026-03", "qtd_contemplacoes": 0},
            {"mes": "2026-04", "qtd_contemplacoes": 0},
            {"mes": "2026-05", "qtd_contemplacoes": 0},
            {"mes": "2026-06", "qtd_contemplacoes": 1},
        ]
        result = analyze_client_consortium_viability(
            payload(objetivo="Investidor - 36 meses"),
            [group(historico_12_meses=history[-12:], historico_periodos=history)],
        )

        self.assertEqual(result["items"], [])
        capacity = result["credit_items"][0]["capacidade_contemplacoes_selecionada"]
        self.assertEqual(capacity["janela_meses"], 36)
        self.assertEqual(capacity["meses_contemplados"], 5)
        self.assertAlmostEqual(capacity["media_contemplacoes"], 0.17, places=2)
        self.assertFalse(capacity["atinge_regra_minima"])

    def test_capacidade_selecionada_no_motor360_segue_o_objetivo_declarado(self):
        history = [
            {"mes": "2026-04", "qtd_contemplacoes": 2},
            {"mes": "2026-05", "qtd_contemplacoes": 2},
            {"mes": "2026-06", "qtd_contemplacoes": 2},
        ]
        result = analyze_client_consortium_viability(
            payload(objetivo="Urgente - 3 meses"),
            [
                group(
                    historico_12_meses=history,
                    lance_super_agressivo_3m="10%",
                    lance_agressivo_6m="10%",
                    lance_moderado_12m="10%",
                    lance_conservador_24m="10%",
                    lance_investidor="10%",
                )
            ],
        )

        item = result["items"][0]
        self.assertEqual(item["best_contemplation_strategy"], "Urgente - 3 meses")
        self.assertEqual(item["capacidade_contemplacoes_selecionada"]["perfil"], "Urgente - 3 meses")
        self.assertEqual(item["capacidade_contemplacoes_selecionada"]["janela_meses"], 3)
        self.assertEqual(item["capacidade_contemplacoes_selecionada"]["meses_contemplados"], 3)
        self.assertEqual(item["capacidade_contemplacoes_selecionada"]["media_contemplacoes"], 2.0)
        self.assertTrue(item["capacidade_contemplacoes_selecionada"]["atinge_regra_minima"])
        self.assertEqual(
            [profile["label"] for profile in item["cenarios"][0]["perfis_contemplacao"]],
            ["Urgente", "Rápido", "Moderado", "Conservador", "Investidor"],
        )

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

        self.assertEqual(embedded["credito_contratado"], 1235000.0)
        self.assertEqual(embedded["valor_lance_embutido"], 285000.0)
        self.assertEqual(embedded["taxa_administracao"], 197600.0)
        self.assertEqual(embedded["fundo_reserva"], 37050.0)
        self.assertEqual(embedded["saldo_devedor"], 1469650.0)
        self.assertEqual(embedded["lance_total"], 435000.0)
        self.assertEqual(embedded["lance_cliente_total"], 150000.0)
        self.assertAlmostEqual(embedded["percentual_lance_cliente"], 150000 / 1235000, places=6)
        self.assertEqual(embedded["saldo_apos_lance"], 1034650.0)
        self.assertEqual(embedded["parcela_pos_contemplacao"], 3443.98)
        self.assertEqual(embedded["prazo_apos_lance_limite_renda_meses"], 69)
        self.assertTrue(embedded["liquidez_preservada"])
        item = result["items"][0]
        self.assertEqual(item["parcela_inicial_sem_embutido"], 3768.33)
        self.assertEqual(item["parcela_inicial_com_embutido"], 4898.83)

    def test_null_percentage_remains_null_and_only_embedded_scenario_is_not_created(self):
        result = analyze_client_consortium_viability(payload(), [group(percentual_lance_embutido=None)])
        scenarios = result["items"][0]["cenarios"]
        without = next(item for item in scenarios if item["id"] == "without_embedded")
        embedded = next(item for item in scenarios if item["id"] == "with_embedded")
        self.assertTrue(without["eligible"])
        self.assertEqual(embedded["creation_status"], "not_created")
        self.assertEqual(embedded["creation_reason"], "percentual_x_ausente")
        self.assertIsNone(embedded["credito_contratado"])

    def test_empty_reserve_fund_is_informational_and_does_not_block_calculation(self):
        result = analyze_client_consortium_viability(
            payload(credito_desejado=400000, lance_proprio=200000, fgts=100000, parcela_desejada=6000, parcela_limite=12000, renda_total=40000),
            [group("40038", fundo_reserva=None, percentual_lance_embutido=None, taxa_adm="36%", prazo_restante=192, credito_minimo=296216, credito_maximo=575970)],
        )

        self.assertEqual(result["total_grupos_preselecionados"], 1)
        item = result["items"][0]
        without = next(entry for entry in item["cenarios"] if entry["id"] == "without_embedded")
        self.assertEqual(without["fundo_reserva"], 0.0)
        self.assertEqual(without["saldo_devedor"], 544000.0)
        self.assertEqual(without["parcela_inicial"], 2833.33)
        self.assertEqual(without["parcela_pos_contemplacao"], 1262.65)
        self.assertTrue(without["term_compatible"])

        audit = result["audit"]
        self.assertEqual(audit["summary"]["groups_with_incomplete_data"], 0)
        self.assertEqual(audit["summary"]["incomplete_field_occurrences"], 0)
        self.assertEqual(audit["execution_steps"][3]["incomplete_count"], 0)

        group_audit = next(entry for entry in audit["group_results"] if entry["grupo"] == "40038")
        reserve_field = next(field for field in group_audit["missing_fields"] if field["column"] == "AA")
        self.assertEqual(reserve_field["impact"], "informational_only")

    def test_credit_range_uses_nominal_contracted_credit_not_debt(self):
        result = analyze_client_consortium_viability(payload(fgts=0), [
            group("outside", credito_minimo=100000, credito_maximo=949999),
            group("inside", credito_minimo=900000, credito_maximo=1100000, percentual_lance_embutido=None, lance_moderado_12m="5%"),
        ])
        self.assertEqual([item["grupo"] for item in result["items"]], ["inside"])
        self.assertEqual(result["items"][0]["cenarios"][0]["saldo_devedor"], 1130500.0)

    def test_initial_installment_must_respect_income_limit(self):
        result = analyze_client_consortium_viability(payload(), [
            group("enough", prazo_restante=300, percentual_lance_embutido=None, taxa_adm="16%"),
            group("above-limit", prazo_restante=60, percentual_lance_embutido=None, taxa_adm="80%"),
        ])
        self.assertEqual([item["grupo"] for item in result["items"]], ["enough"])
        reasons = result["audit"]["excluded_groups"][0]["detail"]
        self.assertIn("parcela_inicial_acima_do_limite_de_renda", reasons)

    def test_credit_stage_remains_visible_when_later_rules_reject_group(self):
        result = analyze_client_consortium_viability(payload(), [
            group("credit-only", prazo_restante=1, percentual_lance_embutido=None),
        ])
        self.assertEqual(result["items"], [])
        self.assertEqual(result["total_grupos_credito_compativeis"], 1)
        self.assertEqual([item["grupo"] for item in result["credit_items"]], ["credit-only"])

    def test_objective_is_an_exclusion_rule_for_preselection(self):
        result = analyze_client_consortium_viability(payload(objetivo="Contemplar - urgente - 3 meses"), [
            group(percentual_lance_embutido=None, lance_super_agressivo_3m="90%", lance_agressivo_6m="80%", lance_moderado_12m="10%"),
        ])
        self.assertEqual(result["items"], [])
        self.assertEqual(result["total_grupos_credito_compativeis"], 1)
        self.assertEqual(result["credit_items"][0]["objective_compatible"], False)
        self.assertIn("perfil_objetivo_nao_atingido", result["audit"]["excluded_groups"][0]["detail"])

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
        self.assertAlmostEqual(embedded["percentual_lance_cliente"], 200000 / 780000, places=6)
        self.assertEqual(embedded["lance_embutido"], 180000.0)
        self.assertEqual(embedded["lance_total_cenario"], 380000.0)
        self.assertAlmostEqual(embedded["percentual_lance_efetivo"], 380000 / 780000, places=6)
        self.assertIn("moderate", without["compatible_contemplation_strategies"])
        self.assertIn("moderate", embedded["compatible_contemplation_strategies"])
        moderate = next(profile for profile in without["perfis_contemplacao"] if profile["id"] == "moderate")
        self.assertEqual(moderate["percentual_referencia"], 0.25)
        self.assertEqual(moderate["lance_ideal"], 150000.0)
        self.assertEqual(moderate["falta_para_ideal"], 0)
        embedded_moderate = next(profile for profile in embedded["perfis_contemplacao"] if profile["id"] == "moderate")
        self.assertEqual(embedded_moderate["lance_ideal_total"], 195000.0)
        self.assertEqual(embedded_moderate["lance_embutido"], 180000.0)
        self.assertEqual(embedded_moderate["lance_ideal"], 15000.0)
        self.assertEqual(embedded_moderate["falta_para_ideal"], 0.0)

    def test_preselection_requires_history_average_for_declared_objective(self):
        result = analyze_client_consortium_viability(payload(), [
            group(
                historico_12_meses=[
                    {"mes": "2026-04", "qtd_contemplacoes": 1},
                    {"mes": "2026-05", "qtd_contemplacoes": 1},
                    {"mes": "2026-06", "qtd_contemplacoes": 1},
                ],
                percentual_lance_embutido=None,
                lance_super_agressivo_3m="10%",
                lance_agressivo_6m="10%",
                lance_moderado_12m="10%",
                lance_conservador_24m="10%",
                lance_investidor="10%",
            ),
        ])
        self.assertEqual(result["total_grupos_credito_compativeis"], 1)
        self.assertEqual(result["total_grupos_preselecionados"], 0)
        self.assertIn("media_contemplacao_abaixo_da_regra_minima", result["audit"]["excluded_groups"][0]["detail"])

    def test_golden_preselection_split_keeps_credit_and_term_stages_separate(self):
        approved = ["40112", "40174", "40105", "40098", "40090", "40086", "1820", "1038", "1031", "1026", "1019"]
        term_rejected = ["1176", "1011", "1770", "1006"]
        groups = [group(identifier, prazo_restante=240, percentual_lance_embutido=None) for identifier in approved]
        groups.extend(group(identifier, prazo_restante=1, percentual_lance_embutido=None) for identifier in term_rejected)
        result = analyze_client_consortium_viability(
            payload(credito_desejado=600000, lance_proprio=100000, fgts=100000, renda_total=40000, parcela_desejada=6000, parcela_limite=12000),
            groups,
        )
        self.assertEqual(result["total_grupos_credito_compativeis"], 15)
        self.assertEqual(result["total_grupos_preselecionados"], 11)
        self.assertEqual({item["grupo"] for item in result["items"]}, set(approved))
        self.assertEqual(result["audit"]["summary"]["total_term_income_rejected"], 4)

    def test_term_rejection_keeps_only_the_consolidated_term_reason(self):
        result = analyze_client_consortium_viability(payload(), [
            group("1770", credito_minimo=400000, credito_maximo=1100000, prazo_restante=1),
        ])
        audit_entry = result["audit"]["group_results"][0]
        self.assertEqual(audit_entry["result"], "excluded_term_income")
        self.assertEqual(audit_entry["justification"], ["parcela_inicial_acima_do_limite_de_renda"])

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
                lance_moderado_12m="10%",
                lance_conservador_24m="30%",
                lance_investidor="30%",
            ),
        ])
        classification = result["items"][0]["contemplation_classification"]
        self.assertEqual(classification["strategies"], ["moderate"])
        self.assertEqual(classification["ignored_scenarios"][0]["scenario_id"], "with_embedded")
        self.assertEqual(classification["ignored_scenarios"][0]["reason"], "credito_fora_da_faixa")

    def test_missing_operational_data_excludes_instead_of_becoming_zero(self):
        result = analyze_client_consortium_viability(payload(), [group(taxa_adm=None)])
        self.assertEqual(result["items"], [])
        self.assertIn("taxa_administracao_nao_informada", result["audit"]["excluded_groups"][0]["detail"])

    def test_status_and_explicit_type_are_eligibility_filters(self):
        result = analyze_client_consortium_viability(payload(tipo_bem="Auto", tipo_bem_explicit=True), [
            group("inactive", status="Inativo"),
            group("wrong-type", tipo_bem="Imovel"),
            group("auto", tipo_bem="Auto"),
        ])
        self.assertEqual([item["grupo"] for item in result["items"]], ["auto"])

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
        self.assertEqual(audit["metadata"]["engine_version"], "4.0.112")
        self.assertEqual(audit["metadata"]["rules_version"], "RFC-001-architecture-v4.0")
        self.assertIn("Y", [item["column"] for item in audit["columns_used"]])
        self.assertIn("BM", [item["column"] for item in audit["columns_used"]])
        self.assertEqual(len(audit["group_results"]), 1)

    def test_declared_objective_mapping_remains_specific(self):
        self.assertEqual(map_declared_objective_to_preference("Contemplar - urgente - 3 meses"), "urgent")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - rapido - 6 meses"), "fast")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - moderado - 12 meses"), "moderate")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - conservador - 24 meses"), "conservative")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - investidor - 36 meses"), "long_term")
        self.assertEqual(map_declared_objective_to_preference("Urgente - 3 meses"), "urgent")
        self.assertEqual(map_declared_objective_to_preference("Rapido - 6 meses"), "fast")
        self.assertEqual(map_declared_objective_to_preference("Moderado - 12 meses"), "moderate")
        self.assertEqual(map_declared_objective_to_preference("Conservador - 24 meses"), "conservative")
        self.assertEqual(map_declared_objective_to_preference("Investidor - 36 meses"), "long_term")
        self.assertEqual(map_declared_objective_to_preference("Investidor - carta"), "long_term")


if __name__ == "__main__":
    unittest.main()
