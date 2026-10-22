"""Contract check for the real Motor 360 endpoint using a source-row fixture."""

import unittest
from unittest.mock import patch

from fastapi import Response

from backend.main import viabilidade_360_analisar
from backend.models import ViabilidadeRequest


class Motor360ApiContractTest(unittest.TestCase):
    def test_endpoint_filters_asset_type_before_passing_groups_to_engine(self):
        property_group = {"grupo": "126", "administradora": "ITAÚ", "tipo_bem": "Imóvel"}
        auto_group = {"grupo": "A1", "administradora": "ITAÚ", "tipo_bem": "Automóvel"}
        request = ViabilidadeRequest(
            objetivo="Contemplar - urgente - 3 meses", credito_desejado=600000,
            prazo_desejado=3, lance_proprio=460000, fgts=0, renda_total=40000,
            parcela_desejada=4500, parcela_limite=12000,
            tipo_bem="Imóvel", tipo_bem_explicit=True,
        )
        analysis = {"audit": {"metadata": {}, "data_source": {}, "summary": {}, "execution_steps": []}}
        with patch("backend.main.list_grupos", return_value=[property_group, auto_group]), patch(
            "backend.main.analyze_client_consortium_viability", return_value=analysis
        ) as analyze, patch(
            "backend.main.save_motor360_audit", return_value={"metadata": {"audit_id": "AUD-TYPE-FILTER"}}
        ):
            result = viabilidade_360_analisar(request, Response())

        self.assertEqual(analyze.call_args.args[1], [property_group])
        self.assertEqual(result["grupos_na_base"], 2)
        self.assertEqual(result["grupos_filtrados_por_tipo_bem"], 1)
        self.assertEqual(result["grupos_ignorados_por_tipo_bem"], 1)

    def test_source_row_fields_survive_analysis_and_endpoint_serialization(self):
        source_row = {
            "grupo_id": "1011", "grupo": "1011", "grupo_raw": "1011", "source_row": 59,
            "administradora": "CNP", "tipo_bem": "Imovel", "status": "Ativo",
            "credito_minimo": 717519.32, "credito_maximo": 1255658.79,
            "prazo_restante": 61, "vencimento_parcela": "10",
            "taxa_adm": 0.20, "fundo_reserva": 0.05,
            "percentual_lance_embutido": 0.30,
            "lance_super_agressivo_3m": "40%", "lance_agressivo_6m": "30%",
            "lance_moderado_12m": "10%", "lance_conservador_24m": "5%",
            "lance_investidor": "2%", "historico_12_meses": [],
            "mapeamento_origem": {
                "credito_maximo": {"column": "V", "header": "Maior Crédito"},
                "taxa_adm": {"column": "AD", "header": "Taxa ADM total"},
                "historico:2026-06:qtd_contemplacoes": {"column": "X", "header": "Histórico"},
            },
        }
        request = ViabilidadeRequest(
            objetivo="Contemplar - moderado - 12 meses", credito_desejado=600000,
            prazo_desejado=12, lance_proprio=460000, fgts=0, renda_total=40000,
            parcela_desejada=4500, parcela_limite=12000,
        )
        audit_capture = {}

        def save_audit(audit):
            audit_capture.update(audit)
            return {"metadata": {"audit_id": "AUD-CONTRACT-FIXTURE"}}

        response = Response()
        with patch("backend.main.list_grupos", return_value=[source_row]), patch(
            "backend.main.save_motor360_audit", side_effect=save_audit
        ):
            result = viabilidade_360_analisar(request, response, compact=True)

        self.assertEqual(result["audit_id"], "AUD-CONTRACT-FIXTURE")
        self.assertEqual(result["engine_version"], "4.0.231")
        self.assertNotIn("items", result)
        self.assertNotIn("credit_items", result)
        self.assertNotIn("composition_items", result)
        self.assertTrue(all(set(row) <= {"grupo", "grupo_id", "administradora", "eligible_scenarios", "cenarios"} for row in result["matrix_items"]))
        self.assertEqual(result["total_grupos_analisados"], 1)
        item = next(row for row in result["final_items"] if row["grupo"] == "1011")
        self.assertEqual(
            [option["value"] for option in item["available_credit_options"]],
            [717519.32, 1255658.79],
        )
        self.assertEqual(item["available_credit_options"][0]["source_fields"], ["credito_minimo"])
        self.assertNotIn("source_values", item)
        self.assertEqual(set(item["mapeamento_origem"]), {"credito_maximo", "taxa_adm"})
        self.assertEqual(
            {key: item[key] for key in ("grupo_raw", "source_row", "credito_minimo", "credito_maximo", "prazo_restante", "vencimento_parcela")},
            {"grupo_raw": "1011", "source_row": 59, "credito_minimo": 717519.32,
             "credito_maximo": 1255658.79, "prazo_restante": 61, "vencimento_parcela": "10"},
        )
        self.assertAlmostEqual(item["taxa_adm"], 0.20)
        self.assertAlmostEqual(item["fundo_reserva"], 0.05)
        self.assertEqual({scenario["id"] for scenario in item["cenarios"]}, {"without_embedded", "with_embedded"})
        without = next(s for s in item["cenarios"] if s["id"] == "without_embedded")
        self.assertAlmostEqual(without["credito_contratado"], 600000)
        self.assertAlmostEqual(without["percentual_lance_cliente"], 460000 / 600000)
        audit_group = next(row for row in audit_capture["group_results"] if row["grupo"] == "1011")
        self.assertEqual(audit_group["source_row"], 59)
        self.assertEqual(audit_group["source_values"]["credito_maximo"], 1255658.79)
        timing = response.headers.get("Server-Timing", "")
        for phase in ("sheet_load", "engine", "audit_save", "total"):
            self.assertRegex(timing, rf"(?:^|, )\s*{phase};dur=[0-9.]+")

    def test_endpoint_preserves_legacy_payload_unless_compact_is_requested(self):
        analysis = {
            "items": [{"grupo": "G1"}], "final_items": [{"grupo": "G1"}],
            "credit_items": [{"grupo": "G1"}], "composition_items": [{"grupo": "G1"}],
            "matrix_items": [{"grupo": "G1", "cenarios": []}],
            "audit": {"metadata": {}, "data_source": {}, "summary": {}, "execution_steps": []},
        }
        request = ViabilidadeRequest(
            objetivo="Contemplar", credito_desejado=100000, prazo_desejado=12,
            lance_proprio=0, fgts=0, renda_total=10000, parcela_desejada=1000,
            parcela_limite=3000,
        )
        with patch("backend.main.list_grupos", return_value=[]), patch(
            "backend.main.analyze_client_consortium_viability", return_value=analysis
        ), patch("backend.main.save_motor360_audit", return_value={"metadata": {"audit_id": "AUD-COMPACT"}}):
            result = viabilidade_360_analisar(request, Response())

        self.assertEqual(result["items"], [{"grupo": "G1"}])
        self.assertIn("credit_items", result)
        self.assertIn("composition_items", result)


if __name__ == "__main__":
    unittest.main()
