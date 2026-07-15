"""Ateliê Cristo Rei — gestão de pedidos, orçamentos e finanças.

Aplicação independente, com banco SQLite criado automaticamente em data/atelie.db.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from io import BytesIO
from math import ceil
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


APP_NAME = "Ateliê Cristo Rei"
DB_PATH = Path("data") / "atelie.db"
LOGO_PATH = Path(__file__).with_name("logo.jpeg")
CAPACIDADE_DIARIA_HORAS = 8
DIAS_SECAGEM_FABRICACAO = 3
ORDER_STATUS = ["Novo pedido", "Em produção", "Aguardando aprovação", "Pronto para entrega", "Entregue", "Cancelado"]

st.set_page_config(page_title=APP_NAME, page_icon="✦", layout="wide", initial_sidebar_state="expanded")


def brl(value: float | int | None) -> str:
    value = float(value or 0)
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def iso_to_br(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return value


def workdays_for_hours(hours: float) -> int:
    """Converte horas de produção em dias úteis de 8 horas."""
    return ceil(max(hours, 0) / CAPACIDADE_DIARIA_HORAS)


def estimated_completion(start: date, hours: float, requires_fabrication: bool = False) -> date:
    """Calcula a conclusão com dias úteis e, se necessário, secagem."""
    remaining_days = workdays_for_hours(hours)
    current = start

    while current.weekday() >= 5:
        current += timedelta(days=1)

    while remaining_days:
        if current.weekday() < 5:
            remaining_days -= 1
            if remaining_days == 0:
                return current + timedelta(days=DIAS_SECAGEM_FABRICACAO if requires_fabrication else 0)
        current += timedelta(days=1)

    return current + timedelta(days=DIAS_SECAGEM_FABRICACAO if requires_fabrication else 0)


def deadline_priority(deadline: str | None) -> str:
    if not deadline:
        return "Sem prazo"
    remaining = (date.fromisoformat(deadline) - date.today()).days
    if remaining < 0:
        return f"Vencido há {abs(remaining)} dia(s)"
    if remaining == 0:
        return "Entrega hoje"
    if remaining == 1:
        return "Entrega amanhã"
    return f"Entrega em {remaining} dias"


@st.cache_resource
def database() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            telefone TEXT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            tecnica TEXT,
            prazo TEXT,
            horas_estimadas REAL NOT NULL DEFAULT 0,
            exige_fabricacao INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'Novo pedido',
            valor_combinado REAL NOT NULL DEFAULT 0,
            custo_estimado REAL NOT NULL DEFAULT 0,
            observacoes TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orcamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT NOT NULL UNIQUE,
            cliente TEXT NOT NULL,
            telefone TEXT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            validade TEXT,
            prazo_entrega TEXT,
            tecnica TEXT,
            horas_estimadas REAL NOT NULL DEFAULT 0,
            exige_fabricacao INTEGER NOT NULL DEFAULT 1,
            valor REAL NOT NULL DEFAULT 0,
            prazo_producao TEXT,
            condicoes TEXT,
            status TEXT NOT NULL DEFAULT 'Pendente',
            pedido_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL CHECK(tipo IN ('Entrada', 'Saída')),
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            data TEXT NOT NULL,
            pedido_id INTEGER,
            categoria TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        );
        """
    )
    columns = {column["name"] for column in conn.execute("PRAGMA table_info(pedidos)")}
    if "horas_estimadas" not in columns:
        conn.execute("ALTER TABLE pedidos ADD COLUMN horas_estimadas REAL NOT NULL DEFAULT 0")
    if "exige_fabricacao" not in columns:
        conn.execute("ALTER TABLE pedidos ADD COLUMN exige_fabricacao INTEGER NOT NULL DEFAULT 1")
    quote_columns = {column["name"] for column in conn.execute("PRAGMA table_info(orcamentos)")}
    quote_migrations = {
        "prazo_entrega": "TEXT",
        "tecnica": "TEXT",
        "horas_estimadas": "REAL NOT NULL DEFAULT 0",
        "exige_fabricacao": "INTEGER NOT NULL DEFAULT 1",
        "pedido_id": "INTEGER",
    }
    for name, definition in quote_migrations.items():
        if name not in quote_columns:
            conn.execute(f"ALTER TABLE orcamentos ADD COLUMN {name} {definition}")
    conn.execute("DELETE FROM orcamentos WHERE status != 'Aprovado' AND date(criado_em) <= date('now', '-30 days')")
    conn.commit()
    return conn


def execute(sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
    cur = database().execute(sql, params)
    database().commit()
    return cur


def reload_page() -> None:
    """Atualiza a tela em versões antigas e novas do Streamlit."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [dict(row) for row in database().execute(sql, params).fetchall()]


def scalar(sql: str, params: tuple[Any, ...] = ()) -> Any:
    result = database().execute(sql, params).fetchone()
    return result[0] if result else 0


def inject_style() -> None:
    st.markdown(
        """
        <style>
          :root { --vinho: #560D1B; --vinho-escuro: #310811; --ouro: #B98728; --creme: #FBF8F1; --texto: #2C2020; }
          .stApp { background: var(--creme); color: var(--texto); }
          [data-testid="stSidebar"] { background: linear-gradient(180deg, #4A0A18 0%, #26050C 100%); border-right: 1px solid rgba(185,135,40,.45); }
          [data-testid="stSidebar"] * { color: #FFF9EF !important; }
          [data-testid="stSidebar"] .stRadio label { border-radius: 9px; padding: .45rem .55rem; margin: .12rem 0; font-weight: 600; }
          [data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,.10); }
          [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #E9D5AC !important; }
          .block-container { max-width: 1220px; padding-top: 3.15rem; padding-bottom: 3.4rem; }
          h1, h2, h3 { font-family: Georgia, 'Times New Roman', serif; color: var(--vinho-escuro); letter-spacing: -.015em; }
          h1 { font-size: 2.55rem !important; margin-bottom: 1.4rem !important; }
          h2 { font-size: 1.65rem !important; margin-top: .6rem !important; }
          h3 { font-size: 1.16rem !important; }
          .brand-top { border-bottom: 1px solid #E9DCC6; padding-bottom: .85rem; margin-bottom: 1.7rem; }
          .brand-kicker { color: #9A6D1B; font-size: .70rem; line-height: 1.45; letter-spacing: .18em; text-transform: uppercase; font-weight: 800; margin: 0 0 .12rem; }
          .brand-name { color: var(--vinho); font-family: Georgia, serif; font-size: 1.42rem; font-weight: 700; margin: 0; }
          .brand-tagline { color: #76645A; font-size: .84rem; margin: .15rem 0 0; }
          .eyebrow { color: #9A6D1B; text-transform: uppercase; font-weight: 800; letter-spacing: .15em; font-size: .70rem; margin-bottom: .25rem; }
          .hero { background: linear-gradient(112deg, #4A0A18 0%, #74162A 65%, #8E6520 170%); color: #FFF9EF; border: 1px solid rgba(185,135,40,.55); border-radius: 16px; padding: 1.9rem 2.1rem; margin: .4rem 0 1.5rem; box-shadow: 0 13px 30px rgba(72, 10, 24, .14); }
          .hero h2 { color: #FFF9EF; margin: 0 0 .4rem !important; }
          .hero p { color: #F2E4C9; margin: 0; max-width: 680px; line-height: 1.6; }
          div[data-testid="stMetric"] { background: #FFFDF8; border: 1px solid #E9DCC6; border-top: 3px solid #B98728; border-radius: 11px; padding: .9rem 1rem; box-shadow: 0 5px 14px rgba(58, 32, 21, .04); }
          [data-testid="stMetricLabel"] { color: #78635A !important; font-size: .83rem; }
          [data-testid="stMetricValue"] { color: var(--vinho) !important; font-family: Georgia, serif; }
          .stButton > button, .stDownloadButton > button { background: var(--vinho); color: #FFF9EF; border: 1px solid var(--vinho); border-radius: 7px; font-weight: 700; min-height: 2.7rem; transition: all .18s ease; }
          .stButton > button:hover, .stDownloadButton > button:hover { background: #75172A; border-color: #75172A; color: white; transform: translateY(-1px); box-shadow: 0 5px 14px rgba(86,13,27,.16); }
          .card { background: #FFFDF8; border: 1px solid #E9DCC6; border-radius: 11px; padding: 1.25rem; line-height: 1.65; }
          .muted { color: #76645A; }
          .stDataFrame { border: 1px solid #E9DCC6; border-radius: 10px; overflow: hidden; }
          div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, .stTextArea textarea { background: #FFFDF9 !important; border-color: #D9C8B1 !important; border-radius: 7px !important; }
          div[data-baseweb="input"] > div:focus-within, div[data-baseweb="select"] > div:focus-within, .stTextArea textarea:focus { border-color: #9A6D1B !important; box-shadow: 0 0 0 1px #9A6D1B !important; }
          label, [data-testid="stWidgetLabel"] p { color: #4E3933 !important; font-size: .88rem !important; font-weight: 650 !important; }
          [data-testid="stForm"] { background: #FFFDF8; border: 1px solid #E9DCC6; border-radius: 12px; padding: 1.15rem 1.2rem .8rem; }
          hr { border-color: #E9DCC6 !important; }
          @media (max-width: 700px) { .block-container { padding: 2.6rem .8rem 2rem; } h1 { font-size: 2rem !important; } .hero { padding: 1.35rem; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar() -> str:
    with st.sidebar:
        st.image("logo.jpeg", width=126)
        st.markdown("## Ateliê Cristo Rei")
        st.caption("Arte sacra feita com propósito")
        st.divider()
        page = st.radio("Navegação", ["Visão geral", "Pedidos", "Orçamentos", "Financeiro"], label_visibility="collapsed")
        st.divider()
        st.caption("Gestão de pedidos, orçamentos e finanças.")
    return page


def render_brand_header(page: str) -> None:
    icon, copy = st.columns([1, 13], gap="small")
    with icon:
        st.image("logo.jpeg", width=50)
    with copy:
        st.markdown(
            f'<div class="brand-top"><p class="brand-kicker">Ateliê Cristo Rei · {page}</p><p class="brand-name">Gestão do ateliê</p><p class="brand-tagline">Pedidos organizados, clientes bem atendidos.</p></div>',
            unsafe_allow_html=True,
        )


def order_options() -> dict[str, int | None]:
    options = {"Sem vínculo": None}
    for order in rows("SELECT id, cliente, titulo FROM pedidos WHERE status != 'Cancelado' ORDER BY criado_em DESC"):
        options[f"#{order['id']} · {order['cliente']} — {order['titulo']}"] = order["id"]
    return options


def render_dashboard() -> None:
    st.markdown('<p class="eyebrow">Visão geral</p><h1>Seu ateliê, sob controle.</h1>', unsafe_allow_html=True)
    today = date.today().isoformat()
    active = scalar("SELECT COUNT(*) FROM pedidos WHERE status NOT IN ('Entregue', 'Cancelado')")
    due = scalar("SELECT COUNT(*) FROM pedidos WHERE prazo IS NOT NULL AND prazo >= ? AND status NOT IN ('Entregue', 'Cancelado')", (today,))
    income = scalar("SELECT COALESCE(SUM(valor), 0) FROM transacoes WHERE tipo = 'Entrada'")
    expense = scalar("SELECT COALESCE(SUM(valor), 0) FROM transacoes WHERE tipo = 'Saída'")
    st.markdown('<div class="hero"><h2>Bom trabalho!</h2><p>Acompanhe o andamento das peças, mantenha o cliente informado e enxergue o resultado do seu trabalho.</p></div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pedidos em aberto", active)
    c2.metric("Prazos programados", due)
    c3.metric("Entradas", brl(income))
    c4.metric("Saldo", brl(income - expense))

    st.subheader("Pedidos que precisam de atenção")
    attention = rows(
        """SELECT id, cliente, titulo, prazo, horas_estimadas, status FROM pedidos
           WHERE status NOT IN ('Entregue', 'Cancelado')
           ORDER BY CASE
                WHEN prazo IS NULL THEN 2
                WHEN prazo < date('now') THEN 0
                ELSE 1
            END, prazo ASC LIMIT 8"""
    )
    if attention:
        frame = pd.DataFrame(attention).rename(columns={"id": "Nº", "cliente": "Cliente", "titulo": "Peça", "prazo": "Prazo", "horas_estimadas": "Horas", "status": "Etapa"})
        frame["Prioridade"] = frame["Prazo"].map(deadline_priority)
        frame["Prazo"] = frame["Prazo"].map(iso_to_br)
        frame["Horas"] = frame["Horas"].map(lambda hours: f"{float(hours or 0):g}h")
        frame = frame[["Prioridade", "Prazo", "Nº", "Cliente", "Peça", "Horas", "Etapa"]]
        st.dataframe(frame, use_container_width=True, hide_index=True)
    else:
        st.info("Ainda não há pedidos. Comece adicionando o primeiro pedido na aba Pedidos.")


def render_orders() -> None:
    st.markdown('<p class="eyebrow">Pedidos</p><h1>Da encomenda à entrega.</h1>', unsafe_allow_html=True)
    left, right = st.columns([1.05, 1], gap="large")
    with left:
        st.subheader("Novo pedido")
        with st.form("novo_pedido", clear_on_submit=True):
            cliente = st.text_input("Nome do cliente *")
            telefone = st.text_input("WhatsApp")
            titulo = st.text_input("Peça ou encomenda *", placeholder="Ex.: Imagem de Nossa Senhora Aparecida")
            descricao = st.text_area("Detalhes da peça", placeholder="Tamanho, cores, acabamento e referências")
            a, b = st.columns(2)
            tecnica = a.text_input("Técnica / acabamento", placeholder="Pintura artesanal")
            fabrication = b.selectbox("Exige fabricação?", ["Sim", "Não"], help="Informe se a peça precisa ser fabricada antes da pintura ou acabamento.")
            c, d = st.columns(2)
            horas = c.number_input("Horas de produção", min_value=0.0, step=0.5, help="Estimativa de horas necessárias para produzir a peça.")
            prazo = d.date_input("Prazo de entrega", value=None, format="DD/MM/YYYY")
            if horas or fabrication == "Sim":
                days_needed = workdays_for_hours(horas)
                drying_note = f" + {DIAS_SECAGEM_FABRICACAO} dias corridos de secagem" if fabrication == "Sim" else ""
                finish_date = estimated_completion(date.today(), horas, fabrication == "Sim")
                st.caption(f"Estimativa: {days_needed} dia(s) útil(eis) de trabalho{drying_note} · conclusão prevista em {finish_date.strftime('%d/%m/%Y')}.")
                if prazo and finish_date > prazo:
                    st.warning("A estimativa de produção ultrapassa o prazo informado.")
            d, e = st.columns(2)
            valor = d.number_input("Valor combinado (R$)", min_value=0.0, step=10.0)
            custo = e.number_input("Custo estimado (R$)", min_value=0.0, step=10.0)
            obs = st.text_area("Observações internas")
            saved = st.form_submit_button("Cadastrar pedido", use_container_width=True)
        if saved:
            if not cliente.strip() or not titulo.strip():
                st.error("Informe o nome do cliente e a peça.")
            else:
                execute(
                    "INSERT INTO pedidos (cliente, telefone, titulo, descricao, tecnica, prazo, horas_estimadas, exige_fabricacao, valor_combinado, custo_estimado, observacoes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (cliente.strip(), telefone.strip(), titulo.strip(), descricao.strip(), tecnica.strip(), prazo.isoformat() if prazo else None, horas, fabrication == "Sim", valor, custo, obs.strip()),
                )
                st.success("Pedido cadastrado.")
                reload_page()
    with right:
        st.subheader("Acompanhar pedido")
        pending = rows("SELECT * FROM pedidos ORDER BY criado_em DESC")
        if not pending:
            st.caption("Os pedidos cadastrados aparecerão aqui.")
            return
        choices = {f"#{p['id']} · {p['cliente']} — {p['titulo']}": p for p in pending}
        selected = st.selectbox("Selecione um pedido", list(choices))
        item = choices[selected]
        hours = float(item.get("horas_estimadas") or 0)
        fabrication_status = "Sim" if item.get("exige_fabricacao", 1) else "Não"
        drying_note = f" + {DIAS_SECAGEM_FABRICACAO} dias de secagem" if fabrication_status == "Sim" else ""
        production_time = f"{hours:g}h previstas · {workdays_for_hours(hours)} dia(s) útil(eis){drying_note}" if hours else f"{DIAS_SECAGEM_FABRICACAO} dias de secagem" if fabrication_status == "Sim" else "Tempo de produção não informado"
        st.markdown(f'<div class="card"><b>{item["titulo"]}</b><br><span class="muted">{item["cliente"]} · Entrega: {iso_to_br(item["prazo"])}<br>Exige fabricação: {fabrication_status}<br>Produção: {production_time}<br>Valor: {brl(item["valor_combinado"])} · Custo previsto: {brl(item["custo_estimado"])}<br><br>{item["descricao"] or "Sem detalhes adicionais."}</span></div>', unsafe_allow_html=True)
        with st.form(f"atualiza_pedido_{item['id']}"):
            status = st.selectbox("Etapa atual", ORDER_STATUS, index=ORDER_STATUS.index(item["status"]))
            updated_hours = st.number_input("Horas de produção", min_value=0.0, step=0.5, value=hours)
            updated_fabrication = st.selectbox("Exige fabricação?", ["Sim", "Não"], index=0 if fabrication_status == "Sim" else 1)
            updated_value = st.number_input("Valor combinado (R$)", min_value=0.0, step=10.0, value=float(item["valor_combinado"] or 0))
            updated_notes = st.text_area("Observações", value=item["observacoes"] or "")
            update = st.form_submit_button("Salvar atualização", use_container_width=True)
        if update:
            execute("UPDATE pedidos SET status = ?, horas_estimadas = ?, exige_fabricacao = ?, valor_combinado = ?, observacoes = ?, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?", (status, updated_hours, updated_fabrication == "Sim", updated_value, updated_notes, item["id"]))
            st.success("Pedido atualizado.")
            reload_page()


def quote_pdf_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#B98728"))
    canvas.setLineWidth(0.7)
    canvas.line(doc.leftMargin, 1.55 * cm, A4[0] - doc.rightMargin, 1.55 * cm)
    canvas.setFillColor(colors.HexColor("#765D42"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(doc.leftMargin, 1.05 * cm, "ATELIÊ CRISTO REI  •  Arte sacra feita com propósito")
    canvas.drawRightString(A4[0] - doc.rightMargin, 1.05 * cm, f"Proposta {doc.page}")
    canvas.restoreState()


def quote_pdf(quote: dict[str, Any]) -> bytes:
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=1.55*cm, bottomMargin=2.25*cm)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("proposal_body", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.3, leading=16, textColor=colors.HexColor("#352A25"))
    label = ParagraphStyle("proposal_label", parent=body, fontName="Helvetica-Bold", fontSize=8.3, leading=12, textColor=colors.HexColor("#8C651D"), spaceAfter=2)
    value = ParagraphStyle("proposal_value", parent=body, fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=colors.HexColor("#4A0A18"))
    section = ParagraphStyle("proposal_section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=colors.HexColor("#560D1B"), spaceAfter=6)
    company = ParagraphStyle("proposal_company", parent=body, fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=colors.HexColor("#560D1B"))
    slogan = ParagraphStyle("proposal_slogan", parent=body, fontSize=8.5, leading=12, textColor=colors.HexColor("#8C651D"))
    doc_title = ParagraphStyle("proposal_title", parent=body, fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=colors.HexColor("#560D1B"), alignment=TA_RIGHT)
    doc_meta = ParagraphStyle("proposal_meta", parent=body, fontSize=8.5, leading=12, textColor=colors.HexColor("#765D42"), alignment=TA_RIGHT)

    logo = Image(str(LOGO_PATH), width=1.9*cm, height=1.9*cm)
    brand = Table([[logo, [Paragraph("ATELIÊ CRISTO REI", company), Paragraph("Arte sacra feita com propósito", slogan)], [Paragraph("ORÇAMENTO", doc_title), Paragraph(f"Nº {escape(str(quote['numero']))}<br/>Emitido em {datetime.now().strftime('%d/%m/%Y')}", doc_meta)]]], colWidths=[2.2*cm, 8.0*cm, 4.6*cm])
    brand.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LINEBELOW", (0, 0), (-1, -1), 1.1, colors.HexColor("#B98728"))]))

    client = Table([[Paragraph("CLIENTE", label), Paragraph("VALIDADE", label)], [Paragraph(escape(str(quote["cliente"])), value), Paragraph(iso_to_br(quote["validade"]), value)]], colWidths=[10.2*cm, 4.6*cm])
    client.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F1E5")), ("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#E4D1A7")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]))

    table = Table([["INVESTIMENTO", brl(quote["valor"])]], colWidths=[10.5*cm, 4.3*cm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#560D1B")), ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#FFF9EF")), ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 12), ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 13), ("BOTTOMPADDING", (0, 0), (-1, -1), 13), ("LEFTPADDING", (0, 0), (-1, -1), 13), ("RIGHTPADDING", (0, 0), (-1, -1), 13), ("LINEABOVE", (0, 0), (-1, -1), 2, colors.HexColor("#B98728"))]))

    title = escape(str(quote["titulo"]))
    description = escape(str(quote["descricao"] or "Conforme detalhes combinados com o cliente.")).replace("\n", "<br/>")
    timing = escape(str(quote["prazo_producao"] or "A combinar"))
    technique = escape(str(quote.get("tecnica") or "A combinar"))
    fabrication = "Sim" if quote.get("exige_fabricacao", 1) else "Não"
    conditions = escape(str(quote["condicoes"] or "Condições de pagamento a combinar.")).replace("\n", "<br/>")
    story = [brand, Spacer(1, .65*cm), client, Spacer(1, .75*cm), Paragraph("DETALHES DA ENCOMENDA", section), Paragraph(title, value), Spacer(1, .18*cm), Paragraph(description, body), Spacer(1, .45*cm), Paragraph(f"<b>Técnica / acabamento:</b> {technique}<br/><b>Exige fabricação:</b> {fabrication}", body), Spacer(1, .7*cm), table, Spacer(1, .7*cm), Paragraph("PRAZO DE PRODUÇÃO", label), Paragraph(timing, body), Spacer(1, .42*cm), Paragraph("CONDIÇÕES", label), Paragraph(conditions, body), Spacer(1, 1.0*cm), Paragraph("Agradecemos a confiança em nosso trabalho. Será uma alegria transformar sua encomenda em uma peça especial.", ParagraphStyle("closing", parent=body, alignment=TA_CENTER, textColor=colors.HexColor("#765D42"), fontSize=9.3, leading=14))]
    doc.title = f"Orçamento {quote['numero']} — Ateliê Cristo Rei"
    doc.build(story, onFirstPage=quote_pdf_footer, onLaterPages=quote_pdf_footer)
    return output.getvalue()


def render_quotes() -> None:
    st.markdown('<p class="eyebrow">Orçamentos</p><h1>Uma proposta que valoriza seu trabalho.</h1>', unsafe_allow_html=True)
    st.caption("Orçamentos pendentes ou não aprovados são excluídos automaticamente após 30 dias corridos.")
    left, right = st.columns([1.05, 1], gap="large")
    with left:
        st.subheader("Criar orçamento")
        with st.form("novo_orcamento", clear_on_submit=True):
            cliente = st.text_input("Nome do cliente *", key="q_cliente")
            telefone = st.text_input("WhatsApp", key="q_fone")
            titulo = st.text_input("Peça ou serviço *", key="q_titulo")
            descricao = st.text_area("Descrição", key="q_desc")
            a, b = st.columns(2)
            tecnica = a.text_input("Técnica / acabamento", placeholder="Pintura artesanal", key="q_tecnica")
            fabrication = b.selectbox("Exige fabricação?", ["Sim", "Não"], key="q_fabricacao")
            c, d = st.columns(2)
            horas = c.number_input("Horas de produção", min_value=0.0, step=0.5, key="q_horas")
            prazo_entrega = d.date_input("Prazo de entrega", value=None, format="DD/MM/YYYY", key="q_prazo_entrega")
            e, f = st.columns(2)
            valor = e.number_input("Valor da proposta (R$)", min_value=0.0, step=10.0, key="q_valor")
            validade = f.date_input("Válido até", value=date.today(), format="DD/MM/YYYY")
            conditions = st.text_area("Condições", value="50% de sinal para início da produção e 50% na entrega.")
            create = st.form_submit_button("Salvar orçamento", use_container_width=True)
        if create:
            if not cliente.strip() or not titulo.strip():
                st.error("Informe o cliente e a peça.")
            else:
                number = f"{date.today():%Y}-{scalar('SELECT COALESCE(MAX(id), 0) FROM orcamentos') + 1:03d}"
                days_needed = workdays_for_hours(horas)
                drying = f" + {DIAS_SECAGEM_FABRICACAO} dias de secagem" if fabrication == "Sim" else ""
                production_time = f"{days_needed} dia(s) útil(eis){drying}" if horas or fabrication == "Sim" else "A combinar"
                execute(
                    "INSERT INTO orcamentos (numero, cliente, telefone, titulo, descricao, validade, prazo_entrega, tecnica, horas_estimadas, exige_fabricacao, valor, prazo_producao, condicoes, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pendente')",
                    (number, cliente.strip(), telefone.strip(), titulo.strip(), descricao.strip(), validade.isoformat(), prazo_entrega.isoformat() if prazo_entrega else None, tecnica.strip(), horas, fabrication == "Sim", valor, production_time, conditions.strip()),
                )
                st.success(f"Orçamento {number} salvo.")
                reload_page()
    with right:
        st.subheader("Gerar PDF e aprovar")
        quotes = rows("SELECT * FROM orcamentos ORDER BY criado_em DESC")
        if not quotes:
            st.caption("Salve um orçamento para gerar o documento em PDF.")
            return
        selected = st.selectbox("Orçamento", [f"{q['numero']} · {q['cliente']} — {q['titulo']}" for q in quotes])
        quote = quotes[[f"{q['numero']} · {q['cliente']} — {q['titulo']}" for q in quotes].index(selected)]
        fabrication_status = "Sim" if quote.get("exige_fabricacao", 1) else "Não"
        st.markdown(f'<div class="card"><b>{quote["numero"]} · {quote["status"]}</b><br><span class="muted">{quote["cliente"]}<br>{quote["titulo"]}<br>Entrega: {iso_to_br(quote.get("prazo_entrega"))} · {float(quote.get("horas_estimadas") or 0):g}h · Fabricação: {fabrication_status}<br>Valor: {brl(quote["valor"])} · Válido até {iso_to_br(quote["validade"])}</span></div>', unsafe_allow_html=True)
        st.download_button("Baixar orçamento em PDF", data=quote_pdf(quote), file_name=f"orcamento-{quote['numero']}.pdf", mime="application/pdf", use_container_width=True)

        with st.expander("Editar orçamento ou registrar aprovação"):
            with st.form(f"editar_orcamento_{quote['id']}"):
                edit_client = st.text_input("Nome do cliente *", value=quote["cliente"])
                edit_phone = st.text_input("WhatsApp", value=quote["telefone"] or "")
                edit_title = st.text_input("Peça ou serviço *", value=quote["titulo"])
                edit_description = st.text_area("Descrição", value=quote["descricao"] or "")
                a, b = st.columns(2)
                edit_technique = a.text_input("Técnica / acabamento", value=quote.get("tecnica") or "")
                edit_fabrication = b.selectbox("Exige fabricação?", ["Sim", "Não"], index=0 if quote.get("exige_fabricacao", 1) else 1)
                c, d = st.columns(2)
                edit_hours = c.number_input("Horas de produção", min_value=0.0, step=0.5, value=float(quote.get("horas_estimadas") or 0))
                edit_due = d.date_input("Prazo de entrega", value=date.fromisoformat(quote["prazo_entrega"]) if quote.get("prazo_entrega") else None, format="DD/MM/YYYY")
                e, f = st.columns(2)
                edit_value = e.number_input("Valor da proposta (R$)", min_value=0.0, step=10.0, value=float(quote["valor"] or 0))
                edit_validity = f.date_input("Válido até", value=date.fromisoformat(quote["validade"]) if quote.get("validade") else date.today(), format="DD/MM/YYYY")
                statuses = ["Pendente", "Aprovado", "Não aprovado"]
                edit_status = st.selectbox("Aprovação", statuses, index=statuses.index(quote["status"]) if quote["status"] in statuses else 0)
                edit_conditions = st.text_area("Condições", value=quote["condicoes"] or "")
                save_quote = st.form_submit_button("Salvar alterações", use_container_width=True)
            if save_quote:
                if not edit_client.strip() or not edit_title.strip():
                    st.error("Informe o cliente e a peça.")
                else:
                    days_needed = workdays_for_hours(edit_hours)
                    drying = f" + {DIAS_SECAGEM_FABRICACAO} dias de secagem" if edit_fabrication == "Sim" else ""
                    production_time = f"{days_needed} dia(s) útil(eis){drying}" if edit_hours or edit_fabrication == "Sim" else "A combinar"
                    execute(
                        "UPDATE orcamentos SET cliente = ?, telefone = ?, titulo = ?, descricao = ?, validade = ?, prazo_entrega = ?, tecnica = ?, horas_estimadas = ?, exige_fabricacao = ?, valor = ?, prazo_producao = ?, condicoes = ?, status = ? WHERE id = ?",
                        (edit_client.strip(), edit_phone.strip(), edit_title.strip(), edit_description.strip(), edit_validity.isoformat(), edit_due.isoformat() if edit_due else None, edit_technique.strip(), edit_hours, edit_fabrication == "Sim", edit_value, production_time, edit_conditions.strip(), edit_status, quote["id"]),
                    )
                    st.success("Orçamento atualizado.")
                    reload_page()

            if quote.get("pedido_id"):
                st.success(f"Este orçamento já foi enviado para o pedido #{quote['pedido_id']}.")
            elif st.button("Enviar orçamento aprovado para Pedidos", use_container_width=True):
                if quote["status"] != "Aprovado":
                    st.error("Altere o campo Aprovação para 'Aprovado' e salve antes de enviar para Pedidos.")
                else:
                    result = execute(
                        "INSERT INTO pedidos (cliente, telefone, titulo, descricao, tecnica, prazo, horas_estimadas, exige_fabricacao, valor_combinado, observacoes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (quote["cliente"], quote["telefone"], quote["titulo"], quote["descricao"], quote.get("tecnica") or "", quote.get("prazo_entrega"), quote.get("horas_estimadas") or 0, quote.get("exige_fabricacao", 1), quote["valor"], f"Pedido criado a partir do orçamento {quote['numero']}"),
                    )
                    execute("UPDATE orcamentos SET pedido_id = ? WHERE id = ?", (result.lastrowid, quote["id"]))
                    st.success("Pedido criado a partir do orçamento aprovado.")
                    reload_page()


def render_finance() -> None:
    st.markdown('<p class="eyebrow">Financeiro</p><h1>Veja o resultado do seu trabalho.</h1>', unsafe_allow_html=True)
    income = float(scalar("SELECT COALESCE(SUM(valor), 0) FROM transacoes WHERE tipo = 'Entrada'"))
    expenses = float(scalar("SELECT COALESCE(SUM(valor), 0) FROM transacoes WHERE tipo = 'Saída'"))
    a, b, c = st.columns(3)
    a.metric("Entradas registradas", brl(income))
    b.metric("Saídas registradas", brl(expenses))
    c.metric("Saldo atual", brl(income-expenses))
    left, right = st.columns([.9, 1.1], gap="large")
    with left:
        st.subheader("Novo lançamento")
        with st.form("nova_transacao", clear_on_submit=True):
            kind = st.radio("Tipo", ["Entrada", "Saída"], horizontal=True)
            description = st.text_input("Descrição *", placeholder="Ex.: Sinal da imagem de São José")
            value = st.number_input("Valor (R$)", min_value=0.01, step=10.0)
            when = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")
            category = st.text_input("Categoria", placeholder="Venda, material, embalagem...")
            options = order_options()
            order_label = st.selectbox("Vincular a um pedido", list(options))
            save = st.form_submit_button("Registrar lançamento", use_container_width=True)
        if save:
            if not description.strip():
                st.error("Informe uma descrição.")
            else:
                execute("INSERT INTO transacoes (tipo, descricao, valor, data, pedido_id, categoria) VALUES (?, ?, ?, ?, ?, ?)", (kind, description.strip(), value, when.isoformat(), options[order_label], category.strip()))
                st.success("Lançamento registrado.")
                reload_page()
    with right:
        st.subheader("Últimos lançamentos")
        transactions = rows("SELECT t.*, p.cliente FROM transacoes t LEFT JOIN pedidos p ON t.pedido_id = p.id ORDER BY t.data DESC, t.id DESC LIMIT 20")
        if transactions:
            frame = pd.DataFrame(transactions)[["data", "tipo", "descricao", "categoria", "cliente", "valor"]].rename(columns={"data": "Data", "tipo": "Tipo", "descricao": "Descrição", "categoria": "Categoria", "cliente": "Pedido / cliente", "valor": "Valor"})
            frame["Data"] = frame["Data"].map(iso_to_br)
            frame["Valor"] = frame["Valor"].map(brl)
            st.dataframe(frame, use_container_width=True, hide_index=True)

            with st.expander("Editar ou excluir lançamento"):
                transaction_choices = {
                    f"#{transaction['id']} · {iso_to_br(transaction['data'])} · {transaction['descricao']} · {brl(transaction['valor'])}": transaction
                    for transaction in rows("SELECT * FROM transacoes ORDER BY data DESC, id DESC")
                }
                selected_label = st.selectbox("Lançamento", list(transaction_choices), key="transacao_para_editar")
                selected_transaction = transaction_choices[selected_label]
                options = order_options()
                current_order_index = list(options.values()).index(selected_transaction["pedido_id"]) if selected_transaction["pedido_id"] in options.values() else 0

                with st.form(f"editar_transacao_{selected_transaction['id']}"):
                    kind = st.radio("Tipo", ["Entrada", "Saída"], index=["Entrada", "Saída"].index(selected_transaction["tipo"]), horizontal=True)
                    description = st.text_input("Descrição *", value=selected_transaction["descricao"])
                    value = st.number_input("Valor (R$)", min_value=0.01, step=10.0, value=float(selected_transaction["valor"]))
                    when = st.date_input("Data", value=date.fromisoformat(selected_transaction["data"]), format="DD/MM/YYYY")
                    category = st.text_input("Categoria", value=selected_transaction["categoria"] or "")
                    order_label = st.selectbox("Vincular a um pedido", list(options), index=current_order_index)
                    confirm_delete = st.checkbox("Confirmo que desejo excluir este lançamento definitivamente.")
                    save_col, delete_col = st.columns(2)
                    save_changes = save_col.form_submit_button("Salvar alterações", use_container_width=True)
                    delete_transaction = delete_col.form_submit_button("Excluir lançamento", use_container_width=True)

                if save_changes:
                    if not description.strip():
                        st.error("Informe uma descrição.")
                    else:
                        execute(
                            "UPDATE transacoes SET tipo = ?, descricao = ?, valor = ?, data = ?, pedido_id = ?, categoria = ? WHERE id = ?",
                            (kind, description.strip(), value, when.isoformat(), options[order_label], category.strip(), selected_transaction["id"]),
                        )
                        st.success("Lançamento atualizado.")
                        reload_page()
                if delete_transaction:
                    if not confirm_delete:
                        st.warning("Marque a confirmação antes de excluir o lançamento.")
                    else:
                        execute("DELETE FROM transacoes WHERE id = ?", (selected_transaction["id"],))
                        st.success("Lançamento excluído.")
                        reload_page()
        else:
            st.caption("Os lançamentos financeiros aparecerão aqui.")


def main() -> None:
    database()
    inject_style()
    page = sidebar()
    render_brand_header(page)
    {"Visão geral": render_dashboard, "Pedidos": render_orders, "Orçamentos": render_quotes, "Financeiro": render_finance}[page]()


if __name__ == "__main__":
    main()
