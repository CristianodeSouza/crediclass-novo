import json
import unittest
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "backend" / "data" / "assembly_calendar_2026.json"


class MapaAssembleiaDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    def test_importa_todas_as_secoes_da_planilha(self):
        self.assertEqual(len(self.data["schedules"]), 11)
        self.assertEqual(len(self.data["rules"]), 17)
        self.assertEqual(len(self.data["observations"]), 29)

    def test_datas_de_janeiro_apos_dezembro_sao_de_2027(self):
        cnp_auto = next(item for item in self.data["schedules"] if item["administrator"] == "CNP AUTO")
        december = next(month for month in cnp_auto["months"] if month["number"] == 12)
        events = {event["id"]: event for event in december["events"]}

        self.assertEqual(events["pagamento_lance"]["display"], "04/01/2027")
        self.assertEqual(events["segunda_chamada"]["display"], "07/01/2027")

    def test_texto_importado_esta_em_utf8(self):
        serialized = json.dumps(self.data, ensure_ascii=False)
        self.assertNotIn("�", serialized)
        self.assertIn("Adesão", serialized)
        self.assertIn("ITAÚ", serialized)


if __name__ == "__main__":
    unittest.main()
