"""Contract check for the real Motor 360 endpoint using a source-row fixture."""

import unittest
from unittest.mock import patch

from fastapi import Response

from backend.main import viabilidade_360_analisar
from backend.models import ViabilidadeRequest


class Motor360ApiContractTest(unittest.TestCase):
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
            result = viabilidade_360_analisar(request, response)

        self.assertEqual(result["audit_id"], "AUD-CONTRACT-FIXTURE")
        self.assertEqual(result["total_grupos_analisados"], 1)
        item = next(row for row in result["final_items"] if row["grupo"] == "1011")
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


if __name__ == "__main__":
    unittest.main()
