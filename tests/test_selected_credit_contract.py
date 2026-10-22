"""Regression contract for selected credit options and server-side study math."""

import copy
import unittest
from unittest.mock import patch

from backend.credit_options import available_credit_options
from backend.financial_studies import _validate_selected_credit_basis
from backend.selected_credit_math import calculate_selected_credit


def _scenario(scenario_id, credit, embedded_percent, own_bid):
    expected = calculate_selected_credit(
        credit=credit,
        embedded_percent=embedded_percent,
        administration_rate=0.15,
        reserve_rate=0.02,
        remaining_term=130,
        own_bid=own_bid,
    )
    scenario = {
        "id": scenario_id,
        "selected_credit": expected["contracted_credit"],
        "credito_contratado": expected["contracted_credit"],
        "credito_liquido_projetado": expected["liquid_credit"],
        "valor_lance_embutido": expected["embedded_bid"],
        "lance_embutido": expected["embedded_bid"],
        "taxa_administracao": expected["administration_fee"],
        "fundo_reserva_valor": expected["reserve_fee"],
        "saldo_devedor": expected["remaining_balance"],
        "parcela_inicial": expected["initial_installment"],
        "parcela_pos_contemplacao": expected["post_contemplation_installment"],
        "lance_cliente_total": expected["own_bid"],
        "lance_total_cenario": expected["total_bid"],
    }
    contract = {
        "scenario": scenario_id,
        "contracted_credit": expected["contracted_credit"],
        "liquid_credit": expected["liquid_credit"],
        "embedded_bid": expected["embedded_bid"],
        "initial_installment": expected["initial_installment"],
        "post_contemplation_installment": expected["post_contemplation_installment"],
        "remaining_balance": expected["remaining_balance"],
        "own_bid": expected["own_bid"],
        "total_bid": expected["total_bid"],
    }
    return scenario, contract


def _snapshot():
    without, without_contract = _scenario("without_embedded", 200_000, 0, 10_000)
    with_embedded, embedded_contract = _scenario("with_embedded", 300_000, 0.30, 20_000)
    group = {
        "group": "G-1",
        "administrator": "BANK",
        "source_row": 17,
        "study_credit_basis": "credito_escolhido_por_cenario",
        "calculation_contract_version": 1,
        "quotas_by_scenario": {"without_embedded": 1, "with_embedded": 1},
        "selected_credit_by_scenario": {"without_embedded": 200_000, "with_embedded": 300_000},
        "available_credit_options": [
            {"value": value, "source_fields": [field], "sources": [{"field": field, "column": None, "header": None, "source": None}]}
            for value, field in (
                (100_000, "credito_minimo"), (200_000, "credito_intermediario_1"),
                (300_000, "credito_intermediario_2"), (400_000, "credito_maximo"),
            )
        ],
        "credito_minimo": 100_000,
        "credito_intermediario_1": 200_000,
        "credito_intermediario_2": 300_000,
        "credito_intermediario_3": None,
        "credito_maximo": 400_000,
        "credit_max": 400_000,
        "percentual_lance_embutido": 0.30,
        "taxa_adm": 0.15,
        "fundo_reserva": 0.02,
        "remaining_term": 130,
        "selected_scenarios": [without, with_embedded],
        "contracts": [without_contract, embedded_contract],
        "source_mapping": {},
    }
    return {
        "motor360_audit_id": "AUD-FIXTURE-1",
        "motor_engine_version": "4.0.226",
        "client": {"available_bid": 25_000},
        "groups": [group],
    }


def _validate_with_audit(snapshot):
    audit = {
        "metadata": {"engine_version": "4.0.226"},
        "group_results": [{
            "grupo": "G-1", "administradora": "BANK", "source_row": 17,
            "source_values": {
                "credito_minimo": 100_000,
                "credito_intermediario_1": 200_000,
                "credito_intermediario_2": 300_000,
                "credito_intermediario_3": None,
                "credito_maximo": 400_000,
                "taxa_adm": 0.15,
                "fundo_reserva": 0.02,
                "percentual_lance_embutido": 0.30,
                "prazo_restante": 130,
            },
        }],
    }
    with patch("backend.financial_studies.get_motor360_audit", return_value=audit):
        _validate_selected_credit_basis(snapshot)


class SelectedCreditContractTest(unittest.TestCase):
    def test_credit_options_are_positive_deduplicated_and_retain_origins(self):
        group = {
            "credito_minimo": "R$ 100.000,00",
            "credito_intermediario_1": 200_000,
            "credito_intermediario_2": 200_000,
            "credito_intermediario_3": None,
            "credito_maximo": 400_000,
            "source_mapping": {"credito_maximo": {"column": "V", "header": "Maior Crédito", "source": "planilha"}},
        }
        options = available_credit_options(group)
        self.assertEqual([row["value"] for row in options], [100_000, 200_000, 400_000])
        self.assertEqual(options[1]["source_fields"], ["credito_intermediario_1", "credito_intermediario_2"])
        self.assertEqual(options[-1]["sources"][0]["column"], "V")

    def test_server_math_keeps_embedded_and_non_embedded_scenarios_distinct(self):
        plain = calculate_selected_credit(
            credit=200_000, embedded_percent=0, administration_rate=0.15,
            reserve_rate=0.02, remaining_term=130, own_bid=10_000,
        )
        embedded = calculate_selected_credit(
            credit=300_000, embedded_percent=0.30, administration_rate=0.15,
            reserve_rate=0.02, remaining_term=130, own_bid=20_000,
        )
        self.assertEqual(plain["liquid_credit"], 200_000)
        self.assertEqual(plain["embedded_bid"], 0)
        self.assertEqual(embedded["contracted_credit"], 300_000)
        self.assertEqual(embedded["embedded_bid"], 90_000)
        self.assertEqual(embedded["liquid_credit"], 210_000)
        self.assertEqual(embedded["total_bid"], 110_000)

    def test_valid_independent_scenario_snapshot_passes(self):
        _validate_with_audit(_snapshot())

    def test_new_snapshot_requires_audited_engine_identity(self):
        snapshot = _snapshot()
        snapshot["motor_engine_version"] = None
        with self.assertRaisesRegex(ValueError, "versão do Motor"):
            _validate_with_audit(snapshot)

    def test_altered_installment_or_liquid_credit_is_rejected(self):
        snapshot = _snapshot()
        snapshot["groups"][0]["selected_scenarios"][1]["credito_liquido_projetado"] += 1
        with self.assertRaisesRegex(ValueError, "Crédito líquido"):
            _validate_with_audit(snapshot)

    def test_scenario_budget_is_checked_separately_not_added_across_alternatives(self):
        snapshot = _snapshot()
        # Each alternative has its own R$25k ceiling; alternatives are not added.
        _validate_with_audit(snapshot)
        # More contracts inside one alternative may not reuse that budget.
        snapshot = copy.deepcopy(snapshot)
        group = snapshot["groups"][0]
        group["quotas_by_scenario"]["without_embedded"] = 3
        group["contracts"].extend([copy.deepcopy(group["contracts"][0]), copy.deepcopy(group["contracts"][0])])
        with self.assertRaisesRegex(ValueError, "recursos compartilhados"):
            _validate_with_audit(snapshot)


if __name__ == "__main__":
    unittest.main()
