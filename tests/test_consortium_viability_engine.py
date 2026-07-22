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
    }
    values.update(overrides)
    return values


class Motor360RfcTest(unittest.TestCase):
    def test_official_scenarios_preserve_credit_and_do_not_share_values(self):
        result = analyze_client_consortium_viability(payload(), [group()])
        scenarios = result["items"][0]["cenarios"]
        without = next(item for item in scenarios if item["id"] == "without_embedded")
        embedded = next(item for item in scenarios if item["id"] == "with_embedded")

        self.assertEqual(without["credito_contratado"], 1100000.0)
        self.assertEqual(without["taxa_administracao"], 176000.0)
        self.assertEqual(without["fundo_reserva"], 33000.0)
        self.assertEqual(without["saldo_devedor"], 1309000.0)
        self.assertEqual(without["lance_total"], 150000.0)
        self.assertEqual(without["saldo_apos_lance"], 1159000.0)
        self.assertEqual(without["prazo_inicial_desejada_meses"], 202)
        self.assertEqual(without["prazo_apos_lance_limite_renda_meses"], 78)
        self.assertTrue(without["liquidez_preservada"])

        self.assertEqual(embedded["credito_contratado"], 1571428.57)
        self.assertEqual(embedded["valor_lance_embutido"], 471428.57)
        self.assertEqual(embedded["taxa_administracao"], 251428.57)
        self.assertEqual(embedded["fundo_reserva"], 47142.86)
        self.assertEqual(embedded["saldo_devedor"], 1870000.0)
        self.assertEqual(embedded["lance_total"], 621428.57)
        self.assertEqual(embedded["saldo_apos_lance"], 1248571.43)
        self.assertEqual(embedded["prazo_apos_lance_limite_renda_meses"], 84)
        self.assertTrue(embedded["liquidez_preservada"])

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
            group("outside", credito_minimo=100000, credito_maximo=1049999),
            group("inside", credito_minimo=900000, credito_maximo=1100000, percentual_lance_embutido=None, lance_moderado_12m="5%"),
        ])
        self.assertEqual([item["grupo"] for item in result["items"]], ["inside"])
        self.assertEqual(result["items"][0]["cenarios"][0]["saldo_devedor"], 1249500.0)

    def test_remaining_term_is_compared_to_ceil_after_bid_income_term(self):
        result = analyze_client_consortium_viability(payload(), [
            group("enough", prazo_restante=78, percentual_lance_embutido=None),
            group("short", prazo_restante=77, percentual_lance_embutido=None),
        ])
        self.assertEqual([item["grupo"] for item in result["items"]], ["enough"])
        reasons = result["audit"]["excluded_groups"][0]["detail"]
        self.assertIn("prazo_remanescente_insuficiente", reasons)

    def test_objective_is_priority_not_an_exclusion_rule(self):
        result = analyze_client_consortium_viability(payload(objetivo="Contemplar - urgente - 3 meses"), [
            group(percentual_lance_embutido=None, lance_super_agressivo_3m="90%", lance_agressivo_6m="80%", lance_moderado_12m="10%"),
        ])
        item = result["items"][0]
        self.assertIn("moderate", item["compatible_contemplation_strategies"])
        self.assertFalse(item["destaque_preferencia"])

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
        self.assertEqual(audit["metadata"]["engine_version"], "4.0.0")
        self.assertEqual(audit["metadata"]["rules_version"], "RFC-001-architecture-v4.0")
        self.assertIn("X", [item["column"] for item in audit["columns_used"]])
        self.assertIn("BL", [item["column"] for item in audit["columns_used"]])
        self.assertEqual(len(audit["group_results"]), 1)

    def test_declared_objective_mapping_remains_specific(self):
        self.assertEqual(map_declared_objective_to_preference("Contemplar - urgente - 3 meses"), "urgent")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - rapido - 6 meses"), "fast")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - moderado - 12 meses"), "moderate")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - conservador - 24 meses"), "conservative")
        self.assertEqual(map_declared_objective_to_preference("Contemplar - investidor - 36 meses"), "long_term")
        self.assertEqual(map_declared_objective_to_preference("Investidor - carta"), "investment")


if __name__ == "__main__":
    unittest.main()
