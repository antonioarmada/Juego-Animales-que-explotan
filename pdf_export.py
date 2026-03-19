import json
from pathlib import Path

GAME_TITLE = "Magia en el zoológico"
PDF_LOGO_PATH = Path(__file__).resolve().parent / "img" / "invoa-color-1080px.png"
TRACE_COLORS = (
    "#d90429",
    "#3a0ca3",
    "#0077b6",
    "#1b998b",
    "#fb8500",
    "#6a4c93",
    "#2ec4b6",
    "#e63946",
)


def exportar_sesion_a_pdf(directorio_sesion, resumen, metricas_objetivos, traza_cursor, eventos):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    directorio_sesion = Path(directorio_sesion)
    directorio_sesion.mkdir(parents=True, exist_ok=True)
    pdf_path = directorio_sesion / "reporte_sesion.pdf"

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TituloReporte",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubtituloReporte",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#374151"),
            spaceAfter=8,
            spaceBefore=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MetaHeader",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=15,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#374151"),
            spaceAfter=1,
            spaceBefore=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TablaHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=5.4,
            leading=6.1,
            alignment=TA_CENTER,
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            name="KpiValor",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#111827"),
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="KpiEtiqueta",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#6b7280"),
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="DatoSecundario",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#374151"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="DatoCrudo",
            parent=styles["Code"],
            fontName="Courier",
            fontSize=6.5,
            leading=8,
            textColor=colors.black,
        )
    )

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=18 * mm,
        bottomMargin=14 * mm,
    )

    elementos = []
    elementos.extend(_build_summary_page(resumen, traza_cursor, styles))

    if metricas_objetivos:
        elementos.append(PageBreak())
        elementos.extend(_build_table_section("Metricas por objetivo", metricas_objetivos, styles))

    doc.build(
        elementos,
        onFirstPage=_draw_first_page,
        onLaterPages=_draw_page_number,
    )
    return pdf_path


def _build_summary_page(resumen, traza_cursor, styles):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle

    elementos = _build_header(resumen, styles)

    kpis = [
        ("Objetivos completados", _format_objetivos(resumen)),
        ("Tiempo medio por objetivo", _format_ms(resumen["promedio_tiempo_adquisicion_objetivo_ms"])),
        ("Eficiencia media", _format_ratio(resumen["promedio_eficiencia_trayectoria"])),
        (
            "Hover medio hasta explosion",
            _format_ms(resumen["promedio_tiempo_hover_hasta_explosion_ms"]),
        ),
    ]
    kpi_table = Table(
        [
            [Paragraph(valor, styles["KpiValor"]) for _, valor in kpis],
            [Paragraph(etiqueta, styles["KpiEtiqueta"]) for etiqueta, _ in kpis],
        ],
        colWidths=[42 * mm, 42 * mm, 42 * mm, 42 * mm],
        hAlign="CENTER",
    )
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("TOPPADDING", (0, 1), (-1, 1), 0),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 12),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elementos.extend([kpi_table, Spacer(1, 14)])

    secundarios = [
        ("Estado", resumen["estado"]),
        ("Duracion de la sesion", _format_ms(resumen["duracion_sesion_ms"])),
        ("Distancia total del cursor", f"{resumen['distancia_total_cursor_px']} px"),
        (
            "Mediana tiempo adquisicion",
            _format_ms(resumen["mediana_tiempo_adquisicion_objetivo_ms"]),
        ),
        ("Promedio reingresos hover", str(resumen["promedio_reingresos_hover"])),
        ("Tasa de completitud", _format_percent(resumen["tasa_completitud"])),
        ("Iniciada en", resumen["iniciada_en"]),
        ("Finalizada en", resumen["finalizada_en"]),
    ]
    secundarios_table = Table(
        [[Paragraph(f"<b>{etiqueta}:</b> {valor}", styles["DatoSecundario"])] for etiqueta, valor in secundarios],
        colWidths=[175 * mm],
        hAlign="LEFT",
    )
    secundarios_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elementos.extend(
        [
            Paragraph("Indicadores secundarios", styles["SubtituloReporte"]),
            secundarios_table,
            Spacer(1, 12),
            Paragraph("Trayectoria del cursor", styles["SubtituloReporte"]),
            _build_trace_drawing(traza_cursor),
        ]
    )
    return elementos


def _build_header(resumen, styles):
    from reportlab.platypus import Paragraph, Spacer

    return [
        Paragraph(GAME_TITLE, styles["TituloReporte"]),
        Spacer(1, 1),
        Paragraph("Reporte de sesión", styles["MetaHeader"]),
        Paragraph(f"Sesión: {resumen['id_sesion']}", styles["MetaHeader"]),
        Spacer(1, 8),
    ]


def _build_table_section(titulo, rows, styles):
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    elementos = [Paragraph(titulo, styles["SubtituloReporte"]), Spacer(1, 4)]
    for chunk in _chunk_rows(rows, 18):
        headers = list(chunk[0].keys())
        table_rows = [[
            Paragraph(_format_header_label(header), styles["TablaHeader"])
            for header in headers
        ]]
        for row in chunk:
            table_rows.append([str(row.get(header, "")) for header in headers])

        col_width = 180 * mm / len(headers)
        table = Table(table_rows, repeatRows=1, colWidths=[col_width] * len(headers))
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                    ("FONTSIZE", (0, 1), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, 0), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                    ("TOPPADDING", (0, 1), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        elementos.append(table)
        elementos.append(Spacer(1, 8))
    return elementos


def _chunk_rows(rows, chunk_size):
    for start in range(0, len(rows), chunk_size):
        yield rows[start : start + chunk_size]


def _format_ms(value):
    return f"{float(value):.0f} ms"


def _format_ratio(value):
    return f"{float(value):.2f}"


def _format_percent(value):
    return f"{float(value) * 100:.1f}%"


def _format_objetivos(resumen):
    return (
        f"{resumen['cantidad_objetivos_completada']}/"
        f"{resumen['cantidad_objetivos_configurada']}"
    )


def _format_header_label(header):
    parts = header.split("_")
    if len(parts) <= 2:
        return "<br/>".join(parts)
    midpoint = (len(parts) + 1) // 2
    return "<br/>".join(["_".join(parts[:midpoint]), "_".join(parts[midpoint:])])


def _draw_page_number(canvas, doc):
    from reportlab.lib.units import mm

    canvas.setFont("Helvetica", 8)
    canvas.setFillColorRGB(0.45, 0.45, 0.45)
    canvas.drawRightString(200 * mm, 8 * mm, f"Pagina {doc.page}")


def _draw_first_page(canvas, doc):
    from reportlab.lib.units import mm

    _draw_page_number(canvas, doc)
    if not PDF_LOGO_PATH.exists():
        return

    logo_width = 42 * mm
    image_width = 1080
    image_height = 258
    logo_height = logo_width * (image_height / image_width)
    x = doc.pagesize[0] - doc.rightMargin - logo_width
    top_y = doc.pagesize[1] - doc.topMargin - 4 * mm
    canvas.drawImage(
        str(PDF_LOGO_PATH),
        x,
        top_y - logo_height,
        width=logo_width,
        height=logo_height,
        preserveAspectRatio=True,
        mask="auto",
    )


def _build_trace_drawing(traza_cursor):
    from reportlab.graphics.shapes import Drawing, Line, Rect
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    width = 176 * mm
    height = 72 * mm
    drawing = Drawing(width, height)
    drawing.add(
        Rect(
            0,
            0,
            width,
            height,
            fillColor=colors.white,
            strokeColor=colors.HexColor("#cbd5e1"),
            strokeWidth=0.8,
            rx=8,
            ry=8,
        )
    )

    if not traza_cursor:
        return drawing

    max_x = max(max(row["x"] for row in traza_cursor), 1)
    max_y = max(max(row["y"] for row in traza_cursor), 1)
    pad = 10
    usable_width = width - pad * 2
    usable_height = height - pad * 2

    def scale_x(value):
        return pad + (value / max_x) * usable_width

    def scale_y(value):
        return pad + ((max_y - value) / max_y) * usable_height

    for index in range(1, len(traza_cursor)):
        start = traza_cursor[index - 1]
        end = traza_cursor[index]
        if start.get("indice_objetivo") != end.get("indice_objetivo"):
            continue
        attempt = max(1, int(end.get("indice_objetivo", 1)))
        color = colors.HexColor(TRACE_COLORS[(attempt - 1) % len(TRACE_COLORS)])
        drawing.add(
            Line(
                scale_x(start["x"]),
                scale_y(start["y"]),
                scale_x(end["x"]),
                scale_y(end["y"]),
                strokeColor=color,
                strokeWidth=1.15,
            )
        )

    return drawing
