"""Verifica que TODO el informe use Calibri 12 (checklist del Agente B).

Revisa: docDefaults, estilos, cada run del cuerpo (incluye tablas anidadas), encabezados,
pies de página y numeración; además, a nivel XML, cualquier w:rFonts / w:sz de todas las partes.
Uso: python docs/verificar_formato.py [Informe_Lab04.docx]
"""
import re
import sys
import zipfile
from pathlib import Path

import docx
from docx.shared import Pt

path = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "Informe_Lab04.docx")
errors = []

# 1) Nivel XML: todas las partes de texto de Word
with zipfile.ZipFile(path) as z:
    for name in z.namelist():
        if not (name.startswith("word/") and name.endswith(".xml")) or "theme" in name:
            continue
        x = z.read(name).decode("utf-8")
        for rf in re.findall(r"<w:rFonts\b[^>]*>", x):
            attrs = dict(re.findall(r'w:(\w+)="([^"]*)"', rf))
            if any(k.endswith("Theme") for k in attrs) or any(v != "Calibri" for v in attrs.values()):
                errors.append(f"{name}: fuente distinta {rf}")
        for tag, val in re.findall(r'<w:(sz|szCs) w:val="(\d+)"', x):
            if val != "24":
                errors.append(f"{name}: tamaño {int(val) / 2} pt en w:{tag}")
        if name == "word/styles.xml":
            dd = re.search(r"<w:docDefaults>.*?</w:docDefaults>", x, re.S).group(0)
            if 'w:ascii="Calibri"' not in dd or '<w:sz w:val="24"/>' not in dd:
                errors.append("docDefaults no es Calibri 12")

# 2) Nivel python-docx: fuente efectiva de cada run (run -> estilo de párrafo -> por defecto)
d = docx.Document(str(path))


def effective(run, para):
    name, size = run.font.name, run.font.size
    st = para.style
    while st is not None and (name is None or size is None):
        name = name or st.font.name
        size = size or st.font.size
        st = st.base_style
    return name or "Calibri", size or Pt(12)  # docDefaults ya verificado como Calibri 12


def walk(paragraphs, tables, where):
    n = 0
    for p in paragraphs:
        for r in p.runs:
            n += 1
            name, size = effective(r, p)
            if name != "Calibri" or size != Pt(12):
                errors.append(f"{where}: run '{r.text[:30]}' -> {name} {size.pt if size else None}")
    for t in tables:
        for row in t.rows:
            for cell in row.cells:
                n += walk(cell.paragraphs, cell.tables, where + "/tabla")
    return n


total = walk(d.paragraphs, d.tables, "cuerpo")
for i, s in enumerate(d.sections):
    for part, label in ((s.header, "encabezado"), (s.footer, "pie")):
        total += walk(part.paragraphs, part.tables, f"{label} {i}")
for st in d.styles:
    if st.type == 1 and st.font.name not in (None, "Calibri"):
        errors.append(f"estilo {st.name}: {st.font.name}")
    if st.type == 1 and st.font.size not in (None, Pt(12)):
        errors.append(f"estilo {st.name}: {st.font.size.pt} pt")

print(f"Runs revisados: {total}")
if errors:
    print(f"ERRORES ({len(errors)}):")
    print("\n".join(errors[:50]))
    sys.exit(1)
print("OK: todo el documento usa Calibri 12 (cuerpo, tablas, estilos, encabezado, pie y numeración).")
