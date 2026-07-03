import sys
import unittest
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from orcamento_utils import gerar_link_whatsapp, gerar_pdf_orcamento


class OrcamentoUtilsTest(unittest.TestCase):
    def test_gerar_pdf_orcamento_retorna_bytes_pdf(self):
        dados = {
            "nome_servico": "Teste",
            "descricao_orcamento": "Descrição teste",
            "horas_estimadas": 3,
            "custo_material": 20,
            "valor_hora": 50,
            "margem_desejada": 25,
            "custo_total": 170,
            "valor_orcamento": 226.67,
            "lucro_estimado": 56.67,
            "status_orcamento": "Pendente",
            "telefone_whatsapp": "5511999999999",
        }

        pdf_bytes = gerar_pdf_orcamento(dados)

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_gerar_link_whatsapp_contem_numero_e_texto(self):
        link = gerar_link_whatsapp("5511999999999", "Teste", 226.67, "Pendente")

        self.assertIn("wa.me", link)
        self.assertIn("5511999999999", link)
        self.assertIn("Teste", link)


if __name__ == "__main__":
    unittest.main()
