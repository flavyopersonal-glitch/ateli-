from io import BytesIO
from urllib.parse import quote
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def gerar_link_whatsapp(telefone, nome_servico, valor_orcamento, status_orcamento):
    mensagem = (
        f"Olá! segue o orçamento para {nome_servico}.\n"
        f"Valor estimado: R$ {valor_orcamento:,.2f}\n"
        f"Status: {status_orcamento}"
    )
    return f"https://wa.me/{telefone}?text={quote(mensagem)}"


def gerar_pdf_orcamento(dados):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setTitle(f"Orçamento - {dados.get('nome_servico', 'Serviço')}")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, height - 60, "Orçamento Ateliê")

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, height - 90, f"Serviço: {dados.get('nome_servico', '-')}" )
    pdf.drawString(50, height - 115, f"Descrição: {dados.get('descricao_orcamento', 'Sem descrição adicional.')}" )
    pdf.drawString(50, height - 140, f"Horas estimadas: {dados.get('horas_estimadas', 0)}")
    pdf.drawString(50, height - 165, f"Custo de material: R$ {dados.get('custo_material', 0):,.2f}")
    pdf.drawString(50, height - 190, f"Valor da hora: R$ {dados.get('valor_hora', 0):,.2f}")
    pdf.drawString(50, height - 215, f"Margem desejada: {dados.get('margem_desejada', 0)}%")
    pdf.drawString(50, height - 240, f"Custo total: R$ {dados.get('custo_total', 0):,.2f}")
    pdf.drawString(50, height - 265, f"Valor do orçamento: R$ {dados.get('valor_orcamento', 0):,.2f}")
    pdf.drawString(50, height - 290, f"Lucro estimado: R$ {dados.get('lucro_estimado', 0):,.2f}")
    pdf.drawString(50, height - 315, f"Status: {dados.get('status_orcamento', 'Pendente')}")

    pdf.setFont("Helvetica-Oblique", 9)
    pdf.drawString(50, 70, "Gerado automaticamente pelo sistema de gestão do ateliê")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
