"""Genera MEMORIA_CALCULO_MUROS.xlsx: predimensionamiento y diseño de muros de contención en voladizo.

Procedimiento: notas 'Muros de Contención' (G. A. Chang Nieto, Diseño de Concreto II, U. del Magdalena),
basadas en Das, Fundamentos de Ingeniería de Cimentaciones, 7a ed., y NSR-10 (B.2.4, Título C).
Unidades: kN, m, kPa, grados; f'c y fy en MPa.
"""
import re
import sys

from openpyxl import Workbook
from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

OUT = sys.argv[1] if len(sys.argv) > 1 else "MEMORIA_CALCULO_MUROS.xlsx"

# ---------------------------------------------------------------- estilos (como la memoria de zapatas)
FONT = "Lucida Bright"
NAVY = "44546A"
BLUE = "1F3864"
f_txt = Font(name=FONT, size=11)
f_b = Font(name=FONT, size=11, bold=True)
f_in = Font(name=FONT, size=11, bold=True, color=BLUE)
f_hdr = Font(name=FONT, size=11, bold=True, italic=True)
f_title = Font(name=FONT, size=14, bold=True, color="FFFFFF")
f_small = Font(name=FONT, size=9, italic=True, color="595959")
fill_in = PatternFill("solid", fgColor="DDDDDD")
fill_title = PatternFill("solid", fgColor=NAVY)
fill_head = PatternFill("solid", fgColor="D6DCE4")
fill_sum = PatternFill("solid", fgColor="E2EFDA")
thin = Side(style="thin", color="000000")
box = Border(left=thin, right=thin, top=thin, bottom=thin)
center = Alignment(horizontal="center", vertical="center", wrap_text=True)
left = Alignment(horizontal="left", vertical="center", wrap_text=True)

N_ROWS = 200  # filas disponibles en INPUTS

# ---------------------------------------------------------------- INPUTS: columnas de la tabla de muros
IN_COLS = [  # (clave, encabezado, unidad, ancho, formato, comentario)
    ("muro", "Muro", "", 10, "@", "Nombre único del muro. La hoja de memoria lo busca por este nombre."),
    ("desc", "Descripción / ubicación", "", 26, "@", None),
    ("H2", "Altura vástago H2", "m", 11, "0.00", "Altura del vástago medida desde la cara superior de la zapata."),
    ("tc", "Corona", "m", 9, "0.00", "Espesor del vástago en la corona (Das: mín. 0.30 m)."),
    ("tb", "Base vástago", "m", 9, "0.00", "Espesor del vástago en su base (Das: ≈ 0.1H)."),
    ("Lp", "Puntera", "m", 9, "0.00", "Longitud de la puntera, desde el borde C hasta la cara frontal del vástago."),
    ("Lt", "Talón", "m", 9, "0.00", "Longitud del talón, desde la cara posterior del vástago."),
    ("hz", "Espesor zapata H3", "m", 10, "0.00", "Espesor de la losa de base (Das: ≈ 0.1H)."),
    ("D", "Prof. desplante D", "m", 10, "0.00", "Profundidad del suelo frente a la puntera (para Pp)."),
    ("alpha", "α relleno", "°", 8, "0.0", "Inclinación del relleno respecto a la horizontal."),
    ("g1", "γ1", "kN/m³", 8, "0.00", "Peso unitario del relleno."),
    ("phi1", "φ'1", "°", 8, "0.0", "Ángulo de fricción efectivo del relleno."),
    ("c1", "c'1", "kPa", 8, "0.0", "Cohesión del relleno. Esta hoja aplica para relleno granular (c'1 = 0)."),
    ("g2", "γ2", "kN/m³", 8, "0.00", "Peso unitario del suelo de fundación."),
    ("phi2", "φ'2", "°", 8, "0.0", "Ángulo de fricción efectivo del suelo de fundación."),
    ("c2", "c'2", "kPa", 8, "0.0", "Cohesión del suelo de fundación."),
    ("qadm", "q adm", "kPa", 9, "0.0", "Capacidad admisible del suelo (estudio de suelos)."),
    ("fc", "f'c", "MPa", 8, "0.0", None),
    ("fy", "fy", "MPa", 8, "0", None),
    ("gc", "γ concreto", "kN/m³", 10, "0.00", "Das usa 23.58 kN/m³; NSR-10 B.3: 24 kN/m³."),
    ("rec", "Recubrimiento al centroide", "m", 12, "0.000", "Distancia de la cara al centroide del acero (d = h - rec)."),
    ("metodo", "Método empuje", "", 11, "@", "Rankine (empuje paralelo al relleno, ángulo α) o Coulomb (fricción muro-suelo δ')."),
    ("delta", "δ' muro", "°", 8, "0.0", "Ángulo de fricción muro-suelo: φ'/2 ≤ δ' ≤ 2φ'/3. Se usa en Coulomb y en sismo."),
    ("Ka_man", "Ka manual (opcional)", "", 11, "0.0000", "Déjelo vacío para calcular Ka. Escriba un valor (p. ej. de tabla) para imponerlo."),
    ("kh", "kh", "", 7, "0.000", "Coeficiente sísmico horizontal (0 = sin análisis sísmico)."),
    ("kv", "kv", "", 7, "0.000", "Coeficiente sísmico vertical."),
    ("D1", "Prof. con dentellón D1", "m", 11, "0.00", "Opcional. Si hay dentellón, profundidad total D1 para Pp; 0 = sin dentellón."),
]
COL = {k: get_column_letter(2 + i) for i, (k, *_r) in enumerate(IN_COLS)}

EXAMPLES = [
    dict(muro="M1", desc="Ejemplo Das 7ed / notas Chang (Ka de tabla 0.3532)", H2=6, tc=0.5, tb=0.7, Lp=0.7, Lt=2.6,
         hz=0.7, D=1.5, alpha=10, g1=18, phi1=30, c1=0, g2=19, phi2=20, c2=40, qadm=300, fc=28, fy=420, gc=23.58,
         rec=0.07, metodo="Rankine", delta=20, Ka_man=0.3532, kh=0, kv=0, D1=0),
    dict(muro="M2", desc="Muro sótano, relleno horizontal, con sismo", H2=4, tc=0.3, tb=0.45, Lp=0.8, Lt=1.85,
         hz=0.45, D=1.0, alpha=0, g1=18, phi1=32, c1=0, g2=18.5, phi2=28, c2=10, qadm=200, fc=28, fy=420, gc=24,
         rec=0.075, metodo="Rankine", delta=21, Ka_man=None, kh=0.15, kv=0, D1=0),
]

BARS = [(3, 9.5, 0.71), (4, 12.7, 1.29), (5, 15.9, 1.99), (6, 19.1, 2.84), (7, 22.2, 3.87), (8, 25.4, 5.10)]


def style_range(ws, rng, font=None, fill=None, border=None, align=None, fmt=None):
    for row in ws[rng]:
        for c in row:
            if font: c.font = font
            if fill: c.fill = fill
            if border: c.border = border
            if align: c.alignment = align
            if fmt: c.number_format = fmt


def build_inputs(wb):
    ws = wb.active
    ws.title = "INPUTS"
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3
    last = get_column_letter(1 + len(IN_COLS))
    ws.merge_cells(f"B2:{last}2")
    ws["B2"] = "DATOS DE ENTRADA — MUROS DE CONTENCIÓN EN VOLADIZO"
    style_range(ws, f"B2:{last}2", font=f_title, fill=fill_title, align=center)
    ws["B3"] = ("Celdas grises = datos editables. Agregue una fila por muro; para cada muro copie una hoja de memoria "
                "(clic derecho → Mover o copiar → Crear una copia) y escriba su nombre en la celda C4.")
    ws.merge_cells(f"B3:{last}3")
    style_range(ws, f"B3:{last}3", font=f_small, align=left)
    ws.row_dimensions[3].height = 30
    ws["B4"] = "Unidades: kN, m, kPa, grados; f'c y fy en MPa. Ejemplo M1 = ejemplo del documento (Das 7ed)."
    ws.merge_cells(f"B4:{last}4")
    style_range(ws, f"B4:{last}4", font=f_small, align=left)
    groups = [("Identificación", "muro", "desc"), ("Geometría (m)", "H2", "alpha"), ("Relleno", "g1", "c1"),
              ("Suelo de fundación", "g2", "qadm"), ("Materiales", "fc", "rec"), ("Empuje y sismo", "metodo", "D1")]
    for name, a, b in groups:
        rng = f"{COL[a]}5:{COL[b]}5"
        ws.merge_cells(rng)
        ws[f"{COL[a]}5"] = name
        style_range(ws, rng, font=f_b, fill=fill_head, border=box, align=center)
    for i, (k, head, unit, width, fmt, note) in enumerate(IN_COLS):
        c = COL[k]
        ws.column_dimensions[c].width = width
        ws[f"{c}6"] = head
        ws[f"{c}7"] = f"({unit})" if unit else ""
        for r in (6, 7):
            ws[f"{c}{r}"].font = f_b
            ws[f"{c}{r}"].border = box
            ws[f"{c}{r}"].alignment = center
        if note:
            ws[f"{c}6"].comment = Comment(note, "Memoria muros")
        for r in range(8, 8 + 30):
            cell = ws[f"{c}{r}"]
            cell.fill = fill_in
            cell.font = f_in
            cell.border = box
            cell.alignment = center
            cell.number_format = fmt
    ws.row_dimensions[6].height = 45
    for r, ex in enumerate(EXAMPLES, start=8):
        for k, v in ex.items():
            if v is not None:
                ws[f"{COL[k]}{r}"] = v
    dv = DataValidation(type="list", formula1='"Rankine,Coulomb"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{COL['metodo']}8:{COL['metodo']}{8 + N_ROWS}")
    ws.freeze_panes = "C8"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    return ws


def build_tablas(wb):
    ws = wb.create_sheet("TABLAS")
    ws.sheet_view.showGridLines = False
    for c, w in zip("ABCDEFG", (3, 12, 14, 14, 4, 40, 30)):
        ws.column_dimensions[c].width = w
    ws.merge_cells("B2:D2")
    ws["B2"] = "BARRAS DE REFUERZO (NSR-10 C.3.5)"
    style_range(ws, "B2:D2", font=f_title, fill=fill_title, align=center)
    for c, h in zip("BCD", ("Barra No.", "Diámetro (mm)", "Área (cm²)")):
        ws[f"{c}4"] = h
    style_range(ws, "B4:D4", font=f_b, fill=fill_head, border=box, align=center)
    for i, (n, d, a) in enumerate(BARS, start=5):
        ws[f"B{i}"], ws[f"C{i}"], ws[f"D{i}"] = n, d, a
        style_range(ws, f"B{i}:D{i}", font=f_txt, border=box, align=center)
        ws[f"D{i}"].number_format = "0.00"
    ws.merge_cells("F2:G2")
    ws["F2"] = "PREDIMENSIONAMIENTO (Das, 7ed)"
    style_range(ws, "F2:G2", font=f_title, fill=fill_title, align=center)
    rows = [("Elemento", "Muro en voladizo / gravedad"),
            ("Corona", "≥ 0.30 m (ambos)"),
            ("Inclinación cara frontal", "≥ 0.02 (ambos)"),
            ("Espesor base vástago", "≈ 0.1H (voladizo)"),
            ("Espesor losa de base", "≈ 0.1H voladizo; 0.12–0.17H gravedad"),
            ("Ancho de base B", "0.5H – 0.7H (ambos)"),
            ("Puntera (gravedad)", "0.12H – 0.17H"),
            ("Profundidad D", "≥ 0.6 m recomendable")]
    for i, (a, b) in enumerate(rows, start=4):
        ws[f"F{i}"], ws[f"G{i}"] = a, b
        style_range(ws, f"F{i}:G{i}", font=f_b if i == 4 else f_txt, border=box, align=left,
                    fill=fill_head if i == 4 else None)
    refs = ["Referencias del procedimiento:",
            "Ka Rankine con relleno inclinado: Das ec. 7.26 (cara posterior vertical θ = 0).",
            "Ka Coulomb: Das ec. 7.25. Kae Mononobe-Okabe: Das ec. 7.42; ubicación de Pae: ec. 7.49.",
            "Volcamiento: Das ec. 8.2–8.4, tabla 8.1. Deslizamiento: ec. 8.11. Presiones: ec. 8.16–8.21.",
            "Combinaciones de carga: NSR-10 B.2.4.2 (1.2D + 1.6H para el diseño estructural).",
            "Flexión y cortante: NSR-10 Título C (φ = 0.90 flexión, 0.75 cortante; Vc = 0.17λ√f'c b d)."]
    for i, t in enumerate(refs, start=14):
        ws[f"F{i}"] = t
        ws[f"F{i}"].font = f_b if i == 14 else f_small
    return ws


# ---------------------------------------------------------------- hoja de memoria de un muro
BANDS = {"L": ("B", "C", "D", "E"), "M": ("F", "G", "H", "I"), "R": ("J", "K", "L", "M")}


def lk(key):
    c = COL[key]
    return (f'=IFERROR(INDEX(INPUTS!${c}$8:${c}${8 + N_ROWS},MATCH($C$4,INPUTS!$B$8:$B${8 + N_ROWS},0)),"")')


class Sheet:
    def __init__(self, ws):
        self.ws = ws
        self.addr = {}
        self.blocks = []
        self.checks = []

    def block(self, band, row, title, rows):
        self.blocks.append((band, row, title, rows))
        lab, val, unit, chk = BANDS[band]
        for i, r in enumerate(rows, start=row + 1):
            if r.get("key"):
                self.addr[r["key"]] = f"${val}${i}"
            if r.get("ckey"):
                self.addr[r["ckey"]] = f"${chk}${i}"
        return row + len(rows) + 2  # siguiente fila libre

    def sub(self, expr):
        if not isinstance(expr, str):
            return expr
        return re.sub(r"\{(\w+)\}", lambda m: self.addr[m.group(1)], expr)

    def write(self):
        ws = self.ws
        for band, row, title, rows in self.blocks:
            lab, val, unit, chk = BANDS[band]
            ws.merge_cells(f"{lab}{row}:{chk}{row}")
            ws[f"{lab}{row}"] = title
            style_range(ws, f"{lab}{row}:{chk}{row}", font=f_hdr, border=box, align=left)
            for i, r in enumerate(rows, start=row + 1):
                ws[f"{lab}{i}"] = r.get("label", "")
                ws[f"{lab}{i}"].font = f_txt
                ws[f"{lab}{i}"].alignment = Alignment(horizontal="center", vertical="center", shrink_to_fit=True)
                kind = r.get("kind", "calc")
                if "expr" in r:
                    c = ws[f"{val}{i}"]
                    c.value = self.sub(r["expr"])
                    c.number_format = r.get("fmt", "0.00")
                    c.alignment = center
                    c.font = {"in": f_in, "lk": f_in, "calc": f_txt, "key": f_b}[kind]
                    if kind == "in":
                        c.fill = fill_in
                    if r.get("note"):
                        c.comment = Comment(r["note"], "Memoria muros")
                if r.get("span"):  # valor de texto largo ocupa valor+unidad+chequeo
                    ws.merge_cells(f"{val}{i}:{chk}{i}")
                if not r.get("span"):
                    ws[f"{unit}{i}"] = r.get("unit", "")
                    ws[f"{unit}{i}"].font = f_txt
                    ws[f"{unit}{i}"].alignment = center
                if "check" in r:
                    c = ws[f"{chk}{i}"]
                    c.value = self.sub(r["check"])
                    c.font = f_b
                    c.alignment = center
                    self.checks.append(f"{chk}{i}")
            # marco del bloque
            last = row + len(rows)
            for rr in range(row, last + 1):
                for cc in (lab, val, unit, chk):
                    cell = ws[f"{cc}{rr}"]
                    b = cell.border
                    cell.border = Border(left=thin if cc == lab else b.left, right=thin if cc == chk else b.right,
                                         top=thin if rr == row else b.top, bottom=thin if rr == last else b.bottom)


def R(expr):  # alias corto
    return expr


def build_wall(wb, name):
    ws = wb.create_sheet(name)
    ws.sheet_view.showGridLines = False
    widths = {"A": 2, "B": 26, "C": 22, "D": 11, "E": 14, "F": 24, "G": 13, "H": 11, "I": 14,
              "J": 26, "K": 13, "L": 12, "M": 16}
    for c, w in widths.items():
        ws.column_dimensions[c].width = w
    ws.merge_cells("B2:M2")
    ws["B2"] = "MEMORIA DE CÁLCULO — MURO DE CONTENCIÓN EN VOLADIZO"
    style_range(ws, "B2:M2", font=f_title, fill=fill_title, align=center)
    ws.row_dimensions[2].height = 24
    ws["B4"], ws["C4"] = "MURO:", name
    ws["B5"] = "Descripción:"
    ws["C5"] = lk("desc")
    ws.merge_cells("C5:I5")
    for c in ("B4", "B5"):
        ws[c].font = Font(name=FONT, size=12, bold=True)
        ws[c].alignment = Alignment(horizontal="right")
    ws["C4"].font, ws["C4"].fill, ws["C4"].border, ws["C4"].alignment = f_in, fill_in, box, center
    ws["C4"].comment = Comment("Nombre del muro tal como aparece en la hoja INPUTS.", "Memoria muros")
    ws["C5"].font = f_txt
    ws["J4"] = "Celdas grises = editables · Azul = viene de INPUTS · Negro = cálculo"
    ws["J4"].font = f_small
    ws["J5"] = "Procedimiento: Das 7ed (cap. 7–8) y notas de clase Muros de Contención; NSR-10."
    ws["J5"].font = f_small

    S = Sheet(ws)
    RAD = "RADIANS"
    # ---- 1. Geometría
    r = S.block("L", 7, "1. Geometría adoptada", [
        dict(key="H2", label="H2 (vástago)", expr=lk("H2"), unit="m", kind="lk"),
        dict(key="tc", label="Corona", expr=lk("tc"), unit="m", kind="lk"),
        dict(key="tb", label="Base del vástago", expr=lk("tb"), unit="m", kind="lk"),
        dict(key="Lp", label="Puntera", expr=lk("Lp"), unit="m", kind="lk"),
        dict(key="Lt", label="Talón", expr=lk("Lt"), unit="m", kind="lk"),
        dict(key="hz", label="H3 (espesor zapata)", expr=lk("hz"), unit="m", kind="lk"),
        dict(key="D", label="D (desplante)", expr=lk("D"), unit="m", kind="lk"),
        dict(key="alpha", label="α (relleno)", expr=lk("alpha"), unit="°", kind="lk", fmt="0.0"),
        dict(key="B", label="B = puntera + base + talón", expr="={Lp}+{tb}+{Lt}", unit="m"),
        dict(key="H", label="H = H2 + H3", expr="={H2}+{hz}", unit="m"),
        dict(key="H1", label="H1 = talón·tan α", expr=f"={{Lt}}*TAN({RAD}({{alpha}}))", unit="m", fmt="0.000"),
        dict(key="Hp", label="H' = H1 + H2 + H3", expr="={H1}+{H2}+{hz}", unit="m", fmt="0.000", kind="key"),
    ])
    # ---- 6. Predimensionamiento (debajo de geometría)
    S.block("L", r, "5. Predimensionamiento (Das) — recomendado vs adoptado", [
        dict(label="Corona ≥ 0.30 m", expr="=0.3", unit="", fmt="0.00", check='=IF({tc}>=0.3,"OK","REVISAR")'),
        dict(label="Base vástago ≈ 0.1H", expr="=0.1*{H}", fmt="0.00", check='=IF({tb}>=0.1*{H}-0.005,"OK","REVISAR")'),
        dict(label="Losa base ≈ 0.1H", expr="=0.1*{H}", fmt="0.00", check='=IF({hz}>=0.1*{H}-0.005,"OK","REVISAR")'),
        dict(label="B mínimo = 0.5H", expr="=0.5*{H}", fmt="0.00", check='=IF({B}>=0.5*{H},"OK","REVISAR")'),
        dict(label="B máximo = 0.7H", expr="=0.7*{H}", fmt="0.00", check='=IF({B}<=0.7*{H},"OK","REVISAR")'),
        dict(key="batter", label="Inclinación cara (≥ 0.02)", expr="=({tb}-{tc})/{H2}", fmt="0.000",
             check='=IF({batter}>=0.02,"OK","REVISAR")'),
    ])
    # ---- 2/3. Suelos
    r = S.block("M", 7, "2. Relleno (suelo 1)", [
        dict(key="g1", label="γ1", expr=lk("g1"), unit="kN/m³", kind="lk"),
        dict(key="phi1", label="φ'1", expr=lk("phi1"), unit="°", kind="lk", fmt="0.0"),
        dict(key="c1", label="c'1", expr=lk("c1"), unit="kPa", kind="lk", fmt="0.0",
             check='=IF({c1}=0,"OK","NO CUMPLE")'),
    ])
    r = S.block("M", r, "3. Suelo de fundación (suelo 2)", [
        dict(key="g2", label="γ2", expr=lk("g2"), unit="kN/m³", kind="lk"),
        dict(key="phi2", label="φ'2", expr=lk("phi2"), unit="°", kind="lk", fmt="0.0"),
        dict(key="c2", label="c'2", expr=lk("c2"), unit="kPa", kind="lk", fmt="0.0"),
        dict(key="qadm", label="q admisible", expr=lk("qadm"), unit="kPa", kind="lk", fmt="0.0"),
        dict(key="D1", label="D1 con dentellón (0 = no)", expr=lk("D1"), unit="m", kind="lk"),
    ])
    mid_next = r
    # ---- 4. Materiales y factores
    r = S.block("R", 7, "4. Materiales", [
        dict(key="fc", label="f'c", expr=lk("fc"), unit="MPa", kind="lk", fmt="0.0"),
        dict(key="fy", label="fy", expr=lk("fy"), unit="MPa", kind="lk", fmt="0"),
        dict(key="gc", label="γ concreto", expr=lk("gc"), unit="kN/m³", kind="lk"),
        dict(key="rec", label="Recubrimiento (a centroide)", expr=lk("rec"), unit="m", kind="lk", fmt="0.000"),
        dict(key="lam", label="λ", expr=1.0, kind="in", note="1.0 concreto de peso normal."),
    ])
    r = S.block("R", r, "4.1 Factores y requisitos", [
        dict(key="k1", label="k1 (δ' = k1·φ'2)", expr="=2/3", kind="in", fmt="0.000",
             note="Das: k1 y k2 entre 1/2 y 2/3."),
        dict(key="k2", label="k2 (c'a = k2·c'2)", expr="=2/3", kind="in", fmt="0.000"),
        dict(key="FSv", label="FS volcamiento mín.", expr=2.0, kind="in", note="Documento: entre 2 y 3."),
        dict(key="FSd", label="FS deslizamiento mín.", expr=1.5, kind="in"),
        dict(key="fD", label="Factor carga muerta (D)", expr=1.2, kind="in", note="NSR-10 B.2.4-2: 1.2D + 1.6H."),
        dict(key="fH", label="Factor empuje / suelo (H)", expr=1.6, kind="in"),
        dict(key="phif", label="φ flexión", expr=0.9, kind="in"),
        dict(key="phiv", label="φ cortante", expr=0.75, kind="in"),
        dict(key="rhomin", label="ρ mínima", expr=0.0018, kind="in", fmt="0.0000",
             note="El documento usa 0.0018 sobre b·d. Verifique también C.7.12 / C.14 de la NSR-10."),
        dict(key="FSvs", label="FS volc. mín. (sismo)", expr=1.5, kind="in",
             note="Valor usual para condición sísmica; confirme con el docente / NSR-10 Título H."),
        dict(key="FSds", label="FS desl. mín. (sismo)", expr=1.1, kind="in",
             note="Valor usual para condición sísmica; confirme con el docente / NSR-10 Título H."),
    ])
    right_next = r
    # ---- 6. Empuje activo (columna central)
    cos_a, phi = f"{RAD}({{alpha}})", f"{RAD}({{phi1}})"
    r = S.block("M", mid_next, "6. Empuje activo de tierras", [
        dict(key="metodo", label="Método", expr=lk("metodo"), kind="lk", fmt="@"),
        dict(key="delta", label="δ' (muro-suelo)", expr=lk("delta"), unit="°", kind="lk", fmt="0.0"),
        dict(key="Kar", label="Ka Rankine (ec. 7.26)",
             expr=(f"=IFERROR(COS({cos_a})*(COS({cos_a})-SQRT(COS({cos_a})^2-COS({phi})^2))/"
                   f"(COS({cos_a})+SQRT(COS({cos_a})^2-COS({phi})^2)),\"α > φ'\")"), fmt="0.0000"),
        dict(key="Kac", label="Ka Coulomb (ec. 7.25, β=90°)",
             expr=(f"=IFERROR(COS({phi})^2/(COS({RAD}({{delta}}))*(1+SQRT(SIN({phi}+{RAD}({{delta}}))*"
                   f"SIN({phi}-{cos_a})/(COS({RAD}({{delta}}))*COS({cos_a}))))^2),\"α > φ'\")"), fmt="0.0000"),
        dict(key="Kam", label="Ka manual (INPUTS)", expr=lk("Ka_man"), kind="lk", fmt="0.0000"),
        dict(key="Ka", label="Ka usado", kind="key", fmt="0.0000",
             expr='=IF(N({Kam})>0,{Kam},IF({metodo}="Coulomb",{Kac},{Kar}))'),
        dict(key="ang", label="Inclinación de Pa", unit="°", fmt="0.0",
             expr='=IF({metodo}="Coulomb",{delta},{alpha})'),
        dict(key="Pa", label="Pa = ½ γ1 H'² Ka", expr="=0.5*{g1}*{Hp}^2*{Ka}", unit="kN/m", kind="key"),
        dict(key="Pv", label="Pv = Pa sen(ángulo)", expr=f"={{Pa}}*SIN({RAD}({{ang}}))", unit="kN/m"),
        dict(key="Ph", label="Ph = Pa cos(ángulo)", expr=f"={{Pa}}*COS({RAD}({{ang}}))", unit="kN/m"),
        dict(key="Mo", label="ΣMo = Ph·H'/3 (ec. 8.3)", expr="={Ph}*{Hp}/3", unit="kN·m/m", kind="key"),
    ])
    top_end = max(r, right_next, 7 + 13 + 2 + 6 + 2)

    # ---- 7. Tabla 8.1 (ancho completo)
    t0 = top_end + 1
    ws.merge_cells(f"B{t0}:M{t0}")
    ws[f"B{t0}"] = "7. Fuerzas verticales y momento resistente respecto a la punta C (Das, tabla 8.1) — servicio y mayoradas"
    style_range(ws, f"B{t0}:M{t0}", font=f_hdr, border=box, align=left)
    heads = ["Sección", "Descripción", "Área (m²)", "γ (kN/m³)", "W (kN/m)", "Brazo X (m)", "M (kN·m/m)",
             "Factor carga", "Wu (kN/m)", "Mu (kN·m/m)", "", ""]
    for c, h in zip("BCDEFGHIJKLM", heads):
        ws[f"{c}{t0 + 1}"] = h
    style_range(ws, f"B{t0 + 1}:K{t0 + 1}", font=f_b, fill=fill_head, border=box, align=center)
    secs = [
        ("1", "Vástago (rectángulo)", "={tc}*{H2}", "={gc}", "={Lp}+({tb}-{tc})+{tc}/2", "={fD}"),
        ("2", "Vástago (triángulo)", "=0.5*({tb}-{tc})*{H2}", "={gc}", "={Lp}+2/3*({tb}-{tc})", "={fD}"),
        ("3", "Losa de base", "={B}*{hz}", "={gc}", "={B}/2", "={fD}"),
        ("4", "Relleno sobre el talón", "={Lt}*{H2}", "={g1}", "={Lp}+{tb}+{Lt}/2", "={fH}"),
        ("5", "Relleno inclinado (cuña)", "=0.5*{Lt}*{H1}", "={g1}", "={Lp}+{tb}+2/3*{Lt}", "={fH}"),
    ]
    rows_tab = []
    for i, (n, desc, area, gam, x, fac) in enumerate(secs):
        rr = t0 + 2 + i
        rows_tab.append(rr)
        S.addr[f"W{n}"] = f"$F${rr}"
        S.addr[f"Wu{n}"] = f"$J${rr}"
        ws[f"B{rr}"], ws[f"C{rr}"] = int(n), desc
        ws[f"D{rr}"] = S.sub(area)
        ws[f"E{rr}"] = S.sub(gam)
        ws[f"F{rr}"] = f"=D{rr}*E{rr}"
        ws[f"G{rr}"] = S.sub(x)
        ws[f"H{rr}"] = f"=F{rr}*G{rr}"
        ws[f"I{rr}"] = S.sub(fac)
        ws[f"J{rr}"] = f"=F{rr}*I{rr}"
        ws[f"K{rr}"] = f"=H{rr}*I{rr}"
    rv = t0 + 7
    ws[f"B{rv}"], ws[f"C{rv}"] = "Pv", "Componente vertical de Pa"
    ws[f"F{rv}"] = S.sub("={Pv}")
    ws[f"G{rv}"] = S.sub("={B}")
    ws[f"H{rv}"] = f"=F{rv}*G{rv}"
    ws[f"I{rv}"] = S.sub("={fH}")
    ws[f"J{rv}"] = f"=F{rv}*I{rv}"
    ws[f"K{rv}"] = f"=H{rv}*I{rv}"
    S.addr["Mv"] = f"$H${rv}"
    rs = t0 + 8
    ws[f"B{rs}"] = "Σ"
    ws[f"C{rs}"] = "Totales"
    for c in "FHJK":
        ws[f"{c}{rs}"] = f"=SUM({c}{t0 + 2}:{c}{rv})"
    S.addr.update(SV=f"$F${rs}", SMR=f"$H${rs}", SVu=f"$J${rs}", SMRu=f"$K${rs}")
    style_range(ws, f"B{t0 + 2}:K{rs}", font=f_txt, border=box, align=center, fmt="0.00")
    style_range(ws, f"B{rs}:K{rs}", font=f_b, fill=fill_sum)
    for rr in range(t0 + 2, rs + 1):
        ws[f"B{rr}"].number_format = "General"
        ws[f"C{rr}"].alignment = Alignment(horizontal="left", vertical="center", shrink_to_fit=True)
        ws[f"D{rr}"].number_format = "0.000"
    ws[f"L{t0 + 2}"] = "Nota: se desprecia el suelo sobre la puntera (conservador), como en el documento."
    ws.merge_cells(f"L{t0 + 2}:M{t0 + 5}")
    ws[f"L{t0 + 2}"].font, ws[f"L{t0 + 2}"].alignment = f_small, left

    b0 = rs + 2
    # ---- 8. Volcamiento
    rL = S.block("L", b0, "8. Volcamiento (ec. 8.2)", [
        dict(label="ΣMR (incluye Mv)", expr="={SMR}", unit="kN·m/m"),
        dict(label="ΣMo", expr="={Mo}", unit="kN·m/m"),
        dict(key="FSv1", label="Opción 1: ΣMR / ΣMo", expr="={SMR}/{Mo}", kind="key",
             check='=IF({FSv1}>={FSv},"OK","NO CUMPLE")'),
        dict(key="FSv2", label="Opción 2: (ΣMR−Mv)/(ΣMo−Mv)", expr="=({SMR}-{Mv})/({Mo}-{Mv})",
             check='=IF({FSv2}>={FSv},"OK","NO CUMPLE")'),
    ])
    # ---- 9. Deslizamiento
    rM = S.block("M", b0, "9. Deslizamiento (ec. 8.11)", [
        dict(key="Kp", label="Kp = tan²(45 + φ'2/2)", expr=f"=TAN({RAD}(45+{{phi2}}/2))^2", fmt="0.000"),
        dict(key="Dp", label="Profundidad para Pp", expr="=IF(N({D1})>0,{D1},{D})", unit="m"),
        dict(key="Pp", label="Pp = ½Kpγ2D² + 2c'2√Kp D", expr="=0.5*{Kp}*{g2}*{Dp}^2+2*{c2}*SQRT({Kp})*{Dp}",
             unit="kN/m"),
        dict(key="Fr", label="ΣV tan(k1φ'2) + B k2 c'2", expr=f"={{SV}}*TAN({RAD}({{k1}}*{{phi2}}))+{{B}}*{{k2}}*{{c2}}",
             unit="kN/m"),
        dict(key="FSd1", label="FS con Pp", expr="=({Fr}+{Pp})/{Ph}", kind="key",
             check='=IF({FSd1}>={FSd},"OK","NO CUMPLE")'),
        dict(key="FSd2", label="FS sin Pp", expr="={Fr}/{Ph}", check='=IF({FSd2}>={FSd},"OK","NO CUMPLE")'),
    ])
    # ---- 10. Presiones
    rR = S.block("R", b0, "10. Presiones sobre el suelo (ec. 8.16–8.21)", [
        dict(key="e", label="e = B/2 − (ΣMR−ΣMo)/ΣV", expr="={B}/2-({SMR}-{Mo})/{SV}", unit="m", fmt="0.000"),
        dict(key="B6", label="B/6", expr="={B}/6", unit="m", fmt="0.000",
             check='=IF(ABS({e})<={B6},"OK","REDIMENSIONAR")'),
        dict(key="qmax", label="q punta = ΣV/B (1+6e/B)", expr="={SV}/{B}*(1+6*{e}/{B})", unit="kPa", kind="key",
             check='=IF({qmax}<={qadm},"OK","NO CUMPLE")'),
        dict(key="qmin", label="q talón = ΣV/B (1−6e/B)", expr="={SV}/{B}*(1-6*{e}/{B})", unit="kPa",
             check='=IF({qmin}>=0,"OK","NO CUMPLE")'),
        dict(label="q admisible", expr="={qadm}", unit="kPa"),
    ])
    b1 = max(rL, rM, rR)
    # ---- 11. Sismo (Mononobe-Okabe)
    th = f"{RAD}({{thp}})"
    d_ = f"{RAD}({{delta}})"
    rL = S.block("L", b1, "11. Condición sísmica — Mononobe-Okabe (ec. 7.42)", [
        dict(key="kh", label="kh", expr=lk("kh"), kind="lk", fmt="0.000"),
        dict(key="kv", label="kv", expr=lk("kv"), kind="lk", fmt="0.000"),
        dict(key="thp", label="θ' = atan(kh/(1−kv))", expr="=DEGREES(ATAN({kh}/(1-{kv})))", unit="°", fmt="0.00"),
        dict(key="Kae", label="Kae (β = 90°)", fmt="0.0000",
             expr=(f"=IF({{kh}}>0,IFERROR(COS({phi}-{th})^2/(COS({th})*COS({th}+{d_})*(1+SQRT(SIN({phi}+{d_})*"
                   f"SIN({phi}-{th}-{cos_a})/(COS({d_}+{th})*COS({cos_a}))))^2),\"φ' < θ'+α\"),\"No aplica\")")),
        dict(key="Pae", label="Pae = ½γ1H'²(1−kv)Kae", unit="kN/m",
             expr='=IF(ISNUMBER({Kae}),0.5*{g1}*{Hp}^2*(1-{kv})*{Kae},"No aplica")'),
        dict(key="Pas", label="Pa estático (Coulomb, δ')", expr="=0.5*{g1}*{Hp}^2*{Kac}", unit="kN/m"),
        dict(key="zbar", label="z̄ (ec. 7.49)", unit="m", fmt="0.000",
             expr='=IF(ISNUMBER({Pae}),(0.6*{Hp}*({Pae}-{Pas})+{Hp}/3*{Pas})/{Pae},"No aplica")'),
        dict(key="Phe", label="Pae horizontal", unit="kN/m", expr=f'=IF(ISNUMBER({{Pae}}),{{Pae}}*COS({d_}),"No aplica")'),
        dict(key="Pve", label="Pae vertical", unit="kN/m", expr=f'=IF(ISNUMBER({{Pae}}),{{Pae}}*SIN({d_}),"No aplica")'),
        dict(key="FSve", label="FS volcamiento sísmico", fmt="0.00",
             expr='=IF(ISNUMBER({Pae}),({SMR}-{Mv}+{Pve}*{B})/({Phe}*{zbar}),"No aplica")',
             check='=IF(ISNUMBER({FSve}),IF({FSve}>={FSvs},"OK","NO CUMPLE"),"—")'),
        dict(key="FSde", label="FS deslizamiento sísmico", fmt="0.00",
             expr=(f'=IF(ISNUMBER({{Pae}}),(({{SV}}-{{Pv}}+{{Pve}})*TAN({RAD}({{k1}}*{{phi2}}))+{{B}}*{{k2}}*{{c2}}'
                   f'+{{Pp}})/{{Phe}},"No aplica")'),
             check='=IF(ISNUMBER({FSde}),IF({FSde}>={FSds},"OK","NO CUMPLE"),"—")'),
    ])
    # ---- 12. Diseño del vástago
    def flex_rows(p, Mexpr, dexpr, bar_default, bar2_default, hexpr, extra_label=""):
        return [
            dict(key=f"{p}Mu", label=f"Mu {extra_label}".strip(), expr=Mexpr, unit="kN·m/m", kind="key"),
            dict(key=f"{p}d", label="d = h − rec", expr=dexpr, unit="m", fmt="0.000"),
            dict(key=f"{p}Rn", label="Rn = Mu/(φ b d²)", expr=f"=ABS({{{p}Mu}})/1000/({{phif}}*1*{{{p}d}}^2)",
                 unit="MPa", fmt="0.000"),
            dict(key=f"{p}rho", label="ρ requerida", fmt="0.00000",
                 expr=f'=IFERROR(0.85*{{fc}}/{{fy}}*(1-SQRT(1-2*{{{p}Rn}}/(0.85*{{fc}}))),"Sección insuficiente")'),
            dict(key=f"{p}rhod", label="ρ diseño = máx(ρ, ρmín)", expr=f"=MAX({{{p}rho}},{{rhomin}})", fmt="0.00000",
                 check=(f'=IF({{{p}rhod}}<=0.85*IF({{fc}}<=28,0.85,MAX(0.65,0.85-0.05*({{fc}}-28)/7))*{{fc}}/{{fy}}'
                        f'*0.003/0.008,"OK","NO CUMPLE")')),
            dict(key=f"{p}As", label="As = ρ b d", expr=f"={{{p}rhod}}*1*{{{p}d}}*10000", unit="cm²/m"),
            dict(key=f"{p}bar", label="Barra opción 1 (No.)", expr=bar_default, kind="in", fmt="0"),
            dict(key=f"{p}s", label="Separación opción 1", unit="m",
                 expr=(f"=MIN(FLOOR(INDEX(TABLAS!$D$5:$D$10,MATCH({{{p}bar}},TABLAS!$B$5:$B$10,0))/{{{p}As}},0.01),"
                       f"3*{hexpr},0.45)")),
            dict(key=f"{p}txt", label="Refuerzo opción 1", span=True, fmt="@",
                 expr=f'="1 No."&{{{p}bar}}&" @ "&FIXED({{{p}s}},2)&" m"'),
            dict(key=f"{p}bar2", label="Barra opción 2 (No.)", expr=bar2_default, kind="in", fmt="0"),
            dict(key=f"{p}s2", label="Separación opción 2", unit="m",
                 expr=(f"=MIN(FLOOR(INDEX(TABLAS!$D$5:$D$10,MATCH({{{p}bar2}},TABLAS!$B$5:$B$10,0))/{{{p}As}},0.01),"
                       f"3*{hexpr},0.45)")),
            dict(key=f"{p}txt2", label="Refuerzo opción 2", span=True, fmt="@",
                 expr=f'="1 No."&{{{p}bar2}}&" @ "&FIXED({{{p}s2}},2)&" m"'),
        ]

    rM = S.block("M", b1, "12. Diseño del vástago (1.6H, b = 1.0 m)",
                 [dict(key="Vu", label="Vu = 1.6·Ph", expr="={fH}*{Ph}", unit="kN/m")]
                 + flex_rows("v", "={fH}*{Mo}", "={tb}-{rec}", 6, 7, "{tb}", "= 1.6·ΣMo")
                 + [dict(key="vVc", label="Vc = 0.17λ√f'c b d", expr="=0.17*{lam}*SQRT({fc})*1*{vd}*1000",
                         unit="kN/m"),
                    dict(key="vphiVc", label="φVc", expr="={phiv}*{vVc}", unit="kN/m",
                         check='=IF({Vu}<={vphiVc},"OK","NO CUMPLE")')])
    # ---- 13. Diseño de la zapata
    qx = "({qmaxu}-({qmaxu}-{qminu})*{x}/{B})"
    rR = S.block("R", b1, "13. Diseño de la zapata (cargas mayoradas)", [
        dict(label="ΣVu (tabla 7)", expr="={SVu}", unit="kN/m"),
        dict(label="ΣMRu (tabla 7)", expr="={SMRu}", unit="kN·m/m"),
        dict(key="Mou", label="Mou = 1.6·ΣMo", expr="={fH}*{Mo}", unit="kN·m/m"),
        dict(key="eu", label="eu = B/2 − (ΣMRu−Mou)/ΣVu", expr="={B}/2-({SMRu}-{Mou})/{SVu}", unit="m", fmt="0.000"),
        dict(key="qmaxu", label="qu punta", expr="={SVu}/{B}*(1+6*{eu}/{B})", unit="kPa"),
        dict(key="qminu", label="qu talón", expr="={SVu}/{B}*(1-6*{eu}/{B})", unit="kPa"),
        dict(key="qp", label="qu cara frontal vástago", expr="=" + qx.replace("{x}", "{Lp}"), unit="kPa"),
        dict(key="qt", label="qu cara posterior vástago", expr="=" + qx.replace("{x}", "({Lp}+{tb})"), unit="kPa"),
        dict(key="Vp", label="Vu puntera", unit="kN/m",
             expr="=0.5*({qp}+{qmaxu})*{Lp}-{fD}*{gc}*{hz}*{Lp}"),
        dict(key="Vt", label="Vu talón (− hacia abajo)", unit="kN/m",
             expr="=-{Wu4}-{Wu5}-{fD}*{gc}*{hz}*{Lt}+0.5*({qt}+{qminu})*{Lt}"),
        dict(key="zd", label="d zapata", expr="={hz}-{rec}", unit="m", fmt="0.000"),
        dict(key="zVc", label="φVc = φ·0.17λ√f'c b d", expr="={phiv}*0.17*{lam}*SQRT({fc})*1*{zd}*1000", unit="kN/m",
             check='=IF(MAX(ABS({Vp}),ABS({Vt}))<={zVc},"OK","NO CUMPLE")'),
    ])
    b2 = max(rL, rM, rR)
    mp = ("={qp}*{Lp}^2/2+({qmaxu}-{qp})*{Lp}/2*(2/3*{Lp})-{fD}*{gc}*{hz}*{Lp}*{Lp}/2")
    mt = ("={qminu}*{Lt}^2/2+({qt}-{qminu})*{Lt}/2*({Lt}/3)-{Wu5}*(2/3*{Lt})-{Wu4}*({Lt}/2)"
          "-{fD}*{gc}*{hz}*{Lt}*{Lt}/2")
    rM2 = S.block("M", b2, "13.1 Puntera — acero inferior", flex_rows("p", mp, "={zd}", 5, 6, "{hz}", "puntera"))
    rR2 = S.block("R", b2, "13.2 Talón — acero superior", flex_rows("t", mt, "={zd}", 5, 6, "{hz}", "talón"))
    # ---- Síntesis
    rL2 = S.block("L", b2, "SÍNTESIS DE DISEÑO", [
        dict(label="Dimensiones B × H", expr='=FIXED({B},2)&" × "&FIXED({H},2)&" m"', fmt="@", span=True),
        dict(label="FS volcamiento", expr="={FSv1}", check='=IF({FSv1}>={FSv},"OK","NO CUMPLE")'),
        dict(label="FS deslizamiento", expr="={FSd1}", check='=IF({FSd1}>={FSd},"OK","NO CUMPLE")'),
        dict(label="Excentricidad / q máx", expr="={qmax}", unit="kPa",
             check='=IF(AND(ABS({e})<={B6},{qmax}<={qadm},{qmin}>=0),"OK","NO CUMPLE")'),
        dict(label="Sismo (volc. / desl.)", expr='=IF(ISNUMBER({FSve}),FIXED({FSve},2)&" / "&FIXED({FSde},2),"No aplica")',
             fmt="@", check='=IF(ISNUMBER({FSve}),IF(AND({FSve}>={FSvs},{FSde}>={FSds}),"OK","NO CUMPLE"),"—")'),
        dict(label="Vástago (cara interior)", expr="={vtxt}", fmt="@", span=True),
        dict(label="Puntera (inferior)", expr="={ptxt}", fmt="@", span=True),
        dict(label="Talón (superior)", expr="={ttxt}", fmt="@", span=True),
        dict(label="Cortante vástago", expr="={Vu}", unit="kN/m", check='=IF({Vu}<={vphiVc},"OK","NO CUMPLE")'),
        dict(label="Cortante zapata", expr="=MAX(ABS({Vp}),ABS({Vt}))", unit="kN/m",
             check='=IF(MAX(ABS({Vp}),ABS({Vt}))<={zVc},"OK","NO CUMPLE")'),
        dict(label="Relleno granular (c'1 = 0)", expr="={c1}", unit="kPa", check='=IF({c1}=0,"OK","NO CUMPLE")'),
    ])
    end = max(rM2, rR2, rL2)
    notes = [
        "Notas:",
        "• Vástago: como en el documento, Vu y Mu del vástago se toman con el empuje total sobre H' (conservador); "
        "la sección crítica exacta está en la base del vástago.",
        "• Puntera: el peso propio se mayora con 1.2 de forma consistente (el ejemplo del documento no lo mayora en Mp).",
        "• Cortante de zapata evaluado en la cara del vástago (conservador frente a evaluarlo a d de la cara).",
        "• No incluye: refuerzo horizontal / de retracción del vástago, longitudes de desarrollo, ni la fuerza inercial "
        "del muro en sismo (kh·W). Revíselos según NSR-10.",
    ]
    for i, t in enumerate(notes):
        ws[f"B{end + i}"] = t
        ws[f"B{end + i}"].font = f_b if i == 0 else f_small
        ws.merge_cells(f"B{end + i}:M{end + i}")
    S.write()
    for rng_cell in S.checks:
        pass
    # formato condicional de chequeos
    red = PatternFill("solid", fgColor="FFC7CE")
    green = PatternFill("solid", fgColor="C6EFCE")
    for cell in S.checks:
        ws.conditional_formatting.add(cell, FormulaRule(
            formula=[f'OR(ISNUMBER(SEARCH("NO CUMPLE",{cell})),ISNUMBER(SEARCH("REVISAR",{cell})),'
                     f'ISNUMBER(SEARCH("REDIMENSIONAR",{cell})))'],
            fill=red, font=Font(name=FONT, bold=True, color="9C0006"), stopIfTrue=True))
        ws.conditional_formatting.add(cell, FormulaRule(formula=[f'{cell}="OK"'], fill=green,
                                                        font=Font(name=FONT, bold=True, color="006100")))
    dv = DataValidation(type="list", formula1='"3,4,5,6,7,8"', allow_blank=False)
    ws.add_data_validation(dv)
    for k in ("vbar", "vbar2", "pbar", "pbar2", "tbar", "tbar2"):
        dv.add(S.addr[k].replace("$", ""))

    # ---- esquema del muro (gráfico que se actualiza con la geometría)
    hx = 16  # columnas P..S auxiliares
    pts = [("0", "0"), ("{B}", "0"), ("{B}", "{hz}"), ("{Lp}+{tb}", "{hz}"), ("{Lp}+{tb}", "{hz}+{H2}"),
           ("{Lp}+{tb}-{tc}", "{hz}+{H2}"), ("{Lp}", "{hz}"), ("0", "{hz}"), ("0", "0")]
    soil = [("{Lp}+{tb}", "{hz}+{H2}"), ("{B}+0.5", f"{{hz}}+{{H2}}+({{Lt}}+0.5)*TAN({RAD}({{alpha}}))")]
    front = [("-1", "{D}"), ("{Lp}", "{D}")]
    ws.cell(7, hx, "Esquema (auxiliar)").font = f_small
    rows_series = []
    rr = 8
    for nm, P in (("Muro", pts), ("Relleno", soil), ("Terreno frontal", front)):
        start = rr
        for x, y in P:
            ws.cell(rr, hx, S.sub("=" + x)).number_format = "0.00"
            ws.cell(rr, hx + 1, S.sub("=" + y)).number_format = "0.00"
            for c in (hx, hx + 1):
                ws.cell(rr, c).font = f_small
            rr += 1
        rows_series.append((nm, start, rr - 1))
        rr += 1
    ch = ScatterChart()
    ch.title = "Sección del muro (m)"
    ch.style = 13
    ch.height, ch.width = 12, 16
    ch.roundedCorners = False
    ch.legend.position = "b"
    ch.legend.overlay = False
    ch.title.overlay = False
    ch.x_axis.delete = False
    ch.y_axis.delete = False
    ch.x_axis.title, ch.y_axis.title = "x desde la punta C", "y"
    colors = {"Muro": "7F7F7F", "Relleno": "C55A11", "Terreno frontal": "548235"}
    for nm, a, b in rows_series:
        xs = Reference(ws, min_col=hx, min_row=a, max_row=b)
        ys = Reference(ws, min_col=hx + 1, min_row=a, max_row=b)
        s = Series(ys, xs, title=nm)
        s.marker.symbol = "none"
        s.graphicalProperties.line.solidFill = colors[nm]
        s.graphicalProperties.line.width = 28000 if nm == "Muro" else 19000
        s.smooth = False
        ch.series.append(s)
    ws.add_chart(ch, f"B{end + len(notes) + 1}")
    ws.column_dimensions[get_column_letter(hx)].width = 9
    ws.column_dimensions[get_column_letter(hx + 1)].width = 9
    # alturas fijas: evita que el gráfico se desplace al crecer filas con texto ajustado
    for rr in range(3, end + len(notes) + 25):
        ws.row_dimensions[rr].height = 16.5
    ws.row_dimensions[t0 + 1].height = 30
    for rr in rows_tab + [rv]:
        ws.row_dimensions[rr].height = 16.5
    ws.freeze_panes = "A3"
    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_area = f"A1:M{end + len(notes) + 20}"
    return S


wb = Workbook()
build_inputs(wb)
for ex in EXAMPLES:
    S = build_wall(wb, ex["muro"])
build_tablas(wb)
for ws in wb.worksheets:
    for row in ws.iter_rows():
        for c in row:
            if c.font and c.font.name != FONT:
                c.font = Font(name=FONT, size=c.font.sz or 11, bold=c.font.b, italic=c.font.i, color=c.font.color)
wb.save(OUT)
print("saved", OUT)
