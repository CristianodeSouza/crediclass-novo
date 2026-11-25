import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import configuracoes
from backend import main


class PiperunAutomationConfigTests(unittest.TestCase):
    def setUp(self):
        self.original = configuracoes.get_configuracoes()
        self.temp = tempfile.TemporaryDirectory()
        self.settings = patch.object(configuracoes, "_settings", configuracoes.deepcopy(configuracoes.DEFAULT_CONFIG))
        self.settings.start()
        self.files = patch.object(configuracoes, "RUNTIME_DIR", Path(self.temp.name)), patch.object(configuracoes, "CONFIG_FILE", Path(self.temp.name) / "configuracoes.json")
        for item in self.files:
            item.start()

    def tearDown(self):
        configuracoes._settings.clear()
        configuracoes._settings.update(self.original)
        for item in reversed(self.files):
            item.stop()
        self.settings.stop()
        self.temp.cleanup()

    def test_salvar_owners_sem_fidelidade_preserva_fidelidade_existente(self):
        configuracoes._settings["piperun_owners"][0]["parceiros_fidelidade"] = [{"chave": "12345678000199"}]
        configuracoes.update_configuracoes({"piperun_owners": [{"owner_id": 2602, "nome": "Bruna", "pipeline_ids": [4501]}]})
        self.assertEqual(configuracoes.get_configuracoes()["piperun_owners"][0]["parceiros_fidelidade"][0]["chave"], "12345678000199")

    def test_schedule_normaliza_dias_horarios_e_fuso(self):
        configuracoes.update_configuracoes({"piperun_scan_schedule": {"days": ["monday", "invalid"], "times": ["08:00", "25:00"], "timezone": "UTC", "enabled": True}})
        schedule = configuracoes.get_configuracoes()["piperun_scan_schedule"]
        self.assertEqual(schedule, {"days": ["monday"], "times": ["08:00"], "timezone": "America/Sao_Paulo", "enabled": True})

    def test_flag_desligada_nao_distribui_owner(self):
        configuracoes.update_configuracoes({"piperun_owner_distribution_enabled": False})
        self.assertFalse(configuracoes.get_configuracoes()["piperun_owner_distribution_enabled"])


if __name__ == "__main__":
    unittest.main()
