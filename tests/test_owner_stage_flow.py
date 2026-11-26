"""Testes de integração da trava owner -> etapa em _sync_people_for_new_items.

O PipeRun é simulado: cada chamada externa registra seu nome em `calls`,
o que permite verificar a ordem real das gravações e o que foi bloqueado.
"""

import asyncio
import unittest
from unittest.mock import patch

import httpx

from backend import main

STAGE = 262860
OWNERS = [
    {"owner_id": 2602, "nome": "Bruna", "credito_minimo": None, "credito_maximo": 999999, "pipeline_ids": [4501]},
    {"owner_id": 2609, "nome": "Bruno", "credito_minimo": 1000000, "credito_maximo": None, "pipeline_ids": [4501]},
]


def make_item(owner_id=None, credit=900000):
    deal = {"id": "65626853", "person_id": "1565826", "pipeline_id": 4501}
    if owner_id:
        deal["owner_id"] = owner_id
    return {"oportunidade": deal, "encontrado": True, "dados": {"credito_desejado": credit, "campos_formulario": {}}}


class OwnerStageFlowTests(unittest.TestCase):
    def run_flow(self, item, *, distribution=True, owners=OWNERS, titular_error=None, assign_error=None, stage_error=None):
        calls = []

        async def titular(*_):
            calls.append("titular")
            if titular_error:
                raise titular_error
            return {"titular_atualizado": True}

        async def spouse(*_):
            calls.append("conjuge")
            return {"conjuge_atualizado": True}

        async def partners(*_):
            calls.append("parceiros")
            return {"empresa_parceira_status": "ok", "parceiros_status": "ok"}

        async def assign(deal_id, owner_id):
            calls.append(f"owner:{owner_id}")
            if assign_error:
                raise assign_error
            return {"owner_id": owner_id, "changed": True, "verified": True}

        async def stage(deal_id, stage_id):
            calls.append(f"etapa:{stage_id}")
            if stage_error:
                raise stage_error
            return {"changed": True, "to": stage_id}

        config = {"piperun_owner_distribution_enabled": distribution, "piperun_owners": owners}
        with patch.object(main, "update_opportunity_person", titular), \
             patch.object(main, "sync_spouse", spouse), \
             patch.object(main, "sync_partner_company", partners), \
             patch.object(main, "assign_piperun_deal_owner", assign), \
             patch.object(main, "move_piperun_deal_to_stage", stage), \
             patch.object(main, "get_configuracoes", return_value=config):
            result = asyncio.run(main._sync_people_for_new_items([item]))[0]
        return result, calls

    def test_novo_owner_e_atribuido_antes_da_etapa(self):
        result, calls = self.run_flow(make_item())
        self.assertEqual(calls, ["titular", "conjuge", "parceiros", "owner:2602", f"etapa:{STAGE}"])
        self.assertTrue(result["owner_atribuido"])
        self.assertTrue(result["etapa_atualizada"])

    def test_owner_existente_permite_etapa_sem_redistribuir(self):
        result, calls = self.run_flow(make_item(owner_id=2602))
        self.assertEqual(calls, ["titular", "conjuge", "parceiros", f"etapa:{STAGE}"])

    def test_distribuicao_desligada_sem_owner_nao_muda_etapa(self):
        result, calls = self.run_flow(make_item(), distribution=False)
        self.assertNotIn(f"etapa:{STAGE}", calls)
        self.assertFalse(any(call.startswith("owner:") for call in calls))
        self.assertNotIn("etapa_atualizada", result)

    def test_sem_owner_elegivel_nao_muda_etapa(self):
        result, calls = self.run_flow(make_item(credit=50_000_000), owners=[OWNERS[0]])
        self.assertEqual(calls, ["titular", "conjuge", "parceiros"])

    def test_mais_de_um_candidato_distribui_de_forma_deterministica(self):
        duplicated = [OWNERS[0], {**OWNERS[0], "owner_id": 2700}]
        result, calls = self.run_flow(make_item(), owners=duplicated)
        self.assertEqual(calls, ["titular", "conjuge", "parceiros", "owner:2602", f"etapa:{STAGE}"])
        self.assertEqual(result["oportunidade"]["owner_id"], 2602)

    def test_falha_na_atribuicao_bloqueia_etapa(self):
        result, calls = self.run_flow(make_item(), assign_error=RuntimeError("PipeRun recusou"))
        self.assertEqual(calls, ["titular", "conjuge", "parceiros", "owner:2602"])
        self.assertFalse(result["owner_atribuido"])
        self.assertIn("PipeRun recusou", result["owner_atribuicao_erro"])

    def test_timeout_na_atribuicao_bloqueia_etapa_sem_derrubar_lote(self):
        result, calls = self.run_flow(make_item(), assign_error=httpx.ReadTimeout("timeout"))
        self.assertNotIn(f"etapa:{STAGE}", calls)
        self.assertFalse(result["owner_atribuido"])

    def test_titular_inexistente_interrompe_antes_de_qualquer_gravacao(self):
        result, calls = self.run_flow(make_item(owner_id=2602), titular_error=RuntimeError("Titular não encontrado no PipeRun."))
        self.assertEqual(calls, ["titular"])
        self.assertFalse(result["titular_atualizado"])
        self.assertIn("Titular não encontrado", result["titular_erro"])

    def test_erro_na_etapa_e_registrado(self):
        result, calls = self.run_flow(make_item(owner_id=2602), stage_error=ValueError("fora do funil 4501"))
        self.assertFalse(result["etapa_atualizada"])
        self.assertIn("fora do funil", result["etapa_erro"])


if __name__ == "__main__":
    unittest.main()
