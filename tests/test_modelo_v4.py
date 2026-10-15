import unittest

from pydantic import ValidationError

from backend.models import (
    AdministradoraV4,
    AuditoriaV4,
    CenarioViabilidadeV4,
    ClienteV4,
    EstrategiaV4,
)
from backend.sheets_client import row_to_grupo_detalhe


class ModeloV4Test(unittest.TestCase):
    def test_entidades_v4_serializam(self):
        administradora = AdministradoraV4(
            administradora_id="ITAU",
            nome="Itau Consorcios",
            possui_template=True,
            template_padrao_id="ITAU_TEMPLATE_V1",
        )
        cliente = ClienteV4(
            cliente_id="CLI-1",
            nome="Cliente",
            renda_titular=10000,
            renda_conjuge=5000,
            renda_total=15000,
            fgts_total=50000,
        )
        cenario = CenarioViabilidadeV4(
            cenario_id="CEN-1",
            cliente_id=cliente.cliente_id,
            credito_desejado=500000,
            prazo_desejado=12,
            recurso_total_disponivel=150000,
        )
        estrategia = EstrategiaV4(
            estrategia_id="ESTR-1",
            cenario_id=cenario.cenario_id,
            grupo_id="128",
            nome="Lance Moderado",
            tipo="Moderada",
            score=92,
            selo="Excelente",
            recomendada=True,
            aprovada=True,
        )
        auditoria = AuditoriaV4(
            auditoria_id="AUD-1",
            usuario_id="USR-1",
            entidade="Cenario",
            entidade_id=cenario.cenario_id,
            acao="CREATE",
            origem="AUTO",
        )


    def test_grupo_v4_le_campos_novos_por_cabecalho(self):
        row = {
            "Administradora": "Itaú Consórcios",
            "Grupo": "128",
            "Tipo de Bem": "Imóvel",
            "Próxima Assembleia": "2026-06-13",
            "Limite de Adesão": "2026-06-03",
            "Vencimento da Primeira Parcela": "2026-06-05",
            "Percentual Parcela Reduzida": "30%",
            "Idade Máxima": "75",
            "Observações": "Grupo com parcela reduzida.",
        }

        result = row_to_grupo_detalhe(row)

        self.assertEqual(result["administradora_id"], "ITAU-CONSORCIOS")
        self.assertEqual(result["proxima_assembleia"], "2026-06-13")
        self.assertEqual(result["limite_adesao"], "2026-06-03")
        self.assertEqual(result["vencimento_primeira_parcela"], "2026-06-05")
        self.assertEqual(result["percentual_parcela_reduzida"], 0.3)
        self.assertEqual(result["idade_maxima"], 75)
        self.assertEqual(result["observacoes"], "Grupo com parcela reduzida.")


if __name__ == "__main__":
    unittest.main()
