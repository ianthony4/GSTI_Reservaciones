"""Genera Informe_Lab04.docx a partir de la plantilla EPIS y de los resultados en docs/.

Uso (desde lab04/):  python docs/generar_informe.py [--toc-pages paginas.json]
Requiere: python-docx.
Regla de formato: TODO en Calibri 12 (se normaliza al final en todas las partes XML).
"""
import copy
import json
import re
import sys
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DIAG = DOCS / "diagramas"
EV = DOCS / "evidencias"
TEMPLATE = ROOT / "Plantilla de Laboratorios EPIS - 2022.docx"
OUT = ROOT / "Informe_Lab04.docx"

FONT = "Calibri"
RED = RGBColor(0xC8, 0x31, 0x0E)
USABLE_CM = 16.0  # A4 (21 cm) - 2 x 2.5 cm
PENDING = "[PENDIENTE: completar]"

TOC_PAGES = {}
if "--toc-pages" in sys.argv:
    TOC_PAGES = json.loads(Path(sys.argv[sys.argv.index("--toc-pages") + 1]).read_text(encoding="utf-8"))

doc = Document(str(TEMPLATE))
body = doc.element.body


# --------------------------------------------------------------------------- estilos
def set_rfonts(rpr):
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in list(rf.attrib):
        del rf.attrib[a]
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), FONT)


def style_font(style, bold=None, italic=None, color=None):
    style.font.name = FONT
    style.font.size = Pt(12)
    set_rfonts(style.element.get_or_add_rPr())
    if bold is not None:
        style.font.bold = bold
    if italic is not None:
        style.font.italic = italic
    if color is not None:
        style.font.color.rgb = color


def get_style(name, style_id):
    for s in doc.styles:
        if s.name == name or s.style_id == style_id:
            return s
    st = OxmlElement("w:style")
    st.set(qn("w:type"), "paragraph")
    st.set(qn("w:styleId"), style_id)
    n = OxmlElement("w:name")
    n.set(qn("w:val"), name)
    st.append(n)
    b = OxmlElement("w:basedOn")
    b.set(qn("w:val"), "normal" if any(s.style_id == "normal" for s in doc.styles) else "Normal")
    st.append(b)
    doc.styles.element.append(st)
    return next(s for s in doc.styles if s.style_id == style_id)


normal = next(s for s in doc.styles if s.style_id in ("normal", "Normal"))
style_font(normal)
pf = normal.paragraph_format
pf.line_spacing = 1.15
pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
pf.space_after = Pt(6)
pf.space_before = Pt(0)

for name, sid, before, after in [("heading 1", "Heading1", 18, 8), ("heading 2", "Heading2", 14, 6),
                                 ("heading 3", "Heading3", 10, 4)]:
    st = get_style(name, sid)
    style_font(st, bold=True, color=RED if sid != "Heading3" else RGBColor(0x40, 0x40, 0x40))
    st.paragraph_format.space_before = Pt(before)
    st.paragraph_format.space_after = Pt(after)
    st.paragraph_format.keep_with_next = True
    st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    st.paragraph_format.line_spacing = 1.15
    ppr = st.element.get_or_add_pPr()
    if ppr.find(qn("w:outlineLvl")) is None:
        ol = OxmlElement("w:outlineLvl")
        ol.set(qn("w:val"), str(int(sid[-1]) - 1))
        ppr.append(ol)

for name, sid in [("title", "Title"), ("subtitle", "Subtitle")]:
    st = get_style(name, sid)
    style_font(st, bold=True)

caption = get_style("caption", "Caption")
style_font(caption, italic=False)
caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
caption.paragraph_format.space_before = Pt(3)
caption.paragraph_format.space_after = Pt(10)

for lvl in (1, 2, 3):
    st = get_style(f"toc {lvl}", f"TOC{lvl}")
    style_font(st, bold=(lvl == 1))
    st.paragraph_format.left_indent = Cm(0.6 * (lvl - 1))
    st.paragraph_format.space_after = Pt(2)
    st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

# --------------------------------------------------------------------------- página (A4, 2.5 cm)
sec = doc.sections[0]
OLD_USABLE_TW = sec.page_width.twips - sec.left_margin.twips - sec.right_margin.twips
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
    setattr(sec, m, Cm(2.5))
sec.header_distance = Cm(1.25)
sec.footer_distance = Cm(1.25)
SCALE = Cm(USABLE_CM).twips / OLD_USABLE_TW


def scale_widths(el):
    """Reescala anchos de tabla (dxa) del formato Carta al ancho útil A4."""
    for tag in ("w:tblW", "w:gridCol", "w:tcW", "w:tblInd"):
        for node in el.iter(qn(tag)):
            w = node.get(qn("w:w"))
            if w and node.get(qn("w:type"), "dxa") == "dxa" and w.isdigit():
                node.set(qn("w:w"), str(int(int(w) * SCALE)))


scale_widths(sec.header._element)

# --------------------------------------------------------------------------- tablas de la plantilla
children = list(body.iterchildren())
tables = [c for c in children if c.tag == qn("w:tbl")]
info_tbl, sol_tbl, retro_tbl, ref_tbl = tables
for t in tables:
    scale_widths(t)
banner_proto = copy.deepcopy(sol_tbl)
for tr in banner_proto.findall(qn("w:tr"))[1:]:
    banner_proto.remove(tr)
retro_proto = copy.deepcopy(retro_tbl)
# se elimina todo lo posterior a la tabla de información (se reconstruye abajo)
sect_pr = body.find(qn("w:sectPr"))
started = False
for c in children:
    if c is info_tbl:
        started = True
        continue
    if started and c is not sect_pr:
        body.remove(c)

from docx.table import Table  # noqa: E402

info = Table(info_tbl, doc)


def fill_cell(cell, lines, bold=False):
    """Escribe líneas en una celda reutilizando los párrafos vacíos existentes."""
    paras = [p for p in cell.paragraphs if not p.text.strip()]
    for i, line in enumerate(lines):
        p = paras[i] if i < len(paras) else cell.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(line)
        r.bold = bold


def clear_cell(cell):
    for p in cell.paragraphs[1:]:
        p._element.getparent().remove(p._element)
    for r in cell.paragraphs[0].runs:
        r._element.getparent().remove(r._element)


rows = info.rows
clear_cell(rows[1].cells[1]); fill_cell(rows[1].cells[1], ["Gestión de Sistemas y Tecnologías de Información"])
clear_cell(rows[2].cells[1]); fill_cell(rows[2].cells[1], ["Laboratorio 04: Proceso de Desarrollo de Software basado en SWEBOK"])
fill_cell(rows[3].cells[1], ["04"]); fill_cell(rows[3].cells[3], ["2026"]); fill_cell(rows[3].cells[5], ["X"])
fill_cell(rows[4].cells[1], [PENDING]); fill_cell(rows[4].cells[3], [PENDING])
integ = rows[5].cells[0]
fill_cell(integ, [f"1. {PENDING} (apellidos, nombres y CUI)", f"2. {PENDING}"])
fill_cell(rows[6].cells[0], ["M.Sc. Ing. Fabrizio Calienes Rodríguez"])

# --------------------------------------------------------------------------- helpers de contenido
fig_n = 0
tab_n = 0
headings = []  # (nivel, texto) para el índice
BULLET_NUM_ID = None


def _append(el):
    sect_pr.addprevious(el)
    return el


def para(text="", style=None, align=None, bold_all=False, keep_next=False, space_after=None):
    p = doc.add_paragraph(style=style)
    _append(p._element)
    add_runs(p, text, bold_all)
    if align is not None:
        p.paragraph_format.alignment = align
    if keep_next:
        p.paragraph_format.keep_with_next = True
    if space_after is not None:
        p.paragraph_format.space_after = Pt(space_after)
    return p


def add_runs(p, text, bold_all=False):
    """Soporta **negrita** dentro del texto."""
    for i, chunk in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
        if chunk:
            r = p.add_run(chunk)
            if bold_all or i % 2 == 1:
                r.bold = True


def heading(text, level):
    headings.append((level, text))
    p = doc.add_paragraph(style=f"Heading {level}")
    _append(p._element)
    p.add_run(text)
    return p


def page_break():
    p = doc.add_paragraph()
    _append(p._element)
    p.add_run().add_break(WD_BREAK.PAGE)


def ensure_bullets():
    global BULLET_NUM_ID
    if BULLET_NUM_ID:
        return BULLET_NUM_ID
    numbering = doc.part.numbering_part.element
    abs_ids = [int(a.get(qn("w:abstractNumId"))) for a in numbering.findall(qn("w:abstractNum"))]
    num_ids = [int(n.get(qn("w:numId"))) for n in numbering.findall(qn("w:num"))]
    aid, nid = max(abs_ids + [0]) + 1, max(num_ids + [0]) + 1
    xml = (f'<w:abstractNum xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:abstractNumId="{aid}">'
           '<w:multiLevelType w:val="hybridMultilevel"/>')
    for lvl, char in enumerate(["•", "–", "▪"]):
        ind = 360 + 360 * lvl
        xml += (f'<w:lvl w:ilvl="{lvl}"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="{char}"/>'
                f'<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="{ind + 360}" w:hanging="360"/></w:pPr>'
                f'<w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}" w:eastAsia="{FONT}"/></w:rPr></w:lvl>')
    xml += "</w:abstractNum>"
    from docx.oxml import parse_xml
    first_num = numbering.find(qn("w:num"))
    abs_el = parse_xml(xml)
    if first_num is not None:
        first_num.addprevious(abs_el)
    else:
        numbering.append(abs_el)
    num = parse_xml(f'<w:num xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:numId="{nid}">'
                    f'<w:abstractNumId w:val="{aid}"/></w:num>')
    numbering.append(num)
    BULLET_NUM_ID = nid
    return nid


def bullets(items, level=0):
    nid = ensure_bullets()
    for it in items:
        if isinstance(it, (list, tuple)):
            bullets(it, level + 1)
            continue
        p = para(it)
        p.paragraph_format.space_after = Pt(3)
        ppr = p._element.get_or_add_pPr()
        numpr = OxmlElement("w:numPr")
        il = OxmlElement("w:ilvl"); il.set(qn("w:val"), str(level))
        ni = OxmlElement("w:numId"); ni.set(qn("w:val"), str(nid))
        numpr.append(il); numpr.append(ni)
        ppr.append(numpr)


def next_fig():
    return f"Figura {fig_n + 1}"


def next_tab():
    return f"Tabla {tab_n + 1}"


def cap(label, text):
    p = para("", style="Caption")
    r = p.add_run(label + ". ")
    r.bold = True
    p.add_run(text)
    return p


def set_cell_borders(tbl_el):
    tblpr = tbl_el.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:space"), "0"); e.set(qn("w:color"), "808080")
        borders.append(e)
    old = tblpr.find(qn("w:tblBorders"))
    if old is not None:
        tblpr.remove(old)
    tblpr.append(borders)


def fix_width(t, widths):
    """Ancho total y por columna explícitos (dxa) con diseño fijo."""
    tblpr = t._element.tblPr
    for tag in ("w:tblW", "w:tblLayout"):
        old = tblpr.find(qn(tag))
        if old is not None:
            tblpr.remove(old)
    tw = OxmlElement("w:tblW"); tw.set(qn("w:w"), str(Cm(sum(widths)).twips)); tw.set(qn("w:type"), "dxa")
    tblpr.append(tw)
    lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblpr.append(lay)
    grid = t._element.find(qn("w:tblGrid"))
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(Cm(w).twips))
    for row in t.rows:
        for cell, w in zip(row.cells, widths):
            cell.width = Cm(w)


def shade(cell, fill):
    tcpr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


def cell_text(cell, text, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    lines = text.split("\n")
    p = cell.paragraphs[0]
    for i, line in enumerate(lines):
        if i:
            p = cell.add_paragraph()
        p.paragraph_format.alignment = align
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        add_runs(p, line, bold)


def table(headers, rows_, widths, caption_text, header_fill="F4D9D2", font_bold_first_col=False):
    """Tabla con bordes, encabezado en negrita y título numerado arriba."""
    global tab_n
    tab_n += 1
    c = cap(f"Tabla {tab_n}", caption_text)
    c.paragraph_format.keep_with_next = True
    c.paragraph_format.space_after = Pt(4)
    total = sum(widths)
    widths = [w * USABLE_CM / total for w in widths]
    t = doc.add_table(rows=1 + len(rows_), cols=len(headers))
    _append(t._element)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    set_cell_borders(t._element)
    grid = t._element.find(qn("w:tblGrid"))
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(Cm(w).twips))
    for ri, row in enumerate([headers] + rows_):
        tr = t.rows[ri]
        if ri == 0:
            trpr = tr._tr.get_or_add_trPr()
            th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trpr.append(th)
        cant = OxmlElement("w:cantSplit"); cant.set(qn("w:val"), "true"); tr._tr.get_or_add_trPr().append(cant)
        for ci, val in enumerate(row):
            cell = tr.cells[ci]
            cell.width = Cm(widths[ci])
            cell_text(cell, str(val), bold=(ri == 0) or (font_bold_first_col and ci == 0))
            if ri == 0:
                shade(cell, header_fill)
    fix_width(t, widths)
    spacer = para("")
    spacer.paragraph_format.space_after = Pt(4)
    return t


def img_size(path, width_cm=None, max_h_cm=19.0, max_w_cm=USABLE_CM):
    w, h = Image.open(path).size
    width_cm = width_cm or max_w_cm
    if width_cm * h / w > max_h_cm:
        width_cm = max_h_cm * w / h
    return min(width_cm, max_w_cm)


def figure(path, caption_text, width_cm=None, max_h_cm=17.0):
    global fig_n
    fig_n += 1
    p = para("", align=WD_ALIGN_PARAGRAPH.CENTER, keep_next=True, space_after=0)
    p.paragraph_format.line_spacing = 1.0
    p.add_run().add_picture(str(path), width=Cm(img_size(path, width_cm, max_h_cm)))
    cap(f"Figura {fig_n}", caption_text)


def figure_pair(left, right, caption_text, max_h_cm=12.0):
    """Dos imágenes lado a lado (mockup vs. pantalla real)."""
    global fig_n
    fig_n += 1
    t = doc.add_table(rows=1, cols=2)
    _append(t._element)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for cell, path, lbl in zip(t.rows[0].cells, (left, right), ("Mockup (wireframe)", "Pantalla implementada")):
        cell.width = Cm(USABLE_CM / 2)
        p = cell.paragraphs[0]
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.add_run().add_picture(str(path), width=Cm(img_size(path, USABLE_CM / 2 - 0.4, max_h_cm, USABLE_CM / 2 - 0.4)))
        q = cell.add_paragraph()
        q.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = q.add_run(lbl); r.bold = True
    fix_width(t, [USABLE_CM / 2, USABLE_CM / 2])
    cap(f"Figura {fig_n}", caption_text)


def boxed(lines, caption_text=None):
    """Bloque de texto (código o salida de consola) en una celda sombreada."""
    global tab_n
    t = doc.add_table(rows=1, cols=1)
    _append(t._element)
    set_cell_borders(t._element)
    cell = t.rows[0].cells[0]
    cell.width = Cm(USABLE_CM)
    shade(cell, "F5F5F5")
    for i, line in enumerate(lines):
        p = cell.paragraphs[0] if i == 0 else cell.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        p.add_run(line.replace("\t", "    "))
    fix_width(t, [USABLE_CM])
    if caption_text:
        cap(next_fig(), caption_text)
        globals()["fig_n"] += 1
    else:
        para("").paragraph_format.space_after = Pt(2)


def fit_template_table(t):
    """Ajusta una tabla copiada de la plantilla al ancho útil y la mantiene unida a lo siguiente."""
    tblpr = t.find(qn("w:tblPr"))
    for tag in ("w:tblInd",):
        old = tblpr.find(qn(tag))
        if old is not None:
            tblpr.remove(old)
    full = Cm(USABLE_CM).twips
    tw = tblpr.find(qn("w:tblW"))
    if tw is not None:
        tw.set(qn("w:w"), str(full)); tw.set(qn("w:type"), "dxa")
    for node in t.iter(qn("w:gridCol")):
        node.set(qn("w:w"), str(full))
    for node in t.iter(qn("w:tcW")):
        node.set(qn("w:w"), str(full)); node.set(qn("w:type"), "dxa")
    for p in t.iter(qn("w:p")):
        ppr = p.find(qn("w:pPr"))
        if ppr is None:
            ppr = OxmlElement("w:pPr"); p.insert(0, ppr)
        kn = OxmlElement("w:keepNext"); ppr.insert(0, kn)
    return t


def banner(text):
    t = fit_template_table(copy.deepcopy(banner_proto))
    _append(t)
    tc_p = t.find(".//" + qn("w:p"))
    runs = tc_p.findall(qn("w:r"))
    first = True
    for r in runs:
        for tnode in r.findall(qn("w:t")):
            if first:
                tnode.text = text
                first = False
            else:
                tnode.text = ""
    sp = para("")
    sp.paragraph_format.space_after = Pt(0)
    sp.paragraph_format.keep_with_next = True


def toc():
    """Campo TOC con entradas precargadas (Word lo actualiza al abrir)."""
    entries = [(lvl, txt) for lvl, txt in ALL_HEADINGS if lvl <= 2]
    first = True
    for i, (lvl, txt) in enumerate(entries):
        p = doc.add_paragraph(style=f"toc {lvl}")
        _append(p._element)
        ppr = p._element.get_or_add_pPr()
        tabs = OxmlElement("w:tabs")
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "right"); tab.set(qn("w:leader"), "dot"); tab.set(qn("w:pos"), str(Cm(USABLE_CM).twips - 10))
        tabs.append(tab); ppr.append(tabs)
        if first:
            for kind, instr in (("begin", None), (None, ' TOC \\o "1-2" \\h \\z \\u '), ("separate", None)):
                r = OxmlElement("w:r")
                if kind:
                    fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), kind); r.append(fc)
                else:
                    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr; r.append(it)
                p._element.append(r)
            first = False
        run = p.add_run(txt)
        run.bold = (lvl == 1)
        p.add_run("\t" + str(TOC_PAGES.get(txt, "")))
        if i == len(entries) - 1:
            r = OxmlElement("w:r")
            fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), "end"); r.append(fc)
            p._element.append(r)


def read_ev(name):
    return (EV / name).read_text(encoding="utf-8").splitlines()


ALL_HEADINGS = []  # se llena con una pasada en seco antes de escribir el índice


# =========================================================================== CONTENIDO
def contenido():
    # ------------------------------------------------------------------ I, II, III
    banner("SOLUCIÓN Y RESULTADOS")
    heading("I. Objetivos", 1)
    heading("Objetivo general", 3)
    para("Comprender y aplicar los conceptos clave del **proceso de desarrollo de software** según el **SWEBOK** "
         "(*Software Engineering Body of Knowledge*), simulando un proyecto real que recorre sus áreas de "
         "conocimiento desde la planificación hasta el mantenimiento.".replace("*Software Engineering Body of Knowledge*", "Software Engineering Body of Knowledge"))
    heading("Objetivos específicos", 3)
    bullets([
        "Planificar el proyecto eligiendo y justificando un modelo de proceso, con entregables por fase y estimación de tiempos.",
        "Recolectar los requisitos con el cliente y especificarlos en un documento estilo IEEE 830 / ISO/IEC/IEEE 29148.",
        "Diseñar la arquitectura del sistema con diagramas UML de clases y de secuencia.",
        "Construir las funcionalidades de reserva, modificación, cancelación y notificación, partiendo de mockups.",
        "Verificar el sistema con un plan de pruebas y pruebas unitarias automatizadas.",
        "Gestionar un cambio de requisitos (recompensas), aplicar pruebas de regresión y clasificar el mantenimiento según SWEBOK.",
    ])

    heading("II. Temas a tratar", 1)
    table(["Tema", "Cómo se aborda en el laboratorio"], [
        ["Metodologías de desarrollo", "Comparación cascada / iterativo-incremental / ágil; se adopta un modelo iterativo-incremental de 4 iteraciones."],
        ["Guía SWEBOK", "Se usan 7 áreas de conocimiento como hilo conductor: proceso, requisitos, diseño, construcción, pruebas, mantenimiento y gestión."],
        ["Tecnologías de información", "Aplicación web con Python, FastAPI, SQLite, HTML/CSS/JS, pytest y PlantUML."],
    ], [4.5, 11.5], "Temas del laboratorio y su aplicación")

    heading("III. Marco teórico", 1)
    heading("3.1 SWEBOK", 2)
    para("El SWEBOK es la guía de la IEEE Computer Society que reúne el conocimiento **generalmente aceptado** de la "
         "ingeniería de software y lo organiza en **áreas de conocimiento** (Knowledge Areas, KA). No prescribe una "
         "metodología: define el alcance de la disciplina, ofrece un vocabulario común y sirve de base para planes de "
         "estudio, certificaciones y descripciones de puestos (Bourque y Fairley, 2014). La versión 3.0 (2014) define 15 "
         "áreas, y la versión 4.0 (2024) las amplía a 18 al agregar, entre otras, arquitectura, operaciones y seguridad "
         "de software (Washizaki, 2024).")
    para("Las siete áreas usadas en esta práctica se resumen a continuación:")
    table(["Área de conocimiento", "Descripción (redacción propia)"], [
        ["Proceso de software", "Define, implementa, mide y mejora el conjunto de actividades del ciclo de vida y los modelos que las ordenan."],
        ["Requisitos de software", "Elicita, analiza, especifica y valida lo que el sistema debe hacer y bajo qué restricciones."],
        ["Diseño de software", "Transforma los requisitos en una arquitectura (alto nivel) y en componentes e interfaces detallados (bajo nivel)."],
        ["Construcción de software", "Codifica, integra, depura y prueba unitariamente el software siguiendo estándares de calidad."],
        ["Pruebas de software", "Verifica y valida dinámicamente, con casos finitos, que el comportamiento cumple lo esperado."],
        ["Mantenimiento de software", "Corrige, adapta, mejora y previene problemas del software después de la entrega."],
        ["Gestión de la ingeniería de software", "Planifica, estima, supervisa y controla el proyecto (alcance, tiempo, costo y riesgos)."],
    ], [5, 11], "Áreas de conocimiento SWEBOK usadas en el laboratorio", font_bold_first_col=True)
    heading("3.2 Modelos de proceso", 2)
    bullets([
        "**Cascada:** fases secuenciales (requisitos → diseño → codificación → pruebas → operación). Royce (1970) ya advertía que, sin retroalimentación entre fases, los errores se descubren tarde y su corrección es costosa.",
        "**Iterativo-incremental:** el sistema se construye en incrementos funcionales; cada iteración recorre requisitos, diseño, construcción y pruebas, y recibe retroalimentación del cliente (Sommerville, 2016).",
        "**Ágil (Scrum, XP):** iteraciones cortas, colaboración con el cliente y respuesta al cambio; es adecuado cuando los requisitos son volátiles (Pressman y Maxim, 2019).",
    ])
    heading("3.3 Requisitos y su especificación", 2)
    para("Un **requisito funcional** describe un servicio o comportamiento del sistema; un **requisito no funcional** "
         "establece una propiedad o restricción de calidad (rendimiento, seguridad, usabilidad, etc.). La especificación "
         "de requisitos de software (ERS) se estructura según IEEE Std 830-1998, hoy reemplazado por ISO/IEC/IEEE 29148:2018, "
         "y exige que cada requisito sea correcto, no ambiguo, verificable y trazable.")
    heading("3.4 Diseño con UML", 2)
    para("UML ofrece vistas complementarias: el **diagrama de casos de uso** muestra actores y funcionalidades; el "
         "**diagrama de clases** describe la estructura estática (entidades, atributos y relaciones); y el **diagrama de "
         "secuencia** muestra la interacción entre objetos en el tiempo para un escenario concreto.")
    heading("3.5 Pruebas y mantenimiento", 2)
    para("Las pruebas se organizan por niveles: **unitarias** (componentes aislados), de **integración** (componentes "
         "trabajando juntos, por ejemplo la API con la base de datos) y de **regresión** (volver a ejecutar las pruebas "
         "después de un cambio para confirmar que no se dañó lo existente). El mantenimiento se clasifica, según SWEBOK e "
         "ISO/IEC 14764, en **correctivo, adaptativo, perfectivo y preventivo**.")
    heading("3.6 Tecnologías utilizadas", 2)
    table(["Tecnología", "Uso en el proyecto"], [
        ["Python 3 + FastAPI", "API REST, validación con Pydantic y documentación OpenAPI automática."],
        ["SQLite + SQLAlchemy 2", "Persistencia relacional embebida mediante un ORM."],
        ["HTML, CSS y JavaScript", "Interfaz web responsive que consume la API con fetch."],
        ["pytest + TestClient", "Pruebas unitarias de servicios y pruebas de integración de la API."],
        ["PlantUML", "Diagramas UML como código (.puml) exportados a PNG."],
    ], [5, 11], "Tecnologías de información empleadas")

    # ------------------------------------------------------------------ IV Desarrollo
    heading("IV. Desarrollo de la práctica", 1)
    para("El proyecto desarrollado, **ReservaYa**, es un sistema de reservas en línea para la cadena de restaurantes "
         "\"Sabores del Sur\" (tres sucursales en Arequipa). Permite reservar mesas, modificar y cancelar reservas, y envía "
         "notificaciones de confirmación. La práctica se realizó en cuatro partes; en cada una se indican los entregables "
         "producidos y las evidencias guardadas en el repositorio (carpetas docs/, docs/diagramas/ y docs/evidencias/).")

    # ---------------- Parte 1
    heading("Parte 1: Introducción al proyecto y planificación", 2)
    heading("1.1 SWEBOK aplicado al proyecto", 3)
    table(["Área SWEBOK", "Aplicación en ReservaYa", "Parte"], [
        ["Proceso de software", "Modelo iterativo-incremental de 4 iteraciones", "1"],
        ["Gestión", "Plan, estimación, cronograma y riesgos", "1 (transversal)"],
        ["Requisitos", "Acta con el cliente y ERS (RF, RNF, restricciones)", "2"],
        ["Diseño", "Arquitectura en capas y UML de clases y de secuencia", "2"],
        ["Construcción", "Mockups, API FastAPI y frontend", "3"],
        ["Pruebas", "Plan de pruebas y pytest", "3"],
        ["Mantenimiento", "Recompensas, migración de BD y regresión", "4"],
    ], [4, 9, 3], "Correspondencia entre áreas SWEBOK y actividades del proyecto")
    heading("1.2 Presentación del proyecto y alcance", 3)
    bullets([
        "**Funciones:** reservar mesas, cancelar o modificar reservas y enviar notificaciones de confirmación al cliente.",
        "**Stack:** Python + FastAPI, SQLite con SQLAlchemy, frontend HTML/CSS/JS sin frameworks y pruebas con pytest.",
        "**Notificaciones simuladas:** se registran en la base de datos y en un archivo de log; el envío real por correo queda fuera del alcance.",
    ])
    heading("1.3 Plan de desarrollo", 3)
    para("**Modelo de proceso elegido: iterativo-incremental.** Se descartó la cascada porque la guía anticipa un cambio "
         "de requisitos en la Parte 4: con un modelo secuencial ese cambio obligaría a rehacer fases cerradas, mientras que "
         "en el iterativo se incorpora como un nuevo incremento. Además, cada iteración entrega un producto verificable y "
         "permite validar con el cliente.")
    table(["Iteración", "Incremento entregado"], [
        ["I-1", "Plan del proyecto"], ["I-2", "ERS y diseño (arquitectura y UML)"],
        ["I-3", "Núcleo funcional: reservas, notificaciones, frontend y pruebas"],
        ["I-4", "Cambio de requisitos: recompensas, regresión y presentación"],
    ], [3, 13], "Iteraciones planificadas")
    table(["Fase", "Actividades", "Entregables"], [
        ["1. Planificación", "Estudio de SWEBOK, alcance, modelo, estimación, riesgos", "fase1_planificacion.md, cronograma"],
        ["2. Requisitos", "Reunión con el cliente, análisis, especificación y validación", "Acta y ERS v1.0"],
        ["3. Diseño", "Arquitectura, modelo de datos, diseño detallado", "Diagramas UML (.puml y .png)"],
        ["4. Construcción", "Mockups, API y frontend", "mockups/, backend/app/, frontend/"],
        ["5. Pruebas", "Plan de pruebas, pruebas unitarias y de API", "backend/tests/, pytest_fase3.txt"],
        ["6. Mantenimiento", "Cambio de requisitos, ERS/UML v1.1, regresión", "fase4_mantenimiento.md, pytest_fase4.txt"],
        ["7. Revisión", "Presentación final e informe", "presentacion_final.md, este informe"],
    ], [3.3, 6.7, 6], "Fases del ciclo de vida y entregables por fase")
    para("La estimación se hizo por descomposición de tareas y juicio experto, a partir de las 3 horas por parte que indica la guía, más trabajo autónomo:")
    est = [["A1", "Estudio de SWEBOK y sus áreas", "Planificación", "1.0"], ["A2", "Alcance y modelo de proceso", "Planificación", "0.5"],
           ["A3", "Estimación, cronograma y riesgos", "Planificación", "1.5"], ["A4", "Reunión con el cliente y acta", "Requisitos", "1.0"],
           ["A5", "Redacción de la ERS", "Requisitos", "2.0"], ["A6", "Arquitectura y modelo de datos", "Diseño", "1.0"],
           ["A7", "Diagramas UML de clases y de secuencia", "Diseño", "1.0"], ["A8", "Mockups de interfaces", "Construcción", "1.0"],
           ["A9", "Modelos, servicios y API", "Construcción", "3.0"], ["A10", "Frontend", "Construcción", "2.0"],
           ["A11", "Plan de pruebas y pruebas unitarias/API", "Pruebas", "2.0"], ["A12", "Análisis del cambio y ERS/UML", "Mantenimiento", "1.0"],
           ["A13", "Implementación del cambio", "Mantenimiento", "1.5"], ["A14", "Pruebas de regresión", "Mantenimiento", "0.5"],
           ["A15", "Presentación e informe", "Revisión", "2.0"], ["", "**Total**", "", "**21.0**"]]
    table(["ID", "Actividad", "Fase", "Horas"], est, [1.5, 8.5, 3.5, 2.5], "Estimación de tiempo por actividad")
    para(f"La {next_fig()} muestra el cronograma resultante (de lunes a viernes, una parte por semana).")
    figure(DIAG / "cronograma_gantt.png", "Cronograma del proyecto (diagrama de Gantt, PlantUML)", width_cm=15)
    table(["ID", "Riesgo", "Prob.", "Impacto", "Mitigación"], [
        ["R1", "Cambios de requisitos", "Alta", "Medio", "Modelo iterativo; ERS versionada; diseño en capas"],
        ["R2", "Doble reserva de una mesa", "Media", "Alto", "Validación de solapamiento y pruebas específicas"],
        ["R3", "Subestimar la construcción", "Media", "Medio", "Priorizar RF esenciales"],
        ["R4", "Poca disponibilidad del cliente", "Media", "Medio", "Acta con acuerdos; validación asíncrona"],
        ["R5", "Fallos en el envío real de notificaciones", "Baja", "Bajo", "Notificaciones simuladas y desacopladas"],
        ["R6", "Pérdida de código", "Baja", "Alto", "Repositorio Git y copias"],
    ], [1.2, 4.5, 1.6, 1.9, 6.8], "Riesgos principales del proyecto")

    # ---------------- Parte 2
    heading("Parte 2: Requisitos y diseño de software", 2)
    heading("2.1 Reunión con el cliente (simulada)", 3)
    para("La reunión de elicitación es **simulada**: un integrante asumió el rol de gerente de operaciones de la cadena. "
         "La Tabla siguiente resume las preguntas y respuestas que dieron origen a las reglas de negocio.")
    table(["N.º", "Pregunta del equipo", "Respuesta del cliente"], [
        ["1", "¿Cuántas sucursales hay?", "Tres en Arequipa: Centro, Cayma y Yanahuara."],
        ["2", "¿Horario de atención?", "12:00 a 23:00; la reserva no puede terminar después del cierre."],
        ["3", "¿Duración de una reserva?", "2 horas desde la hora reservada."],
        ["4", "¿Datos del cliente?", "Nombre, correo, teléfono, sucursal, fecha, hora, personas y comentarios."],
        ["5", "¿El cliente elige la mesa?", "No; se asigna la mesa más pequeña disponible que alcance."],
        ["6", "¿Anticipación?", "Desde hoy (horas futuras) hasta 60 días."],
        ["7", "¿Cuenta de usuario?", "No; se identifica con correo y código de reserva."],
        ["8", "¿Qué se puede modificar?", "Fecha, hora, sucursal, personas y comentarios."],
        ["9", "¿Hasta cuándo cancelar?", "Mientras esté confirmada y no haya iniciado."],
        ["10", "¿Notificaciones?", "Al reservar, modificar y cancelar; por ahora simuladas."],
        ["11", "¿Tamaño máximo de grupo?", "El de la mesa más grande (8 personas)."],
    ], [1.2, 5.3, 9.5], "Acta de la reunión con el cliente (simulada)")
    heading("2.2 Especificación de requisitos (ERS v1.0, estilo IEEE 830 / ISO/IEC/IEEE 29148)", 3)
    table(["ID", "Requisito funcional", "Prioridad"], [
        ["RF-01", "Listar las sucursales con dirección, teléfono y horario.", "Alta"],
        ["RF-02", "Consultar la disponibilidad de mesa por sucursal, fecha, hora y número de personas.", "Alta"],
        ["RF-03", "Crear una reserva asignando la mesa más pequeña disponible y generando un código único.", "Alta"],
        ["RF-04", "Consultar una reserva por su código y listar las reservas de un cliente por su correo.", "Alta"],
        ["RF-05", "Modificar fecha, hora, sucursal, personas y comentarios de una reserva confirmada.", "Alta"],
        ["RF-06", "Cancelar una reserva confirmada que aún no inicia.", "Alta"],
        ["RF-07", "Enviar una notificación de confirmación al crear la reserva.", "Alta"],
        ["RF-08", "Enviar notificaciones al modificar y al cancelar.", "Media"],
        ["RF-09", "Consultar el historial de notificaciones de una reserva.", "Baja"],
    ], [1.8, 11.7, 2.5], "Requisitos funcionales")
    table(["ID", "Tipo", "Requisito no funcional"], [
        ["RNF-01", "Usabilidad", "Reserva en una sola pantalla; interfaz responsive."],
        ["RNF-02", "Rendimiento", "Respuesta de la API menor a 1 s con datos de prueba."],
        ["RNF-03", "Integridad", "No pueden existir dos reservas confirmadas solapadas en la misma mesa."],
        ["RNF-04", "Seguridad", "Modificar o cancelar exige el código y el correo del titular; se validan formatos."],
        ["RNF-05", "Mantenibilidad", "Arquitectura en capas y pruebas automatizadas."],
        ["RNF-06", "Portabilidad", "Ejecutable en Windows, Linux o macOS con Python 3.10+."],
        ["RNF-07", "Documentación", "API documentada en OpenAPI (/docs)."],
    ], [2, 3, 11], "Requisitos no funcionales")
    para("**Restricciones:** RS-01 tecnología (FastAPI, SQLite, HTML/CSS/JS); RS-02 horario 12:00–23:00 con reservas de 2 h; "
         "RS-03 solo horas futuras y hasta 60 días; RS-04 personas entre 1 y la capacidad máxima de la sucursal; RS-05 "
         "notificaciones simuladas; RS-06 plazo de 4 semanas.")
    para(f"Los casos de uso identificados se muestran en la {next_fig()}; las operaciones de reserva incluyen el envío de notificación.")
    figure(DIAG / "casos_uso.png", "Diagrama UML de casos de uso", width_cm=14)
    table(["ID", "Requisito", "Criterio de aceptación (Dado / Cuando / Entonces)"], [
        ["CA-01", "RF-01", "Dado que existen sucursales, cuando se consulta /api/restaurants, entonces se listan las 3 con su horario."],
        ["CA-02", "RF-02", "Dada una mesa libre, cuando se consulta disponibilidad, entonces available = true y se indica la mesa."],
        ["CA-03", "RF-03", "Dados datos válidos, cuando se reserva, entonces HTTP 201, código de 8 caracteres y estado CONFIRMED."],
        ["CA-04", "RF-03, RNF-03", "Dadas todas las mesas ocupadas, cuando se reserva, entonces HTTP 409 y no se crea la reserva."],
        ["CA-05", "RF-04", "Dado un correo, cuando se consultan sus reservas, entonces solo se listan las suyas."],
        ["CA-06", "RF-05", "Dada una reserva confirmada, cuando se cambia a un horario libre, entonces se actualiza y se notifica."],
        ["CA-07", "RF-06", "Dada una reserva confirmada, cuando se cancela, entonces queda CANCELLED, la mesa se libera y se notifica."],
        ["CA-08", "RF-07", "Dada una reserva creada, entonces existe una notificación CONFIRMATION al correo del cliente."],
        ["CA-09", "RNF-04", "Dado un correo distinto al del titular, cuando se modifica o cancela, entonces HTTP 403."],
    ], [1.8, 2.7, 11.5], "Criterios de aceptación")
    heading("2.3 Diseño de software", 3)
    para(f"Se eligió una arquitectura **cliente-servidor en capas** ({next_fig()}): presentación (frontend), API (routers "
         "FastAPI y esquemas Pydantic), servicios (reglas de negocio) y datos (SQLAlchemy + SQLite). El notificador escribe "
         "en la base de datos y en un archivo de log.")
    figure(DIAG / "arquitectura.png", "Arquitectura en capas del sistema", max_h_cm=17)
    para(f"El modelo de datos tiene cinco entidades: Restaurant, Table, Customer, Reservation y Notification. La {next_fig()} "
         "presenta el diagrama de clases con sus relaciones y los dos servicios que contienen la lógica de negocio.")
    figure(DIAG / "clases.png", "Diagrama UML de clases (v1.0)", max_h_cm=17)
    para(f"La {next_fig()} detalla la interacción para el escenario principal **crear reserva y notificar**, incluido el "
         "flujo alternativo cuando no hay mesas disponibles (HTTP 409).")
    figure(DIAG / "secuencia_crear_reserva.png", "Diagrama UML de secuencia: crear reserva y notificar", max_h_cm=17)
    table(["Método", "Ruta", "Descripción", "RF"], [
        ["GET", "/api/restaurants", "Lista sucursales", "RF-01"],
        ["GET", "/api/restaurants/{id}/availability", "Consulta disponibilidad", "RF-02"],
        ["POST", "/api/reservations", "Crea reserva", "RF-03, RF-07"],
        ["GET", "/api/reservations/{code}?email=", "Consulta una reserva", "RF-04"],
        ["GET", "/api/customers/{email}/reservations", "Reservas de un cliente", "RF-04"],
        ["PUT", "/api/reservations/{code}", "Modifica reserva", "RF-05, RF-08"],
        ["POST", "/api/reservations/{code}/cancel", "Cancela reserva", "RF-06, RF-08"],
        ["GET", "/api/reservations/{code}/notifications", "Historial de notificaciones", "RF-09"],
    ], [1.6, 6.6, 4.6, 3.2], "Diseño de la API REST (v1.0)")

    # ---------------- Parte 3
    heading("Parte 3: Construcción y pruebas de software", 2)
    heading("3.1 Mockups de las interfaces clave", 3)
    para("Antes de programar se diseñaron tres wireframes de baja fidelidad en HTML (carpeta mockups/). Las figuras "
         "siguientes comparan cada mockup con la pantalla que finalmente se implementó.")
    figure_pair(EV / "mockup_01_reservar.png", EV / "app_01_reservar.png",
                "Pantalla «Reservar mesa»: tarjetas de sucursal, formulario y verificación de disponibilidad (CU-01 a CU-03)")
    figure_pair(EV / "mockup_02_confirmacion.png", EV / "app_02_confirmacion.png",
                "Pantalla «Confirmación»: código de reserva, datos y notificación enviada (CU-03, CU-07)")
    figure_pair(EV / "mockup_03_mis_reservas.png", EV / "app_05_modificar_form.png",
                "Pantalla «Mis reservas»: listado y formulario desplegable de modificación (CU-04 a CU-06)")
    heading("3.2 Construcción", 3)
    table(["Módulo", "Responsabilidad"], [
        ["app/main.py", "Crea la aplicación FastAPI, registra routers, traduce errores de negocio a HTTP y sirve el frontend."],
        ["app/models.py", "Entidades SQLAlchemy y enumeraciones de estado."],
        ["app/schemas.py", "Validación Pydantic (correo, teléfono, rangos) y modelos de respuesta."],
        ["app/services/reservations.py", "ReservationService: horario, anticipación, capacidad, no solapamiento, asignación de mesa."],
        ["app/services/notifications.py", "NotificationService: notificaciones simuladas (BD + log)."],
        ["app/routers/*.py", "Endpoints de sucursales, reservas y clientes."],
        ["app/seed.py", "Datos iniciales: 3 sucursales con 6 mesas (capacidades 2, 2, 4, 4, 6, 8)."],
        ["frontend/", "index.html, styles.css y app.js (fetch a /api)."],
    ], [5.5, 10.5], "Estructura del código fuente")
    para("La regla central del negocio (RNF-03) es la detección de solapamientos: una mesa está ocupada si existe una "
         "reserva confirmada en la misma fecha cuyo inicio es anterior al fin de la nueva y cuyo fin es posterior al inicio "
         "de la nueva. Entre las mesas libres con capacidad suficiente se elige la de menor capacidad:")
    boxed([
        "def find_free_table(self, restaurant, day, start, end, party_size, exclude_reservation_id=None):",
        "    busy_stmt = select(Reservation.table_id).where(",
        "        Reservation.restaurant_id == restaurant.id, Reservation.date == day,",
        "        Reservation.status == ReservationStatus.CONFIRMED,",
        "        Reservation.start_time < end, Reservation.end_time > start)",
        "    if exclude_reservation_id is not None:   # al modificar, no chocar consigo misma",
        "        busy_stmt = busy_stmt.where(Reservation.id != exclude_reservation_id)",
        "    busy = set(self.db.scalars(busy_stmt))",
        "    candidates = sorted((t for t in restaurant.tables if t.capacity >= party_size),",
        "                        key=lambda t: (t.capacity, t.number))",
        "    return next((t for t in candidates if t.id not in busy), None)",
    ], "Extracto de ReservationService.find_free_table (backend/app/services/reservations.py)")
    bullets([
        "**Validaciones adicionales:** horas en :00 o :30; fecha y hora futuras; máximo 60 días; inicio ≥ 12:00 y fin ≤ 23:00; personas ≤ capacidad máxima.",
        "**Errores de negocio a HTTP:** 404 no encontrado, 403 correo no titular, 409 sin mesas o estado inválido, 422 regla incumplida.",
        "**Notificaciones:** cada creación, modificación y cancelación registra una fila en notifications y una línea en notifications.log con asunto y mensaje.",
    ])
    para(f"Las figuras {fig_n + 1} a {fig_n + 5} muestran el sistema funcionando con el servidor real (capturas tomadas con un navegador Chromium automatizado).")
    figure(EV / "app_03_validacion_error.png", "Validación: 9 personas superan la capacidad máxima de la sucursal (8)", width_cm=11)
    figure(EV / "app_06_modificada_cancelada_notificaciones.png",
           "Mis reservas: una reserva modificada (20:00, 5 personas, mesa 5), otra cancelada e historial de notificaciones", max_h_cm=17)
    figure(EV / "app_04_mis_reservas.png", "Listado de reservas del cliente consultado por correo", width_cm=11)
    figure(EV / "app_07_openapi_docs.png", "Documentación OpenAPI generada automáticamente en /docs (RNF-07)", max_h_cm=15)
    figure(EV / "app_08_movil.png", "Vista en un teléfono de 390 px de ancho (RNF-01, diseño responsive)", max_h_cm=13)
    para("Log real de notificaciones generado durante la demostración (docs/evidencias/notifications_demo.log):")
    boxed(read_ev("notifications_demo.log"))

    heading("3.3 Plan de pruebas", 3)
    bullets([
        "**Objetivo:** verificar RF-01 a RF-09, RNF-03 y RNF-04, y cubrir los criterios CA-01 a CA-09.",
        "**Alcance:** pruebas unitarias de la capa de servicios y pruebas de integración de la API con TestClient.",
        "**Entorno:** pytest; base de datos SQLite en memoria, independiente por prueba; fechas relativas al día de ejecución.",
        "**Criterio de salida:** 100 % de los casos ejecutados y aprobados.",
    ])
    tp = [
        ["TP-01", "Listar sucursales (3, con 6 mesas)", "CA-01", "PASSED"],
        ["TP-02", "Disponibilidad asigna la mesa más pequeña (3 pers. → mesa de 4)", "CA-02", "PASSED"],
        ["TP-03", "Crear reserva: código de 8 caracteres, CONFIRMED, fin = inicio + 2 h", "CA-03", "PASSED"],
        ["TP-04", "Notificación CONFIRMATION en BD y en el log", "CA-08", "PASSED"],
        ["TP-05", "La 7.ª reserva a la misma hora → sin mesas (409)", "CA-04", "PASSED"],
        ["TP-06", "Misma mesa en horarios no solapados (13:00 y 15:00)", "CA-04", "PASSED"],
        ["TP-07", "Solapamiento parcial (13:00 y 14:00) → mesas distintas", "CA-04", "PASSED"],
        ["TP-08", "Fecha pasada rechazada (422)", "RS-03", "PASSED"],
        ["TP-09", "Más de 60 días rechazada (422)", "RS-03", "PASSED"],
        ["TP-10", "Fuera de horario: 11:00, 21:30, 22:00 (3 variantes)", "RS-02", "PASSED ×3"],
        ["TP-11", "Excede capacidad (9 personas)", "RS-04", "PASSED"],
        ["TP-12", "Minutos no permitidos (13:15)", "Validación", "PASSED"],
        ["TP-13", "Listar solo las reservas del cliente", "CA-05", "PASSED"],
        ["TP-14", "Modificar hora y notificar MODIFICATION", "CA-06", "PASSED"],
        ["TP-15", "Modificar a horario lleno → 409 sin cambios", "CA-04", "PASSED"],
        ["TP-16", "Modificar solo comentarios no choca consigo misma", "CA-06", "PASSED"],
        ["TP-17", "Cancelar libera la mesa y notifica CANCELLATION", "CA-07", "PASSED"],
        ["TP-18", "No se cancela dos veces (409)", "RF-06", "PASSED"],
        ["TP-19", "Correo no titular → 403 al modificar y cancelar", "CA-09", "PASSED"],
        ["TP-20", "Código inexistente → 404", "RF-04", "PASSED"],
        ["TP-21", "API GET /api/restaurants → 200", "CA-01", "PASSED"],
        ["TP-22", "API POST reserva válida → 201", "CA-03", "PASSED"],
        ["TP-23", "API datos inválidos (correo, teléfono, 0 personas, 23:00) → 422", "RNF-04", "PASSED"],
        ["TP-24", "API flujo completo crear → consultar → modificar → cancelar", "CA-06, CA-07", "PASSED"],
        ["TP-25", "API disponibilidad (5 personas → mesa de 6)", "CA-02", "PASSED"],
        ["TP-26", "API reservas por cliente y 403", "CA-05, CA-09", "PASSED"],
        ["TP-27", "API 404 y 409", "CA-04", "PASSED"],
    ]
    table(["ID", "Descripción / resultado esperado", "Criterio", "Resultado obtenido"], tp, [1.6, 9.4, 2.4, 2.6],
          "Casos de prueba de la versión 1.0 (detalle de entradas en docs/fase3_construccion_pruebas.md)")
    out3 = read_ev("pytest_fase3.txt")
    summary3 = [l for l in out3 if "passed" in l and "=" in l]
    para("**Resultados:** se ejecutaron **29 pruebas** (27 casos; TP-10 tiene 3 variantes) y las **29 aprobaron**. "
         "Resumen de la salida real (docs/evidencias/pytest_fase3.txt):")
    boxed([l for l in out3 if l.startswith("collecting")] + ["..."] + summary3)
    para("La única advertencia es de deprecación de la librería de pruebas (Starlette/httpx) y no afecta los resultados. "
         "Los tiempos medidos con curl contra el servidor local fueron todos menores a 10 ms (RNF-02 exige menos de 1 s):")
    tiempos = [l for l in read_ev("tiempos_respuesta.txt") if l.startswith(("GET", "POST"))]
    table(["Petición", "HTTP", "Tiempo (s)"],
          [[re.sub(r"\?.*", "?…", l.split("  HTTP")[0]), l.split("HTTP ")[1].split()[0], l.split()[-1].rstrip("s")]
           for l in tiempos], [10.5, 2, 3.5], "Tiempos de respuesta medidos (docs/evidencias/tiempos_respuesta.txt)")

    # ---------------- Parte 4
    heading("Parte 4: Mantenimiento y revisión del proyecto", 2)
    heading("4.1 Solicitud de cambio y análisis", 3)
    para("El cliente (simulado) pidió la solicitud **SC-01**: «premiar a los clientes frecuentes: que ganen puntos cada "
         "vez que vienen, que tengan niveles y que puedan canjear los puntos por un descuento». Tras analizarla se acordó:")
    table(["Aspecto", "Decisión"], [
        ["Cuándo se ganan puntos", "Cuando la reserva se completa (el cliente asistió); lo marca el personal."],
        ["Puntos por visita", "10 puntos, una sola vez por reserva."],
        ["Niveles", "Bronce 0–49, Plata 50–99, Oro ≥ 100, según los puntos acumulados históricos (no baja al canjear)."],
        ["Beneficio", "50 puntos de saldo = cupón de 10 % de descuento con código único."],
        ["Avisos", "Notificación al ganar puntos (y al subir de nivel) y al canjear."],
        ["Seguridad", "Solo el personal, con una clave (cabecera X-Staff-Key), puede marcar asistencia."],
    ], [4.5, 11.5], "Acuerdos de la solicitud de cambio SC-01")
    table(["Elemento", "Impacto"], [
        ["Requisitos", "Nuevos RF-10 a RF-14, RNF-08 y RS-07; RF-09 ampliado"],
        ["Modelo de datos", "Customer + points y lifetime_points; nueva RewardTransaction; estado COMPLETED; tipos REWARD y REDEMPTION; Notification.reservation_id opcional"],
        ["BD existente", "Migración automática e idempotente (app/migrations.py)"],
        ["Servicios y API", "Nuevo RewardService; NotificationService.send(); 3 endpoints nuevos"],
        ["Frontend", "Panel «Programa Clientes Frecuentes» en Mis reservas"],
        ["Pruebas", "12 pruebas nuevas + regresión de las 29 existentes"],
    ], [3.5, 12.5], "Análisis de impacto del cambio")
    heading("4.2 Documento de requisitos actualizado (ERS v1.1)", 3)
    table(["Versión", "Fecha", "Descripción"], [
        ["1.0", "14/10/2026", "Línea base: RF-01 a RF-09, RNF-01 a RNF-07, RS-01 a RS-06."],
        ["1.1", "26/10/2026", "SC-01 recompensas: RF-10 a RF-14, RNF-08, RS-07; RF-09 ampliado; estado COMPLETED."],
    ], [2, 3, 11], "Historial de cambios de la ERS")
    table(["ID", "Requisito nuevo (v1.1)", "Prioridad"], [
        ["RF-10", "El personal marca como completada una reserva confirmada cuya hora de inicio ya pasó.", "Alta"],
        ["RF-11", "Al completarse, el cliente recibe 10 puntos una sola vez y se registra el movimiento.", "Alta"],
        ["RF-12", "Se asigna un nivel (Bronce, Plata, Oro) según los puntos acumulados.", "Media"],
        ["RF-13", "El cliente consulta su saldo, nivel, puntos faltantes e historial.", "Media"],
        ["RF-14", "El cliente canjea 50 puntos por un cupón de 10 % de descuento.", "Media"],
        ["RNF-08", "Completar reservas exige la clave de personal; sin ella → HTTP 401.", "Alta"],
        ["RS-07", "La actualización conserva los datos de una BD v1.0 existente.", "Alta"],
    ], [1.8, 11.7, 2.5], "Requisitos agregados en la versión 1.1")
    para("Se agregaron los criterios CA-10 a CA-15 (completar suma 10 puntos; no se suma dos veces; subida a Plata con "
         "notificación; canje con saldo insuficiente → 422; canje genera cupón sin bajar el nivel; migración sin pérdida "
         "de datos) y tres endpoints: POST /api/reservations/{code}/complete, GET /api/customers/{email}/rewards y "
         "POST /api/customers/{email}/rewards/redeem.")
    heading("4.3 Diseño actualizado (UML v1.1)", 3)
    para(f"En la {next_fig()} los elementos nuevos aparecen resaltados en amarillo y los atributos o valores agregados "
         "están marcados con «(v1.1)». La arquitectura en capas no cambió: la funcionalidad se agregó como un servicio "
         "y un router nuevos, sin modificar ReservationService.")
    figure(DIAG / "clases_v1_1.png", "Diagrama UML de clases actualizado (v1.1)", max_h_cm=17)
    figure(DIAG / "secuencia_completar_reserva.png", "Diagrama UML de secuencia v1.1: completar reserva y otorgar puntos", max_h_cm=17)
    heading("4.4 Implementación del cambio", 3)
    table(["Archivo", "Tipo", "Descripción"], [
        ["app/models.py", "Modificado", "Columnas de puntos, entidad RewardTransaction, estados y tipos nuevos"],
        ["app/services/rewards.py", "Nuevo", "Reglas de puntos, niveles y canje"],
        ["app/services/notifications.py", "Modificado", "Método send() para avisos sin reserva asociada"],
        ["app/migrations.py", "Nuevo", "Migración v1.0 → v1.1 (ALTER y reconstrucción de notifications)"],
        ["app/routers/rewards.py", "Nuevo", "3 endpoints; clave de personal con secrets.compare_digest"],
        ["frontend/*", "Modificado", "Panel de recompensas: nivel, barra de progreso, historial y canje"],
    ], [5.3, 2.4, 8.3], "Archivos afectados por el cambio")
    para("La migración se probó sobre la base de datos real de la demostración de la Parte 3 (docs/evidencias/migracion_bd_v1_a_v1_1.txt):")
    boxed([l for l in read_ev("migracion_bd_v1_a_v1_1.txt") if l.startswith(("ANTES", "[migración]", "DESPUÉS"))])
    para("Para la demostración, el personal completó por la API cinco reservas históricas del cliente (HIST0001 a HIST0005, "
         "insertadas directamente en la BD de demo porque la API solo permite crear reservas futuras). Sin clave se obtuvo "
         "HTTP 401; con clave, cada reserva sumó 10 puntos; en la quinta el cliente subió a Plata; y un segundo intento "
         f"sobre la misma reserva devolvió 409 (docs/evidencias/demo_recompensas_api.txt). Las figuras {fig_n + 1} a {fig_n + 3} muestran el resultado en la interfaz.")
    figure(EV / "app_09_recompensas_plata.png", "Panel de recompensas: nivel Plata con 50 puntos y canje habilitado", width_cm=13)
    figure(EV / "app_10_reserva_completada_notificacion.png", "Reserva completada y notificación de subida de nivel BRONCE → PLATA", width_cm=13)
    figure(EV / "app_11_canje_cupon.png", "Canje de 50 puntos: cupón DESC10-8WJGPM, saldo 0 y nivel Plata conservado", max_h_cm=14)
    heading("4.5 Pruebas de regresión", 3)
    para("Se volvió a ejecutar **sin modificaciones** toda la suite de la versión 1.0 (29 pruebas) y se agregaron 12 pruebas "
         "nuevas en test_rewards.py. Las pruebas que dependen del paso del tiempo reemplazan el reloj del servicio con "
         "monkeypatch después de crear las reservas.")
    table(["ID", "Descripción", "Criterio", "Resultado"], [
        ["TP-28", "Niveles y puntos faltantes en los límites (0, 49, 50, 99, 100)", "RF-12", "PASSED"],
        ["TP-29", "Completar otorga 10 puntos, transacción EARN y notificación REWARD", "CA-10", "PASSED"],
        ["TP-30", "No se completa una reserva que aún no inicia", "RF-10", "PASSED"],
        ["TP-31", "No se otorgan puntos dos veces", "CA-11", "PASSED"],
        ["TP-32", "Una reserva cancelada no suma puntos", "RF-11", "PASSED"],
        ["TP-33", "Sube a Plata con 5 visitas y a Oro con 10", "CA-12", "PASSED"],
        ["TP-34", "Canje con saldo insuficiente rechazado", "CA-13", "PASSED"],
        ["TP-35", "Canje genera cupón, saldo 0, nivel conservado", "CA-14", "PASSED"],
        ["TP-36", "Una reserva completada no se modifica ni se cancela", "RF-05/06", "PASSED"],
        ["TP-37", "API: completar sin clave o con clave errónea → 401", "RNF-08", "PASSED"],
        ["TP-38", "API: resumen, canje 422 → 200, cliente inexistente 404", "RF-13, RF-14", "PASSED"],
        ["TP-39", "Migración de una BD con el esquema real v1.0, idempotente", "CA-15", "PASSED"],
    ], [1.6, 9.6, 2.6, 2.2], "Casos de prueba nuevos de la versión 1.1")
    out4 = read_ev("pytest_fase4.txt")
    para("Resumen de la salida real de la regresión (docs/evidencias/pytest_fase4.txt):")
    boxed([l for l in out4 if l.startswith("collecting")] + ["..."] + [l for l in out4 if "passed" in l and "=" in l])
    para("**Resultado: 41 de 41 pruebas aprobadas.** Las 29 pruebas de la versión 1.0 siguen pasando, por lo que el "
         "cambio no introdujo regresiones.")
    heading("4.6 Clasificación del mantenimiento", 3)
    table(["Tipo (SWEBOK / ISO/IEC 14764)", "¿Aplica a SC-01?"], [
        ["Correctivo", "No: no se corrigió ningún defecto."],
        ["Adaptativo", "En parte: la migración adapta la BD existente, pero es consecuencia del cambio, no su causa."],
        ["Perfectivo", "Sí, es el tipo principal: agrega funcionalidad nueva pedida por el usuario."],
        ["Preventivo", "Complementario: send() generaliza el notificador y la migración idempotente evita fallos al actualizar."],
    ], [5, 11], "Clasificación del cambio según los tipos de mantenimiento")
    para("Por tanto, el programa de recompensas es **mantenimiento perfectivo**: es una mejora (enhancement) sobre un "
         "sistema que ya funcionaba correctamente.")
    heading("4.7 Revisión y presentación del proyecto", 3)
    para("Se preparó el guion de la presentación final (docs/presentacion_final.md), de 12 a 15 minutos, con este orden:")
    bullets([
        "Planificación: áreas SWEBOK, modelo iterativo-incremental, estimación de 21 h, diagrama de Gantt y riesgos.",
        "Requisitos y diseño: acta, ERS (9 RF, 7 RNF, 6 restricciones), casos de uso, arquitectura, clases y secuencia.",
        "Diseño de interfaces: comparación entre mockups y pantallas reales, con demostración en vivo opcional.",
        "Resultados de pruebas: 29/29 en la v1.0 y 41/41 en la regresión de la v1.1.",
        "Mantenimiento: SC-01, ERS y UML v1.1, migración sin pérdida de datos y clasificación perfectiva.",
    ])

    # ------------------------------------------------------------------ V Cuestionario
    banner("SOLUCIÓN DEL CUESTIONARIO")
    heading("V. Cuestionario", 1)
    q = [
        ("1. Defina el SWEBOK y su importancia en la ingeniería de software. Explique qué es y cómo ayuda a estandarizar el conocimiento en esta área.", [
            "El SWEBOK (Software Engineering Body of Knowledge) es la guía de la IEEE Computer Society que describe el conocimiento generalmente aceptado de la ingeniería de software, organizado en áreas de conocimiento con sus temas, referencias y relación con otras disciplinas. Su versión 3.0 tiene 15 áreas; la 4.0 (2024), 18.",
            "Es importante porque fija **qué** abarca la disciplina y ofrece un **vocabulario común**: un «requisito no funcional» o un «mantenimiento perfectivo» significan lo mismo para todos. Así estandariza el conocimiento, sirve de base para planes de estudio, certificaciones (por ejemplo, de la IEEE) y perfiles profesionales, y permite evaluar si un proyecto cubre todas las áreas necesarias. En este laboratorio se usó como lista de control: cada parte del proyecto corresponde a una o más áreas.",
        ]),
        ("2. Mencione y describa brevemente las áreas de conocimiento que abarca el SWEBOK (al menos cinco).", [
            "**Requisitos de software:** obtener, analizar, especificar y validar las necesidades (en ReservaYa, RF-01 a RF-14).",
            "**Diseño de software:** definir la arquitectura y los componentes (arquitectura en 4 capas y diagramas UML).",
            "**Construcción de software:** codificar, depurar y probar unitariamente (API FastAPI y frontend).",
            "**Pruebas de software:** verificar y validar con casos de prueba (41 pruebas automatizadas).",
            "**Mantenimiento de software:** modificar el software ya entregado (programa de recompensas).",
            "**Gestión de configuración:** controlar versiones y cambios (ERS v1.0 → v1.1 y repositorio Git).",
            "**Gestión de la ingeniería de software:** planificar, estimar y controlar (plan de 21 h y riesgos).",
            "**Proceso de software:** definir y mejorar el ciclo de vida (modelo iterativo-incremental).",
            "**Calidad de software:** asegurar que el producto y el proceso cumplan estándares (criterios de aceptación).",
            "Otras áreas: modelos y métodos, práctica profesional, economía de la ingeniería de software y fundamentos de computación, matemáticos y de ingeniería.",
        ]),
        ("3. ¿Qué es el proceso de desarrollo de software según SWEBOK?", [
            "Según el área *Proceso de Ingeniería de Software*, el proceso es el conjunto de actividades interrelacionadas que transforman entradas (necesidades del cliente) en salidas (software y documentación), junto con los roles, productos de trabajo y recursos que intervienen. SWEBOK no impone un proceso único: cubre su **definición** (modelos de ciclo de vida como cascada, incremental, espiral o ágil), su **implementación y gestión**, su **evaluación** (por ejemplo, con CMMI o ISO/IEC 15504) y su **medición y mejora**.",
            "En este proyecto el proceso se definió como iterativo-incremental, con fases de planificación, requisitos, diseño, construcción, pruebas y mantenimiento, cada una con entregables verificables.",
        ]),
        ("4. Diferencia entre «requisitos funcionales» y «requisitos no funcionales». Proporcione ejemplos.", [
            "Un **requisito funcional** indica **qué hace** el sistema: un servicio, una reacción a una entrada o un comportamiento. Un **requisito no funcional** indica **cómo** debe hacerlo o bajo qué restricciones: calidad, rendimiento, seguridad, usabilidad o portabilidad. Los funcionales suelen afectar a un componente concreto; los no funcionales, al sistema completo.",
            "Ejemplos funcionales de ReservaYa: RF-03 «crear una reserva asignando automáticamente la mesa más pequeña disponible» y RF-06 «cancelar una reserva confirmada».",
            "Ejemplos no funcionales: RNF-02 «la API responde en menos de 1 s» (se midió menos de 10 ms), RNF-03 «no deben existir reservas solapadas en una mesa» y RNF-04 «modificar o cancelar exige el código y el correo del titular».",
        ]),
        ("5. ¿Qué papel desempeña el diseño de software en el ciclo de vida del desarrollo según SWEBOK?", [
            "El diseño es el puente entre el **qué** (requisitos) y el **cómo** (construcción). SWEBOK lo divide en diseño **arquitectónico** (descomposición en componentes y sus interacciones) y diseño **detallado** (comportamiento interno de cada componente). Sus productos permiten analizar y evaluar la solución antes de programarla, cuando corregir errores es más barato, y guían la construcción y las pruebas.",
            "En ReservaYa, el diseño en capas y el diagrama de clases hicieron que el cambio de la Parte 4 se resolviera agregando un servicio y un router, sin tocar la lógica de reservas. El diagrama de secuencia sirvió como guion de la implementación y de las pruebas del flujo «crear reserva y notificar».",
        ]),
        ("6. Ante requisitos cambiantes de un cliente, ¿qué enfoque de desarrollo recomendaría según SWEBOK y por qué?", [
            "Se recomienda un enfoque **iterativo-incremental o ágil** (por ejemplo, Scrum), no la cascada. SWEBOK reconoce que los requisitos cambian durante el proyecto y que los modelos con iteraciones cortas reducen el riesgo, porque cada incremento se valida con el cliente y los cambios entran en la siguiente iteración sin rehacer fases cerradas.",
            "Prácticas complementarias: gestionar los requisitos con control de versiones y trazabilidad, priorizar el backlog, diseñar con bajo acoplamiento y mantener pruebas automatizadas para la regresión.",
            "Este laboratorio lo demuestra: la solicitud SC-01 (recompensas) se incorporó como la iteración I-4, con ERS v1.1, UML actualizado y 41/41 pruebas aprobadas, sin romper la funcionalidad existente.",
        ]),
        ("7. ¿Qué tipos de mantenimiento existen según el SWEBOK? Describa al menos dos y dé ejemplos.", [
            "SWEBOK, siguiendo ISO/IEC 14764, distingue cuatro tipos:",
            "**Correctivo:** repara defectos descubiertos después de la entrega. Ejemplo: si se detectara que el sistema permite reservar una mesa ya ocupada, corregir la consulta de solapamiento.",
            "**Adaptativo:** ajusta el software a cambios del entorno. Ejemplo: migrar de SQLite a PostgreSQL o adaptarse a una nueva versión de Python.",
            "**Perfectivo:** agrega o mejora funcionalidades a pedido del usuario. Ejemplo: el **programa de recompensas** de la Parte 4.",
            "**Preventivo:** anticipa problemas futuros (refactorización, documentación, actualización de librerías). Ejemplo: reemplazar el TestClient basado en httpx por la alternativa recomendada, antes de que la advertencia de deprecación se convierta en error.",
        ]),
    ]
    for question, answers in q:
        heading(question.replace("*", ""), 3)
        for a in answers:
            para(a.replace("*Proceso de Ingeniería de Software*", "Proceso de Ingeniería de Software"))

    # ------------------------------------------------------------------ Conclusiones
    banner("CONCLUSIONES")
    heading("Conclusiones", 1)
    bullets([
        "SWEBOK sirvió como mapa del proyecto: cada área de conocimiento se tradujo en entregables verificables (plan, ERS, UML, código, pruebas y documento de mantenimiento) y no quedó ninguna fase del ciclo de vida sin cubrir.",
        "El modelo iterativo-incremental fue adecuado: el cambio de requisitos de la Parte 4 se incorporó como un incremento más, sin rehacer las fases anteriores.",
        "Especificar requisitos verificables (RF, RNF, restricciones y criterios Dado/Cuando/Entonces) permitió convertir cada requisito en casos de prueba trazables (TP-01 a TP-39).",
        "La arquitectura en capas redujo el impacto del cambio: el programa de recompensas solo requirió un servicio, un router y una migración, y no modificó la lógica de reservas.",
        "Las pruebas automatizadas fueron la red de seguridad del mantenimiento: la regresión (41/41 aprobadas) confirmó que el cambio perfectivo no dañó la funcionalidad existente.",
        "El mantenimiento no consiste solo en código: también exige actualizar requisitos, diseño y datos. La migración sin pérdida de una base de datos real lo demostró.",
    ])
    heading("Recomendaciones", 1)
    bullets([
        "Reemplazar las notificaciones simuladas por un envío real (SMTP o un servicio de correo), manteniendo la interfaz de NotificationService.",
        "Agregar autenticación de clientes y personal (por ejemplo, con tokens JWT) en lugar de la clave compartida de demostración.",
        "Usar una herramienta de migraciones como Alembic y una base de datos cliente-servidor (PostgreSQL) para producción.",
        "Integrar las pruebas en un flujo de integración continua (por ejemplo, GitHub Actions) y medir la cobertura de código.",
        "Validar la interfaz con usuarios reales y realizar pruebas de carga antes de un despliegue en producción.",
    ])

    # ------------------------------------------------------------------ Retroalimentación (plantilla)
    _append(fit_template_table(copy.deepcopy(retro_proto)))
    para("")

    # ------------------------------------------------------------------ Bibliografía
    banner("REFERENCIAS Y BIBLIOGRAFÍA")
    heading("VI. Bibliografía", 1)
    refs = [
        "Bourque, P., & Fairley, R. E. (Eds.). (2014). *Guide to the Software Engineering Body of Knowledge (SWEBOK Guide), Version 3.0*. IEEE Computer Society.",
        "IEEE. (1998). *IEEE Std 830-1998: IEEE recommended practice for software requirements specifications*. IEEE.",
        "ISO/IEC/IEEE. (2018). *ISO/IEC/IEEE 29148:2018 Systems and software engineering — Life cycle processes — Requirements engineering*. ISO.",
        "ISO/IEC/IEEE. (2022). *ISO/IEC/IEEE 14764:2022 Software engineering — Software life cycle processes — Maintenance*. ISO.",
        "Pressman, R. S., & Maxim, B. R. (2019). *Software engineering: A practitioner's approach* (9th ed.). McGraw-Hill Education.",
        "Royce, W. W. (1970). Managing the development of large software systems. *Proceedings of IEEE WESCON*, 26, 1–9.",
        "Sommerville, I. (2016). *Software engineering* (10th ed.). Pearson.",
        "Washizaki, H. (Ed.). (2024). *Guide to the Software Engineering Body of Knowledge (SWEBOK Guide), Version 4.0*. IEEE Computer Society.",
    ]
    for ref in refs:
        p = para("")
        p.paragraph_format.left_indent = Cm(1.27)
        p.paragraph_format.first_line_indent = Cm(-1.27)
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for i, chunk in enumerate(re.split(r"\*(.+?)\*", ref)):
            if chunk:
                r = p.add_run(chunk)
                r.italic = (i % 2 == 1)

    # ------------------------------------------------------------------ Anexos
    page_break()
    heading("Anexos", 1)
    heading("Anexo A. Repositorio del proyecto", 3)
    para(f"Enlace al repositorio de GitHub: **{PENDING} (URL del repositorio)**")
    heading("Anexo B. Estructura del repositorio", 3)
    boxed([
        "lab04/",
        "├── README.md               instalación y ejecución",
        "├── informe_04.md           guía original del laboratorio",
        "├── instrucciones.md",
        "├── Informe_Lab04.docx      este informe",
        "├── backend/",
        "│   ├── app/                main, models, schemas, migrations, seed, routers/, services/",
        "│   ├── tests/              test_reservation_service.py, test_api.py, test_rewards.py",
        "│   ├── requirements.txt",
        "│   └── pytest.ini",
        "├── frontend/               index.html, styles.css, app.js",
        "├── mockups/                01_reservar, 02_confirmacion, 03_mis_reservas (HTML)",
        "└── docs/",
        "    ├── fase1_planificacion.md … fase4_mantenimiento.md, presentacion_final.md",
        "    ├── generar_informe.py  genera este documento",
        "    ├── diagramas/          .puml + .png (Gantt, casos de uso, arquitectura, clases, secuencias)",
        "    └── evidencias/         capturas, pytest_fase3.txt, pytest_fase4.txt, logs",
    ])
    heading("Anexo C. Ejecución del sistema", 3)
    boxed([
        "python -m venv .venv",
        "source .venv/bin/activate        (Windows: .venv\\Scripts\\activate)",
        "pip install -r backend/requirements.txt",
        "cd backend",
        "uvicorn app.main:app --reload     ->  http://127.0.0.1:8000/  y  /docs",
        "python -m pytest -v               ->  41 passed",
    ])


# --------------------------------------------------------------------------- ensamblado
# 1) pasada en seco para conocer los títulos del índice
_real_append = _append


def dry_run():
    global fig_n, tab_n, headings
    saved = (fig_n, tab_n)
    before = set(map(id, body.iterchildren()))
    globals()["_append"] = lambda el: el
    contenido()
    globals()["_append"] = _real_append
    for el in list(body.iterchildren()):  # add_paragraph/add_table ya insertan en el cuerpo
        if id(el) not in before and el is not sect_pr:
            body.remove(el)
    fig_n, tab_n = saved
    found = list(headings)
    headings.clear()
    return found


ALL_HEADINGS = dry_run()

# 2) índice
page_break()
p = para("ÍNDICE", align=WD_ALIGN_PARAGRAPH.CENTER, bold_all=True)
toc()
page_break()
# 3) contenido
contenido()

# --------------------------------------------------------------------------- configuración y guardado
settings = doc.settings.element
uf = OxmlElement("w:updateFields")
uf.set(qn("w:val"), "true")
settings.append(uf)
doc.save(str(OUT))


def normalize_fonts(path):
    """Fuerza Calibri 12 en TODAS las partes XML (cuerpo, estilos, encabezado, numeración, pies)."""
    tmp = path.with_suffix(".tmp")
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.startswith("word/") and item.filename.endswith(".xml") and "theme" not in item.filename:
                x = data.decode("utf-8")
                x = re.sub(r"<w:rFonts\b[^>]*/>",
                           f'<w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}" w:eastAsia="{FONT}"/>', x)
                x = re.sub(r'<w:sz w:val="\d+"\s*/>', '<w:sz w:val="24"/>', x)
                x = re.sub(r'<w:szCs w:val="\d+"\s*/>', '<w:szCs w:val="24"/>', x)
                if item.filename == "word/styles.xml":
                    x = re.sub(r"<w:docDefaults>.*?</w:docDefaults>",
                               f'<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" '
                               f'w:cs="{FONT}" w:eastAsia="{FONT}"/><w:sz w:val="24"/><w:szCs w:val="24"/>'
                               '<w:lang w:val="es-PE"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr>'
                               '<w:spacing w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>',
                               x, flags=re.S)
                data = x.encode("utf-8")
            zout.writestr(item, data)
    tmp.replace(path)


normalize_fonts(OUT)
print(f"OK: {OUT.name} · figuras={fig_n} tablas={tab_n} títulos={len(ALL_HEADINGS)}")
