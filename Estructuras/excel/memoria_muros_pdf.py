"""Memoria de cálculo paso a paso (PDF) de un muro de contención, a partir de MEMORIA_CALCULO_MUROS.xlsx.

Todos los números se leen del Excel ya recalculado (valores en caché), así el PDF y el Excel coinciden.
Uso: python memoria_muros_pdf.py MEMORIA_CALCULO_MUROS.xlsx M1 salida.pdf
Procedimiento: notas 'Muros de Contención' (G. A. Chang Nieto) basadas en Das (2012), Fundamentos de
Ingeniería de Cimentaciones, 7a ed.; NSR-10 B.2.4 y Título C.
"""
import io
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

XLSX, WALL, OUT = (sys.argv[1:4] + [None] * 3)[:3]
XLSX = XLSX or "MEMORIA_CALCULO_MUROS.xlsx"
WALL = WALL or "M1"
OUT = OUT or f"MEMORIA_{WALL}.pdf"

# ------------------------------------------------------------------ lectura del Excel
class Sheet:
    def __init__(self, ws):
        self.ws = ws
        self.d = {}
        for row in ws.iter_rows(min_row=7, max_row=ws.max_row, min_col=2, max_col=13):
            for i in (0, 4, 8):
                lab, v = row[i].value, row[i + 1]
                if isinstance(lab, str) and v.value is not None:
                    self.d.setdefault(lab.strip(), []).append((v.value, f"{ws.title}!{v.coordinate}"))

    def __call__(self, label, n=0):
        return self.d[label][n][0]

    def cell(self, label, n=0):
        return self.d[label][n][1]


wb = openpyxl.load_workbook(XLSX, data_only=True)
S = Sheet(wb[WALL])
ws = wb[WALL]
if S("H' = H1 + H2 + H3") is None:
    sys.exit("El Excel no tiene valores calculados: ábralo y guárdelo en Excel (o recalcule) primero.")

g = dict(H2=S("H2 (vástago)"), tc=S("Corona"), tb=S("Base del vástago"), Lp=S("Puntera"), Lt=S("Talón"),
         hz=S("H3 (espesor zapata)"), D=S("D (desplante)"), alpha=S("α (relleno)"), B=S("B = puntera + base + talón"),
         H=S("H = H2 + H3"), H1=S("H1 = talón·tan α"), Hp=S("H' = H1 + H2 + H3"))
soil = dict(g1=S("γ1"), phi1=S("φ'1"), c1=S("c'1"), g2=S("γ2"), phi2=S("φ'2"), c2=S("c'2"), qadm=S("q admisible"))
mat = dict(fc=S("f'c"), fy=S("fy"), gc=S("γ concreto"), rec=S("Recubrimiento (a centroide)"), lam=S("λ"))
fac = dict(k1=S("k1 (δ' = k1·φ'2)"), k2=S("k2 (c'a = k2·c'2)"), FSv=S("FS volcamiento mín."),
           FSd=S("FS deslizamiento mín."), fD=S("Factor carga muerta (D)"), fH=S("Factor empuje / suelo (H)"),
           phif=S("φ flexión"), phiv=S("φ cortante"), rhomin=S("ρ mínima"))
# tabla 8.1 (filas tras el encabezado "Sección")
hdr = next(r for r in range(1, ws.max_row + 1) if ws.cell(r, 2).value == "Sección")
tab = []
for r in range(hdr + 1, hdr + 8):
    tab.append([ws.cell(r, c).value for c in range(2, 12)])

# ------------------------------------------------------------------ estilos PDF
_FD = matplotlib.get_data_path() + "/fonts/ttf/"   # DejaVu incluida con matplotlib (siempre disponible)
pdfmetrics.registerFont(TTFont("DV", _FD + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", _FD + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DVI", _FD + "DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DVB", italic="DVI", boldItalic="DVB")
NAVY = colors.HexColor("#44546A")
st_body = ParagraphStyle("b", fontName="DV", fontSize=9.5, leading=13.5, alignment=TA_JUSTIFY, spaceAfter=4)
st_h1 = ParagraphStyle("h1", fontName="DVB", fontSize=14, leading=18, textColor=NAVY, spaceBefore=8, spaceAfter=6)
st_h2 = ParagraphStyle("h2", fontName="DVB", fontSize=11, leading=14, textColor=NAVY, spaceBefore=6, spaceAfter=3)
st_cap = ParagraphStyle("c", fontName="DVI", fontSize=8.5, leading=11, alignment=TA_CENTER, textColor=colors.grey,
                        spaceAfter=6)
st_xl = ParagraphStyle("x", fontName="DV", fontSize=8.5, leading=11, textColor=colors.HexColor("#1F3864"),
                       backColor=colors.HexColor("#EEF2F7"), borderPadding=(3, 4, 3, 4), spaceBefore=3, spaceAfter=6)
st_small = ParagraphStyle("s", fontName="DV", fontSize=8.5, leading=11)

story = []


def P(t, s=st_body):
    story.append(Paragraph(t, s))


def H1(t):
    story.append(Paragraph(t, st_h1))


def H2(t):
    story.append(Paragraph(t, st_h2))


def XL(*labels):
    """Recuadro: dónde ver este valor en el Excel."""
    parts = []
    for lab in labels:
        n = 0
        if isinstance(lab, tuple):
            lab, n = lab
        parts.append(f"<b>{lab}</b> → celda {S.cell(lab, n)}")
    story.append(Paragraph("En el Excel: " + " · ".join(parts), st_xl))


def eq(tex, size=12, width_cm=None):
    """Ecuación renderizada con mathtext."""
    fig = plt.figure(figsize=(0.01, 0.01))
    fig.text(0, 0, f"${tex}$", fontsize=size)
    buf = io.BytesIO()
    fig.savefig(buf, dpi=250, format="png", bbox_inches="tight", pad_inches=0.04, transparent=True)
    plt.close(fig)
    buf.seek(0)
    im = Image(buf)
    w, h = im.imageWidth / 250 * 72, im.imageHeight / 250 * 72
    if width_cm and w > width_cm * cm:
        h, w = h * width_cm * cm / w, width_cm * cm
    im.drawWidth, im.drawHeight = w, h
    story.append(im)
    story.append(Spacer(1, 3))


def fig_img(fig, width_cm=15.5, caption=None):
    buf = io.BytesIO()
    fig.savefig(buf, dpi=200, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    im = Image(buf)
    r = im.imageHeight / im.imageWidth
    im.drawWidth, im.drawHeight = width_cm * cm, width_cm * cm * r
    items = [im]
    if caption:
        items.append(Paragraph(caption, st_cap))
    story.append(KeepTogether(items))


def table(rows, widths, head=True, zebra=True, align="CENTER"):
    t = Table(rows, colWidths=[w * cm for w in widths], hAlign=align)
    style = [("FONT", (0, 0), (-1, -1), "DV", 8.5), ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (1, 0), (-1, -1), "CENTER")]
    if head:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D6DCE4")), ("FONT", (0, 0), (-1, 0), "DVB", 8.5)]
    if zebra:
        for i in range(1 if head else 0, len(rows)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F5F7FA")))
    t.setStyle(TableStyle(style))
    story.append(KeepTogether([t]))
    story.append(Spacer(1, 6))


def ok(cond):
    return '<font color="#006100"><b>CUMPLE ✓</b></font>' if cond else '<font color="#9C0006"><b>NO CUMPLE ✗</b></font>'


f2 = lambda x: f"{x:,.2f}"
f3 = lambda x: f"{x:,.3f}"
f4 = lambda x: f"{x:.4f}"

# ------------------------------------------------------------------ dibujo
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
C_CONC, C_FILL, C_SOIL, C_PRESS, C_FORCE = "#BFBFBF", "#D9C9A3", "#E8DCC0", "#5B9BD5", "#C00000"
Lp, tb, tc, Lt, hz, H2_, D_, B_, H1_, Hp = (g[k] for k in ("Lp", "tb", "tc", "Lt", "hz", "H2", "D", "B", "H1", "Hp"))
ta = math.tan(math.radians(g["alpha"]))
xb = Lp + tb                     # cara posterior del vástago
xf_top = Lp + tb - tc            # cara frontal en la corona
wall_poly = [(0, 0), (B_, 0), (B_, hz), (xb, hz), (xb, hz + H2_), (xf_top, hz + H2_), (Lp, hz), (0, hz)]


def draw_base(ax, soil_back=True, soil_front=True, wall_color=C_CONC):
    if soil_back:
        ax.add_patch(Polygon([(xb, hz), (B_ + 1.2, hz), (B_ + 1.2, hz + H2_ + (Lt + 1.2) * ta), (xb, hz + H2_)],
                             closed=True, fc=C_SOIL, ec="none", zorder=0))
        ax.add_patch(Rectangle((B_, -0.8), 1.2, 0.8 + hz, fc=C_SOIL, ec="none", zorder=0))
        ax.plot([xb, B_ + 1.2], [hz + H2_, hz + H2_ + (Lt + 1.2) * ta], color="#8C6D31", lw=1.2)
    ax.add_patch(Rectangle((-1.5, -0.8), B_ + 2.7, 0.8, fc=C_SOIL, ec="none", zorder=0))
    if soil_front:
        xs = Lp + (tb - tc) * (D_ - hz) / H2_
        ax.add_patch(Polygon([(-1.5, 0), (0, 0), (0, hz), (Lp, hz), (xs, D_), (-1.5, D_)], closed=True,
                             fc=C_SOIL, ec="none", zorder=0))
        ax.plot([-1.5, xs], [D_, D_], color="#8C6D31", lw=1.2)
    ax.add_patch(Polygon(wall_poly, closed=True, fc=wall_color, ec="black", lw=1.4, zorder=2))
    ax.plot(0, 0, "ko", ms=4, zorder=5)
    ax.annotate("C", (0, 0), xytext=(-12, -12), textcoords="offset points", fontweight="bold")
    ax.set_aspect("equal")
    ax.axis("off")


def dim(ax, p1, p2, text, off=(0, 0), color="#1F3864", fs=8):
    (x1, y1), (x2, y2) = p1, p2
    ox, oy = off
    a = FancyArrowPatch((x1 + ox, y1 + oy), (x2 + ox, y2 + oy), arrowstyle="<|-|>", mutation_scale=7, color=color,
                        lw=0.8, zorder=6)
    ax.add_patch(a)
    for (x, y) in (p1, p2):
        ax.plot([x, x + ox * 1.05], [y, y + oy * 1.05], color=color, lw=0.4, zorder=6)
    ax.text((x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy, text, color=color, fontsize=fs, ha="center", va="center",
            bbox=dict(fc="white", ec="none", pad=0.6), zorder=7)


def arrow(ax, p_from, p_to, color=C_FORCE, lw=1.6, text=None, tpos=None, fs=8.5, ha="center"):
    ax.add_patch(FancyArrowPatch(p_from, p_to, arrowstyle="-|>", mutation_scale=11, color=color, lw=lw, zorder=8))
    if text:
        x, y = tpos if tpos else p_from
        ax.text(x, y, text, color=color, fontsize=fs, ha=ha, va="center", fontweight="bold", zorder=9,
                bbox=dict(fc="white", ec="none", alpha=0.8, pad=0.5))


# ================================================================== PORTADA
story.append(Spacer(1, 1.0 * cm))
story.append(Paragraph("MEMORIA DE CÁLCULO", ParagraphStyle("t", fontName="DVB", fontSize=24, leading=30,
                                                            alignment=TA_CENTER, textColor=NAVY)))
story.append(Paragraph("Muro de contención en voladizo — paso a paso",
                       ParagraphStyle("t2", fontName="DV", fontSize=14, leading=20, alignment=TA_CENTER)))
story.append(Spacer(1, 0.4 * cm))
desc = ws["C5"].value or ""
story.append(Paragraph(f"Muro <b>{WALL}</b> — {desc}", ParagraphStyle("t3", fontName="DV", fontSize=11,
                                                                       alignment=TA_CENTER)))
story.append(Spacer(1, 0.6 * cm))
fig, ax = plt.subplots(figsize=(6.5, 5.2))
draw_base(ax)
dim(ax, (0, -0.8), (B_, -0.8), f"B = {B_:.2f} m", off=(0, -0.35))
dim(ax, (B_ + 1.2, 0), (B_ + 1.2, hz + H2_), f"H = {g['H']:.2f} m", off=(0.45, 0))
ax.text(xb + Lt / 2, hz + H2_ / 2, f"Relleno\nγ1 = {soil['g1']:.1f} kN/m³\nφ'1 = {soil['phi1']:.0f}°",
        ha="center", fontsize=8)
ax.text(B_ / 2, -1.75, f"Suelo de fundación: γ2 = {soil['g2']:.1f} kN/m³, φ'2 = {soil['phi2']:.0f}°, c'2 = {soil['c2']:.0f} kPa",
        ha="center", fontsize=7.5)
ax.set_xlim(-1.6, B_ + 2.0)
ax.set_ylim(-2.0, hz + H2_ + (Lt + 1.2) * ta + 0.4)
fig_img(fig, 9.5)
story.append(Spacer(1, 0.4 * cm))
FSv1, FSd1 = S("Opción 1: ΣMR / ΣMo"), S("FS con Pp")
rows = [["Revisión", "Resultado", "Requisito", "Estado"],
        ["Volcamiento", f2(FSv1), f"≥ {fac['FSv']:.1f}", "CUMPLE" if FSv1 >= fac["FSv"] else "NO CUMPLE"],
        ["Deslizamiento", f2(FSd1), f"≥ {fac['FSd']:.1f}", "CUMPLE" if FSd1 >= fac["FSd"] else "NO CUMPLE"],
        ["Excentricidad e", f"{S('e = B/2 − (ΣMR−ΣMo)/ΣV'):.3f} m", f"≤ B/6 = {S('B/6'):.3f} m",
         "CUMPLE" if abs(S('e = B/2 − (ΣMR−ΣMo)/ΣV')) <= S('B/6') else "NO CUMPLE"],
        ["q máx suelo", f"{S('q punta = ΣV/B (1+6e/B)'):.1f} kPa", f"≤ {soil['qadm']:.0f} kPa",
         "CUMPLE" if S('q punta = ΣV/B (1+6e/B)') <= soil["qadm"] else "NO CUMPLE"],
        ["Refuerzo vástago", S("Refuerzo opción 1"), "cara del relleno", ""],
        ["Refuerzo puntera", S("Refuerzo opción 1", 1), "cara inferior", ""],
        ["Refuerzo talón", S("Refuerzo opción 1", 2), "cara superior", ""]]
table(rows, [4.2, 3.8, 3.8, 2.8])
P("Procedimiento: notas de clase <i>Muros de Contención</i> (Diseño de Concreto II, G. A. Chang Nieto), basadas en "
  "B. M. Das, <i>Fundamentos de Ingeniería de Cimentaciones</i>, 7a ed. (2012), y en la NSR-10 (B.2.4, Título C). "
  "Todos los valores de este documento salen de la hoja <b>" + WALL + "</b> del archivo "
  "<b>MEMORIA_CALCULO_MUROS.xlsx</b>; cada paso indica la celda donde aparece.", st_small)
story.append(PageBreak())

# ================================================================== 0. CÓMO ESTÁ ORGANIZADO EL EXCEL
H1("0. Cómo está organizado el Excel")
fig, ax = plt.subplots(figsize=(8, 3.1))
ax.axis("off")
boxes = [(0.02, "INPUTS", "Una fila por muro:\ngeometría, suelos,\nmateriales, método\nde empuje, sismo"),
         (0.37, f"Hoja {WALL}", "Memoria del muro:\nbusca sus datos por\nnombre (celda C4) y\ncalcula pasos 1–13"),
         (0.72, "TABLAS", "Barras de refuerzo,\nrangos de Das,\nreferencias")]
for x, t, s_ in boxes:
    ax.add_patch(Rectangle((x, 0.18), 0.26, 0.64, fc="#EEF2F7", ec=NAVY.hexval().replace("0x", "#"), lw=1.5,
                           transform=ax.transAxes))
    ax.add_patch(Rectangle((x, 0.68), 0.26, 0.14, fc="#44546A", ec="none", transform=ax.transAxes))
    ax.text(x + 0.13, 0.75, t, color="white", ha="center", va="center", fontweight="bold", transform=ax.transAxes)
    ax.text(x + 0.13, 0.43, s_, ha="center", va="center", fontsize=8.5, transform=ax.transAxes)
for x0, x1 in ((0.28, 0.37), (0.72, 0.63)):
    ax.annotate("", xy=(x1, 0.5), xytext=(x0, 0.5), xycoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color="#C00000", lw=1.8))
ax.text(0.325, 0.56, "datos", ha="center", fontsize=8, transform=ax.transAxes, color="#C00000")
ax.text(0.675, 0.56, "áreas\nde barras", ha="center", fontsize=8, transform=ax.transAxes, color="#C00000")
fig_img(fig, 15, "Figura 0.1 — Flujo de información entre hojas.")
rows = [["Color / formato en la hoja", "Significado"],
        ["Celda gris, texto azul en negrita", "Dato editable (factores, barras elegidas, nombre del muro)"],
        ["Texto azul sin relleno", "Dato que viene de la hoja INPUTS"],
        ["Texto negro", "Resultado de una fórmula — no lo edite"],
        ["Verde «OK» / rojo «NO CUMPLE», «REVISAR»", "Chequeo automático contra el requisito"]]
table(rows, [7.5, 8.5])
P("Para un muro nuevo: (1) agregue una fila en <b>INPUTS</b>; (2) copie una hoja de memoria (clic derecho → "
  "Mover o copiar → Crear una copia); (3) escriba el nombre del muro en la celda <b>C4</b>. "
  "Si un chequeo sale en rojo, vuelva a INPUTS y cambie la geometría (más talón para deslizamiento y volcamiento, "
  "más puntera para bajar q máx, dentellón si el deslizamiento no cumple).")
P("<b>Convención de signos y unidades.</b> Fuerzas en kN por metro de muro (kN/m), momentos en kN·m/m, "
  "presiones en kPa (= kN/m²). Los momentos se toman respecto a la punta <b>C</b> (borde frontal de la zapata). "
  "La coordenada x se mide desde C hacia el relleno.")
story.append(PageBreak())

# ================================================================== 1. GEOMETRÍA
H1("1. Datos y geometría")
fig, ax = plt.subplots(figsize=(7.8, 6.6))
draw_base(ax)
dim(ax, (0, 0), (Lp, 0), f"{Lp:.2f}", off=(0, -0.45))
dim(ax, (Lp, 0), (xb, 0), f"{tb:.2f}", off=(0, -0.45))
ax.annotate("puntera", xy=(Lp / 2, -0.5), xytext=(-1.0, -0.85), fontsize=7.5, color="#1F3864",
            arrowprops=dict(arrowstyle="-", color="#1F3864", lw=0.5))
ax.annotate("base del vástago", xy=(Lp + tb / 2, -0.5), xytext=(Lp + tb / 2 + 0.6, -0.85), fontsize=7.5,
            color="#1F3864", arrowprops=dict(arrowstyle="-", color="#1F3864", lw=0.5))
dim(ax, (xb, 0), (B_, 0), f"talón {Lt:.2f}", off=(0, -0.45))
dim(ax, (0, 0), (B_, 0), f"B = {B_:.2f} m", off=(0, -1.2))
dim(ax, (xf_top, hz + H2_), (xb, hz + H2_), f"corona {tc:.2f}", off=(0, 0.3))
dim(ax, (B_, 0), (B_, hz), f"H3={hz:.2f}", off=(0.55, 0), fs=7.5)
dim(ax, (B_, hz), (B_, hz + H2_), f"H2 = {H2_:.2f}", off=(0.55, 0))
if H1_ > 0.01:
    dim(ax, (B_, hz + H2_), (B_, hz + H2_ + H1_), f"H1={H1_:.3f}", off=(0.55, 0), fs=7.5)
dim(ax, (B_ + 1.2, 0), (B_ + 1.2, Hp), f"H' = {Hp:.3f}", off=(0.5, 0))
dim(ax, (-0.9, 0), (-0.9, D_), f"D = {D_:.2f}", off=(-0.3, 0))
ax.plot([B_, B_], [hz, hz + H2_ + H1_], "--", color="#C00000", lw=1)
ax.text(B_ + 0.05, hz + H2_ * 0.55, "plano\nvirtual AB", color="#C00000", fontsize=7.5)
if g["alpha"] > 0:
    ax.text(xb + Lt * 0.55, hz + H2_ + Lt * 0.55 * ta + 0.3, f"α = {g['alpha']:.0f}°", color="#8C6D31", fontsize=8)
ax.set_xlim(-1.8, B_ + 2.4)
ax.set_ylim(-2.0, Hp + 0.9)
fig_img(fig, 14.5, "Figura 1.1 — Geometría adoptada. El empuje se calcula sobre el plano vertical AB que pasa por el "
                   "extremo del talón (Das, fig. 8.7).")
eq(r"B = L_{puntera} + b_{vástago} + L_{talón} = %.2f + %.2f + %.2f = %.2f\ \mathrm{m}" % (Lp, tb, Lt, B_))
eq(r"H_1 = L_{talón}\,\tan\alpha = %.2f\,\tan %.0f^\circ = %.3f\ \mathrm{m}" % (Lt, g["alpha"], H1_))
eq(r"H' = H_1 + H_2 + H_3 = %.3f + %.2f + %.2f = %.3f\ \mathrm{m}" % (H1_, H2_, hz, Hp))
XL("B = puntera + base + talón", "H1 = talón·tan α", "H' = H1 + H2 + H3")
rows = [["Relleno (suelo 1)", "", "Fundación (suelo 2)", "", "Materiales", ""],
        ["γ1", f"{soil['g1']:.2f} kN/m³", "γ2", f"{soil['g2']:.2f} kN/m³", "f'c", f"{mat['fc']:.0f} MPa"],
        ["φ'1", f"{soil['phi1']:.1f}°", "φ'2", f"{soil['phi2']:.1f}°", "fy", f"{mat['fy']:.0f} MPa"],
        ["c'1", f"{soil['c1']:.1f} kPa", "c'2", f"{soil['c2']:.1f} kPa", "γ concreto", f"{mat['gc']:.2f} kN/m³"],
        ["", "", "q adm", f"{soil['qadm']:.0f} kPa", "recubr. (centroide)", f"{mat['rec']:.3f} m"]]
table(rows, [2.0, 2.6, 2.6, 2.6, 3.4, 2.6])

# ================================================================== 2. PREDIMENSIONAMIENTO
H1("2. Predimensionamiento (Das)")
P("Antes de revisar la estabilidad se escogen dimensiones dentro de los rangos que recomienda Das para muros en "
  "voladizo (figura 2.1). H es la altura total del muro (H2 + H3). La hoja compara cada valor adoptado contra la "
  "recomendación; un «REVISAR» no es un error, sino una alerta para justificar la dimensión.")
fig, axs = plt.subplots(1, 2, figsize=(8.6, 4.3), gridspec_kw=dict(width_ratios=[1, 1.05]))
ax = axs[0]
Hn = 1.0
pts = [(0, 0), (0.6, 0), (0.6, 0.1), (0.25, 0.1), (0.25, 1.0), (0.18, 1.0), (0.15, 0.1), (0, 0.1)]
ax.add_patch(Polygon(pts, closed=True, fc=C_CONC, ec="k"))
dim(ax, (0, 0), (0.6, 0), "0.5H – 0.7H", off=(0, -0.08), fs=7.5)
dim(ax, (0.6, 0), (0.6, 0.1), "0.1H", off=(0.08, 0), fs=7.5)
dim(ax, (0.15, 0.1), (0.25, 0.1), "0.1H", off=(0, 0.06), fs=7.5)
dim(ax, (0.18, 1.0), (0.25, 1.0), "≥0.30 m", off=(0, 0.07), fs=7.5)
dim(ax, (0.68, 0), (0.68, 1.0), "H", off=(0.06, 0), fs=8)
ax.text(0.02, 0.6, "inclinación\n≥ 0.02", fontsize=7.5)
ax.set_xlim(-0.1, 0.85)
ax.set_ylim(-0.2, 1.15)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title("Proporciones recomendadas (Das)", fontsize=9)
ax = axs[1]
ax.axis("off")
rows_p = [("Corona ≥ 0.30 m", tc, 0.30, None), ("Base vástago ≈ 0.1H", tb, 0.1 * g["H"], None),
          ("Losa base ≈ 0.1H", hz, 0.1 * g["H"], None), ("B entre 0.5H y 0.7H", B_, 0.5 * g["H"], 0.7 * g["H"])]
y = 0.9
for name, val, lo, hi in rows_p:
    good = val >= lo - 0.005 and (hi is None or val <= hi)
    rng = f"{lo:.2f} – {hi:.2f}" if hi else f"≥ {lo:.2f}"
    ax.text(0, y, name, fontsize=8.5, fontweight="bold", transform=ax.transAxes)
    ax.text(0, y - 0.07, f"recomendado {rng} m · adoptado {val:.2f} m", fontsize=8, transform=ax.transAxes)
    ax.text(0.95, y - 0.035, "OK" if good else "REVISAR", fontsize=9, fontweight="bold", ha="right",
            color="#006100" if good else "#9C0006", transform=ax.transAxes)
    y -= 0.21
fig_img(fig, 16, f"Figura 2.1 — Rangos de predimensionamiento para H = {g['H']:.2f} m.")
XL("Corona ≥ 0.30 m", "B mínimo = 0.5H", "Inclinación cara (≥ 0.02)")
story.append(PageBreak())

# ================================================================== 3. EMPUJE ACTIVO
H1("3. Empuje activo de tierras")
Ka, Kar, Kac = S("Ka usado"), S("Ka Rankine (ec. 7.26)"), S("Ka Coulomb (ec. 7.25, β=90°)")
Pa, Pv, Ph, Mo = S("Pa = ½ γ1 H'² Ka"), S("Pv = Pa sen(ángulo)"), S("Ph = Pa cos(ángulo)"), S("ΣMo = Ph·H'/3 (ec. 8.3)")
ang = S("Inclinación de Pa")
P("El relleno empuja el muro hacia afuera. Con el método de Rankine el empuje actúa sobre el plano virtual AB, "
  "con una distribución triangular de presiones que crece con la profundidad, y la resultante Pa es paralela "
  "a la superficie del relleno (inclinada α). Si se elige Coulomb, Pa se inclina δ' (fricción muro–suelo).")
fig, ax = plt.subplots(figsize=(7.8, 5.8))
draw_base(ax, soil_front=True)
sig = soil["g1"] * Hp * Ka
sc = 1.6 / sig
ax.add_patch(Polygon([(B_, Hp), (B_, 0), (B_ + sig * sc, 0)], closed=True, fc=C_PRESS, alpha=0.35, ec=C_PRESS,
                     zorder=4))
for yy in np.linspace(0.3, Hp - 0.3, 9):
    L = soil["g1"] * (Hp - yy) * Ka * sc
    ax.add_patch(FancyArrowPatch((B_ + L, yy), (B_ + 0.02, yy), arrowstyle="-|>", mutation_scale=6, color=C_PRESS,
                                 lw=0.7, zorder=5))
ax.text(B_ + sig * sc + 0.05, 0.15, f"σa = γ1H'Ka\n= {sig:.1f} kPa", fontsize=7.5, color="#1F4E79")
ya = Hp / 3
ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
arrow(ax, (B_ + 1.5 * ca + 0.05, ya + 1.5 * sa), (B_, ya), text=f"Pa = {Pa:.1f}", tpos=(B_ + 1.7, ya + 1.5 * sa + 0.25))
arrow(ax, (B_ + 1.3, ya), (B_ + 0.02, ya), color="#7030A0", lw=1.1, text=f"Ph = {Ph:.1f}",
      tpos=(B_ + 1.1, ya - 0.3), fs=7.5)
if Pv > 0.01:
    arrow(ax, (B_, ya + 1.0), (B_, ya + 0.02), color="#7030A0", lw=1.1, text=f"Pv = {Pv:.1f}",
          tpos=(B_ - 0.55, ya + 0.8), fs=7.5)
dim(ax, (B_ + 2.5, 0), (B_ + 2.5, ya), f"H'/3 = {ya:.3f}", off=(0.3, 0), fs=7.5)
ax.set_xlim(-1.6, B_ + 3.4)
ax.set_ylim(-1.0, Hp + 0.8)
fig_img(fig, 14.5, "Figura 3.1 — Diagrama de presión activa sobre el plano AB y resultante Pa a H'/3 de la base.")
H2("3.1 Coeficiente de empuje activo Ka")
P("<b>Rankine</b>, cara posterior vertical (θ = 0) y relleno inclinado α (Das, ec. 7.26 con θ = 0):")
eq(r"K_a=\cos\alpha\;\frac{\cos\alpha-\sqrt{\cos^2\alpha-\cos^2\phi'_1}}{\cos\alpha+\sqrt{\cos^2\alpha-\cos^2\phi'_1}}", 13)
eq(r"K_a=\cos %.0f^\circ\;\frac{\cos %.0f^\circ-\sqrt{\cos^2 %.0f^\circ-\cos^2 %.0f^\circ}}{\cos %.0f^\circ+\sqrt{\cos^2 %.0f^\circ-\cos^2 %.0f^\circ}}=%.4f"
   % (g["alpha"], g["alpha"], g["alpha"], soil["phi1"], g["alpha"], g["alpha"], soil["phi1"], Kar), 12)
P("<b>Coulomb</b> (Das, ec. 7.25), con β = 90° (plano AB vertical) y fricción muro–suelo δ':")
eq(r"K_a=\frac{\sin^2(\beta+\phi')}{\sin^2\beta\;\sin(\beta-\delta')\left[1+\sqrt{\dfrac{\sin(\phi'+\delta')\,"
   r"\sin(\phi'-\alpha)}{\sin(\beta-\delta')\,\sin(\alpha+\beta)}}\right]^2}", 13)
eq(r"\beta=90^\circ,\ \delta'=%.0f^\circ,\ \alpha=%.0f^\circ,\ \phi'_1=%.0f^\circ\quad\Rightarrow\quad K_a=%.4f"
   % (S("δ' (muro-suelo)"), g["alpha"], soil["phi1"], Kac), 12)
km = S("Ka manual (INPUTS)")
if km:
    P(f"En este muro se impuso <b>Ka = {km:.4f}</b> en INPUTS (columna «Ka manual»), el valor de tabla que usa el "
      f"ejemplo del documento. Si deja esa celda vacía, la hoja usa el Ka del método elegido "
      f"(<b>{S('Método')}</b>: {Kar if S('Método') == 'Rankine' else Kac:.4f}).")
XL("Ka Rankine (ec. 7.26)", "Ka Coulomb (ec. 7.25, β=90°)", "Ka usado")
H2("3.2 Fuerza activa y sus componentes")
eq(r"P_a=\frac{1}{2}\gamma_1 H'^2 K_a=\frac{1}{2}(%.2f)(%.3f)^2(%.4f)=%.2f\ \mathrm{kN/m}"
   % (soil["g1"], Hp, Ka, Pa))
eq(r"P_v=P_a\sin %.1f^\circ=%.2f\ \mathrm{kN/m}\qquad P_h=P_a\cos %.1f^\circ=%.2f\ \mathrm{kN/m}" % (ang, Pv, ang, Ph))
eq(r"\Sigma M_o=P_h\,\frac{H'}{3}=%.2f\times\frac{%.3f}{3}=%.2f\ \mathrm{kN\cdot m/m}\quad\mathrm{(Das,\ ec.\ 8.3)}"
   % (Ph, Hp, Mo))
XL("Pa = ½ γ1 H'² Ka", "Ph = Pa cos(ángulo)", "ΣMo = Ph·H'/3 (ec. 8.3)")
story.append(PageBreak())

# ================================================================== 4. FUERZAS VERTICALES
H1("4. Fuerzas verticales y momento resistente (tabla 8.1)")
P("El peso del concreto y del suelo que está encima del talón estabilizan el muro. Se divide la sección en figuras "
  "simples; para cada una se calcula el área, el peso por metro de muro W = γ·A y su brazo X medido desde la punta C. "
  "El suelo sobre la puntera se desprecia (conservador), igual que en el documento.")
fig, ax = plt.subplots(figsize=(7.8, 6.0))
draw_base(ax, soil_back=False, soil_front=False, wall_color="white")
polys = {1: [(xf_top, hz), (xb, hz), (xb, hz + H2_), (xf_top, hz + H2_)],
         2: [(Lp, hz), (xf_top, hz), (xf_top, hz + H2_)],
         3: [(0, 0), (B_, 0), (B_, hz), (0, hz)],
         4: [(xb, hz), (B_, hz), (B_, hz + H2_), (xb, hz + H2_)],
         5: [(xb, hz + H2_), (B_, hz + H2_), (B_, hz + H2_ + H1_)]}
cols = {1: "#A6A6A6", 2: "#C9C9C9", 3: "#8F8F8F", 4: C_FILL, 5: "#EAD9B0"}
for k, pp in polys.items():
    if k == 5 and H1_ < 0.01:
        continue
    ax.add_patch(Polygon(pp, closed=True, fc=cols[k], ec="black", lw=0.9, zorder=3))
    xbar = tab[k - 1][5]
    cy = np.mean([p[1] for p in pp])
    ax.text(xbar, cy, str(k), ha="center", va="center", fontsize=11, fontweight="bold", zorder=9,
            bbox=dict(boxstyle="circle", fc="white", ec="black"))
    arrow(ax, (xbar, cy - 0.35), (xbar, cy - 1.0 if k != 3 else cy - 0.5), color="#7F6000", lw=1.2)
if Pv > 0.01:
    arrow(ax, (B_, Hp / 3 + 1.2), (B_, Hp / 3 + 0.05), color=C_FORCE, text="Pv", tpos=(B_ + 0.25, Hp / 3 + 1.0))
for k in (1, 4):
    xbar = tab[k - 1][5]
    dim(ax, (0, 0), (xbar, 0), f"X{k} = {xbar:.2f}", off=(0, -0.45 - 0.4 * (k == 4)), fs=7.5)
ax.set_xlim(-0.8, B_ + 1.0)
ax.set_ylim(-1.4, Hp + 0.6)
fig_img(fig, 13, "Figura 4.1 — Secciones 1 a 5 y sus brazos medidos desde la punta C.")
rows = [["Secc.", "Descripción", "Área\n(m²)", "γ\n(kN/m³)", "W\n(kN/m)", "X\n(m)", "M = W·X\n(kN·m/m)",
         "Factor", "Wu\n(kN/m)", "Mu\n(kN·m/m)"]]
for r in tab[:-1]:
    rows.append([str(r[0]), r[1], f3(r[2]) if r[2] is not None else "", f2(r[3]) if r[3] is not None else "",
                 f2(r[4]), f2(r[5]), f2(r[6]), f2(r[7]), f2(r[8]), f2(r[9])])
r = tab[-1]
rows.append(["Σ", "Totales", "", "", f2(r[4]), "", f2(r[6]), "", f2(r[8]), f2(r[9])])
table(rows, [1.0, 3.6, 1.3, 1.4, 1.5, 1.1, 1.8, 1.2, 1.5, 1.7])
P("Fórmulas de cada fila (x desde C):")
eq(r"W_1=\gamma_c\,b_{corona}H_2\qquad X_1=L_p+(b_{base}-b_{corona})+\frac{b_{corona}}{2}", 10.5)
eq(r"W_2=\gamma_c\,\frac{(b_{base}-b_{corona})H_2}{2}\qquad X_2=L_p+\frac{2}{3}(b_{base}-b_{corona})", 10.5)
eq(r"W_3=\gamma_c\,B\,H_3\qquad X_3=\frac{B}{2}\qquad W_4=\gamma_1 L_t H_2\qquad X_4=L_p+b_{base}+\frac{L_t}{2}", 10.5)
eq(r"W_5=\gamma_1\frac{L_t H_1}{2}\qquad X_5=L_p+b_{base}+\frac{2}{3}L_t\qquad M_v=P_v\,B", 10.5)
P("Las dos últimas columnas mayoran las cargas para el diseño estructural (NSR-10 B.2.4-2: 1.2D + 1.6H): "
  f"concreto ×{fac['fD']:.1f}; suelo y empuje ×{fac['fH']:.1f}.")
story.append(Paragraph(f"En el Excel: tabla de la sección 7, filas {hdr + 1} a {hdr + 7} (ΣV en {WALL}!F{hdr + 7}, "
                       f"ΣMR en {WALL}!H{hdr + 7}).", st_xl))
story.append(PageBreak())

# ================================================================== 5. VOLCAMIENTO
SV, SMR = tab[-1][4], tab[-1][6]
Mv = tab[-2][6]
H1("5. Factor de seguridad al volcamiento")
P("El empuje tiende a hacer girar el muro alrededor de la punta C. Los pesos y la componente vertical Pv "
  "producen momentos que se oponen al giro.")
fig, ax = plt.subplots(figsize=(7.6, 5.4))
draw_base(ax)
th = np.linspace(math.radians(95), math.radians(175), 40)
ax.plot(1.1 * np.cos(th), 1.1 * np.sin(th) + 0.2, color=C_FORCE, lw=1.6)
ax.annotate("", xy=(1.1 * math.cos(th[-1]), 1.1 * math.sin(th[-1]) + 0.2),
            xytext=(1.1 * math.cos(th[-3]), 1.1 * math.sin(th[-3]) + 0.2),
            arrowprops=dict(arrowstyle="-|>", color=C_FORCE))
ax.text(-1.2, 1.5, "ΣMo\n(volcamiento)", color=C_FORCE, fontsize=8, ha="center")
arrow(ax, (B_ + 1.4, Hp / 3), (B_ + 0.02, Hp / 3), text=f"Ph = {Ph:.1f}", tpos=(B_ + 1.3, Hp / 3 + 0.3))
arrow(ax, (xb + Lt / 2, hz + H2_ * 0.7), (xb + Lt / 2, hz + 0.1), color="#7F6000", text="ΣV",
      tpos=(xb + Lt / 2 + 0.3, hz + H2_ * 0.7))
ax.text(B_ / 2, Hp + 0.4, "ΣMR (resistente)", color="#006100", fontsize=8.5, ha="center")
ax.set_xlim(-2.0, B_ + 2.0)
ax.set_ylim(-1.0, Hp + 0.8)
fig_img(fig, 12.5, "Figura 5.1 — Momentos de volcamiento y resistentes respecto a C.")
FSv2 = S("Opción 2: (ΣMR−Mv)/(ΣMo−Mv)")
P("<b>Opción 1</b> (más exigente; la usa el ejemplo del documento): Mv se suma a los momentos resistentes.")
eq(r"FS_{volc}=\frac{\Sigma M_R}{\Sigma M_o}=\frac{%.2f}{%.2f}=%.2f\ \geq %.1f" % (SMR, Mo, FSv1, fac["FSv"]))
P("Resultado: " + ok(FSv1 >= fac["FSv"]))
P("<b>Opción 2</b> (menos exigente): Mv se resta del momento de volcamiento.")
eq(r"FS_{volc}=\frac{\Sigma M_R-M_v}{\Sigma M_o-M_v}=\frac{%.2f-%.2f}{%.2f-%.2f}=%.2f" % (SMR, Mv, Mo, Mv, FSv2))
P("El documento recomienda un FS al volcamiento entre 2 y 3.")
XL("Opción 1: ΣMR / ΣMo", "Opción 2: (ΣMR−Mv)/(ΣMo−Mv)")

# ================================================================== 6. DESLIZAMIENTO
H1("6. Factor de seguridad al deslizamiento")
Kp, Dp, Pp, Fr = S("Kp = tan²(45 + φ'2/2)"), S("Profundidad para Pp"), S("Pp = ½Kpγ2D² + 2c'2√Kp D"), \
    S("ΣV tan(k1φ'2) + B k2 c'2")
FSd2 = S("FS sin Pp")
P("La componente horizontal del empuje intenta deslizar el muro sobre su base. Resisten la fricción y la adhesión "
  "en la base y el empuje pasivo Pp del suelo frente a la puntera.")
fig, ax = plt.subplots(figsize=(7.6, 5.0))
draw_base(ax)
arrow(ax, (B_ + 1.4, Hp / 3), (B_ + 0.02, Hp / 3), text=f"Ph = {Ph:.1f}", tpos=(B_ + 1.3, Hp / 3 + 0.3))
sp = 0.9
ax.add_patch(Polygon([(0, Dp), (0, 0), (-sp, 0), (-sp * 0.35, Dp)], closed=True, fc="#A9D18E", alpha=0.6,
                     ec="#548235", zorder=4))
arrow(ax, (-1.4, Dp / 3), (-0.02, Dp / 3), color="#548235", text=f"Pp = {Pp:.1f}", tpos=(-1.7, Dp / 3 + 0.35))
for xx in np.linspace(0.3, B_ - 0.3, 6):
    arrow(ax, (xx + 0.35, -0.12), (xx - 0.15, -0.12), color="#2F5597", lw=1.0)
ax.text(B_ / 2, -0.55, "R' = ΣV tan δ' + B c'a   (fricción + adhesión en la base)", color="#2F5597",
        ha="center", fontsize=8)
ax.set_xlim(-2.4, B_ + 2.0)
ax.set_ylim(-1.0, Hp + 0.5)
fig_img(fig, 12.5, "Figura 6.1 — Fuerzas horizontales: empuje Ph contra fricción/adhesión en la base y pasivo Pp.")
eq(r"K_p=\tan^2\left(45^\circ+\frac{\phi'_2}{2}\right)=\tan^2\left(45^\circ+\frac{%.0f^\circ}{2}\right)=%.3f"
   % (soil["phi2"], Kp))
eq(r"P_p=\frac{1}{2}K_p\gamma_2 D^2+2c'_2\sqrt{K_p}\,D=\frac{1}{2}(%.3f)(%.2f)(%.2f)^2+2(%.1f)\sqrt{%.3f}(%.2f)"
   r"=%.2f\ \mathrm{kN/m}" % (Kp, soil["g2"], Dp, soil["c2"], Kp, Dp, Pp), 11, 16)
eq(r"\Sigma V\tan(k_1\phi'_2)+B\,k_2\,c'_2=%.2f\tan(%.3f\times %.0f^\circ)+%.2f(%.3f)(%.1f)=%.2f\ \mathrm{kN/m}"
   % (SV, fac["k1"], soil["phi2"], B_, fac["k2"], soil["c2"], Fr), 11, 16)
eq(r"FS_{desl}=\frac{\Sigma V\tan(k_1\phi'_2)+B k_2 c'_2+P_p}{P_a\cos\alpha}=\frac{%.2f+%.2f}{%.2f}=%.2f\ \geq %.1f"
   % (Fr, Pp, Ph, FSd1, fac["FSd"]))
P("Resultado: " + ok(FSd1 >= fac["FSd"]) + f". Sin contar Pp, FS = {FSd2:.2f} "
  + ("(también cumple)." if FSd2 >= fac["FSd"] else "(no cumpliría: el muro depende del pasivo frente a la puntera, "
                                                    "que debe garantizarse que no se excave)."))
P("Si no cumple: alargar el talón, agregar un <b>dentellón</b> (en INPUTS, columna «D1 con dentellón»: Pp se calcula "
  "con D1), o usar un anclaje.")
XL("Kp = tan²(45 + φ'2/2)", "Pp = ½Kpγ2D² + 2c'2√Kp D", "FS con Pp")
story.append(PageBreak())

# ================================================================== 7. PRESIONES SOBRE EL SUELO
H1("7. Presiones sobre el suelo de fundación")
e, B6 = S("e = B/2 − (ΣMR−ΣMo)/ΣV"), S("B/6")
qmax, qmin = S("q punta = ΣV/B (1+6e/B)"), S("q talón = ΣV/B (1−6e/B)")
P("La resultante de las fuerzas verticales no cae en el centro de la base: está desplazada una excentricidad e. "
  "Con e ≤ B/6 (dentro del tercio medio) toda la base queda comprimida y la presión es trapezoidal.")
xE = SMR and (SMR - Mo) / SV
fig, ax = plt.subplots(figsize=(7.6, 3.6))
draw_base(ax, soil_back=False, soil_front=False)
ax.add_patch(Rectangle((B_ / 3, -0.28), B_ / 3, 0.22, fc="#A9D18E", ec="#548235", alpha=0.7))
ax.text(B_ / 2, -0.55, "tercio medio (B/3 a 2B/3)", ha="center", fontsize=8.5, color="#385723")
arrow(ax, (xE, hz + 2.0), (xE, 0.02), color=C_FORCE, text=f"R = ΣV = {SV:.1f} kN/m", tpos=(xE, hz + 2.25))
ax.plot([B_ / 2, B_ / 2], [-0.1, hz + 1.2], ":", color="k", lw=0.9)
ax.text(B_ / 2 + 0.05, hz + 1.15, "B/2", fontsize=8)
dim(ax, (xE, hz + 0.75), (B_ / 2, hz + 0.75), f"e = {e:.3f} m", fs=9)
dim(ax, (0, hz + 1.5), (xE, hz + 1.5), f"x̄ = {xE:.3f} m", fs=9)
ax.set_ylim(-0.8, hz + 2.5)
ax.set_xlim(-0.5, B_ + 0.5)
fig_img(fig, 13, "Figura 7.1 — Ubicación de la resultante R respecto a la punta C y excentricidad e.")
fig, ax = plt.subplots(figsize=(7.6, 2.6))
xs = np.array([0, B_])
qs = np.array([qmax, qmin])
ax.fill_between(xs, 0, -qs, color=C_PRESS, alpha=0.35)
ax.plot(xs, -qs, color="#1F4E79")
for xx in np.linspace(0.1, B_ - 0.1, 12):
    q = qmax + (qmin - qmax) * xx / B_
    ax.annotate("", xy=(xx, 0), xytext=(xx, -q), arrowprops=dict(arrowstyle="-|>", color=C_PRESS, lw=0.7))
ax.text(0.05, -qmax * 1.08, f"q punta = {qmax:.1f} kPa", fontsize=8, color="#1F4E79")
ax.text(B_ - 0.05, -qmin - qmax * 0.12, f"q talón = {qmin:.1f} kPa", fontsize=8, color="#1F4E79", ha="right")
ax.axhline(-soil["qadm"], color="#C00000", ls="--", lw=0.9)
ax.text(B_, -soil["qadm"] * 1.03, f"q adm = {soil['qadm']:.0f}", color="#C00000", fontsize=7.5, ha="right", va="top")
ax.set_ylim(-max(qmax, soil["qadm"]) * 1.25, qmax * 0.1)
ax.axis("off")
fig_img(fig, 13, "Figura 7.2 — Presión de contacto trapezoidal bajo la base (servicio) y q admisible.")
eq(r"\bar{x}=\frac{\Sigma M_R-\Sigma M_o}{\Sigma V}=\frac{%.2f-%.2f}{%.2f}=%.3f\ \mathrm{m}\qquad "
   r"e=\frac{B}{2}-\bar{x}=%.3f\ \mathrm{m}" % (SMR, Mo, SV, xE, e))
eq(r"e=%.3f\ \mathrm{m}\ \leq\ \frac{B}{6}=%.3f\ \mathrm{m}" % (e, B6))
eq(r"q_{punta/talón}=\frac{\Sigma V}{B}\left(1\pm\frac{6e}{B}\right)=\frac{%.2f}{%.2f}\left(1\pm\frac{6(%.3f)}{%.2f}"
   r"\right)=%.2f\ /\ %.2f\ \mathrm{kPa}" % (SV, B_, e, B_, qmax, qmin))
P("Resultado: e ≤ B/6 " + ok(abs(e) <= B6) + f"; q máx = {qmax:.1f} kPa ≤ q adm = {soil['qadm']:.0f} kPa "
  + ok(qmax <= soil["qadm"]) + ". Si e > B/6, q talón sería negativa (tensión): hay que redimensionar.")
XL("e = B/2 − (ΣMR−ΣMo)/ΣV", "q punta = ΣV/B (1+6e/B)", "q talón = ΣV/B (1−6e/B)")
story.append(PageBreak())

# ================================================================== 8. SISMO
H1("8. Condición sísmica — Mononobe-Okabe")
kh = S("kh")
P("Durante un sismo la cuña de suelo recibe fuerzas de inercia kh·W (horizontal) y kv·W (vertical), y el empuje "
  "aumenta. El método de Mononobe-Okabe (Das, ec. 7.42) da el empuje total Pae; su incremento ΔPae = Pae − Pa "
  "actúa más arriba, a 0.6H' de la base.")
fig, ax = plt.subplots(figsize=(7.4, 4.8))
draw_base(ax)
arrow(ax, (B_ + 1.4, Hp / 3), (B_ + 0.02, Hp / 3), color="#7030A0", text="Pa (H'/3)", tpos=(B_ + 1.4, Hp / 3 - 0.35))
arrow(ax, (B_ + 1.4, 0.6 * Hp), (B_ + 0.02, 0.6 * Hp), color=C_FORCE, text="ΔPae (0.6H')", tpos=(B_ + 1.4, 0.6 * Hp + 0.35))
ax.plot([xb + Lt * 0.3, B_ + 1.2], [hz + 0.2, hz + H2_ + (Lt + 1.2) * ta], ":", color="#8C6D31")
arrow(ax, (xb + Lt * 0.75 + 0.6, hz + H2_ * 0.75), (xb + Lt * 0.75 - 0.1, hz + H2_ * 0.75), color="#BF8F00",
      text="kh·W", tpos=(xb + Lt * 0.75 + 0.6, hz + H2_ * 0.75 + 0.3), fs=7.5)
ax.set_xlim(-1.6, B_ + 2.3)
ax.set_ylim(-1.0, Hp + 0.6)
fig_img(fig, 12, "Figura 8.1 — Empuje estático Pa a H'/3 e incremento sísmico ΔPae a 0.6H' (Das, fig. 7.16).")
eq(r"\theta'=\tan^{-1}\frac{k_h}{1-k_v}\qquad P_{ae}=\frac{1}{2}\gamma_1 H'^2(1-k_v)K_{ae}", 11.5)
eq(r"K_{ae}=\frac{\sin^2(\phi'+\beta-\theta')}{\cos\theta'\sin^2\beta\,\sin(\beta-\theta'-\delta')\left[1+\sqrt{"
   r"\frac{\sin(\phi'+\delta')\sin(\phi'-\theta'-\alpha)}{\sin(\beta-\delta'-\theta')\sin(\alpha+\beta)}}\right]^2}", 13)
eq(r"\bar{z}=\frac{0.6H'\,\Delta P_{ae}+\frac{H'}{3}P_a}{P_{ae}}\quad\mathrm{(ec.\ 7.49)}", 11.5)
if kh and kh > 0:
    P(f"Con kh = {kh:.3f}: θ' = {S(chr(952) + chr(39) + ' = atan(kh/(1−kv))'):.2f}°, Kae = {S('Kae (β = 90°)'):.4f}, "
      f"Pae = {S('Pae = ½γ1H' + chr(39) + '²(1−kv)Kae'):.2f} kN/m, z̄ = {S('z̄ (ec. 7.49)'):.3f} m. "
      f"FS volcamiento sísmico = {S('FS volcamiento sísmico'):.2f}; FS deslizamiento sísmico = "
      f"{S('FS deslizamiento sísmico'):.2f}.")
    XL("Kae (β = 90°)", "z̄ (ec. 7.49)", "FS volcamiento sísmico", "FS deslizamiento sísmico")
else:
    P(f"En el muro {WALL} se dejó <b>kh = 0</b>, así que la hoja muestra «No aplica». Para activar la revisión, "
      "escriba kh (y kv) en INPUTS. Como referencia, el muro <b>M2</b> del archivo tiene kh = 0.15 y la hoja calcula "
      "Kae, Pae, z̄ y los factores de seguridad sísmicos.")
P("Los FS mínimos sísmicos de la hoja (1.5 volcamiento, 1.1 deslizamiento) son valores usuales y editables; "
  "confírmelos con el docente o la NSR-10. La hoja no incluye la inercia del propio muro (kh·W del concreto).",
  st_small)
story.append(PageBreak())

# ================================================================== 9. VÁSTAGO
H1("9. Diseño estructural del vástago")
Vu, Mu = S("Vu = 1.6·Ph"), S("Mu = 1.6·ΣMo")
dv, Rn, rho, rhod, As = S("d = h − rec"), S("Rn = Mu/(φ b d²)"), S("ρ requerida"), S("ρ diseño = máx(ρ, ρmín)"), \
    S("As = ρ b d")
Vc, phiVc = S("Vc = 0.17λ√f'c b d"), S("φVc")
P("El vástago trabaja como una viga en voladizo empotrada en la zapata, cargada por la presión del relleno. "
  "Como en el documento, se usa el empuje sobre toda la altura H' con el factor 1.6 (NSR-10 B.2.4-2, carga H). "
  "Es conservador: la sección crítica exacta está en la base del vástago.")
z = np.linspace(0, Hp, 120)
kk = soil["g1"] * Ka * math.cos(math.radians(ang)) * fac["fH"]
Vz, Mz = kk * z ** 2 / 2, kk * z ** 3 / 6
fig, axs = plt.subplots(1, 3, figsize=(8.6, 4.4), sharey=True)
axs[0].fill_betweenx(Hp - z, 0, kk * z, color=C_PRESS, alpha=0.4)
axs[0].plot(kk * z, Hp - z, color="#1F4E79")
axs[0].set_title("Presión mayorada\nwu (kPa)", fontsize=8.5)
axs[1].fill_betweenx(Hp - z, 0, Vz, color="#F4B183", alpha=0.6)
axs[1].plot(Vz, Hp - z, color="#C55A11")
axs[1].set_title(f"Cortante Vu (kN/m)\nmáx = {Vz[-1]:.1f}", fontsize=8.5)
axs[2].fill_betweenx(Hp - z, 0, Mz, color="#A9D18E", alpha=0.6)
axs[2].plot(Mz, Hp - z, color="#548235")
axs[2].set_title(f"Momento Mu (kN·m/m)\nmáx = {Mz[-1]:.1f}", fontsize=8.5)
axs[0].set_ylabel("altura sobre la base (m)")
for a in axs:
    a.grid(alpha=0.3)
    a.axvline(0, color="k", lw=0.8)
fig.tight_layout()
fig_img(fig, 15, "Figura 9.1 — Carga, cortante y momento del vástago (factor 1.6). Los máximos coinciden con Vu y Mu "
                 "de la hoja.")
assert abs(Vz[-1] - Vu) < 0.5 and abs(Mz[-1] - Mu) < 0.5, "diagrama del vástago no coincide con el Excel"
H2("9.1 Flexión (b = 1.0 m)")
eq(r"V_u=1.6\,P_h=1.6(%.2f)=%.2f\ \mathrm{kN/m}\qquad M_u=1.6\,\Sigma M_o=1.6(%.2f)=%.2f\ \mathrm{kN\cdot m/m}"
   % (Ph, Vu, Mo, Mu), 11, 16)
eq(r"d=h-r=%.2f-%.3f=%.3f\ \mathrm{m}\qquad R_n=\frac{M_u}{\phi b d^2}=\frac{%.4f\ \mathrm{MN\cdot m}}{%.2f(1.0)(%.3f)^2}"
   r"=%.3f\ \mathrm{MPa}" % (tb, mat["rec"], dv, Mu / 1000, fac["phif"], dv, Rn), 11, 16)
eq(r"\rho=\frac{0.85f'_c}{f_y}\left(1-\sqrt{1-\frac{2R_n}{0.85f'_c}}\right)=\frac{0.85(%.0f)}{%.0f}\left(1-\sqrt{1-"
   r"\frac{2(%.3f)}{0.85(%.0f)}}\right)=%.5f" % (mat["fc"], mat["fy"], Rn, mat["fc"], rho), 11, 16)
eq(r"A_s=\rho\,b\,d=%.5f(100)(%.1f)=%.2f\ \mathrm{cm^2/m}" % (rhod, dv * 100, As))
P(f"Separación de barras: s = A<sub>barra</sub>/A<sub>s</sub>, redondeada hacia abajo al centímetro y limitada a "
  f"3h y 45 cm (NSR-10 C.14.3.5). Opciones: <b>{S('Refuerzo opción 1')}</b> o <b>{S('Refuerzo opción 2')}</b>. "
  f"La hoja también verifica ρ ≤ ρ máx (εt ≥ 0.005).")
XL("Mu = 1.6·ΣMo", "Rn = Mu/(φ b d²)", "ρ requerida", "As = ρ b d", "Refuerzo opción 1")
H2("9.2 Cortante")
eq(r"V_c=0.17\lambda\sqrt{f'_c}\,b\,d=0.17(%.1f)\sqrt{%.0f}(1000)(%.0f)=%.2f\ \mathrm{kN}\qquad\phi V_c=%.2f(%.2f)=%.2f"
   r"\ \mathrm{kN}" % (mat["lam"], mat["fc"], dv * 1000, Vc, fac["phiv"], Vc, phiVc), 11, 16)
P(f"V<sub>u</sub> = {Vu:.2f} kN ≤ φV<sub>c</sub> = {phiVc:.2f} kN → " + ok(Vu <= phiVc)
  + ". El concreto resiste solo el cortante; no se requieren estribos (lo usual en muros).")
XL("Vc = 0.17λ√f'c b d", "φVc")
story.append(PageBreak())

# ================================================================== 10. ZAPATA
H1("10. Diseño estructural de la zapata")
SVu, SMRu = tab[-1][8], tab[-1][9]
Mou, eu = S("Mou = 1.6·ΣMo"), S("eu = B/2 − (ΣMRu−Mou)/ΣVu")
qmu, qnu, qp, qt = S("qu punta"), S("qu talón"), S("qu cara frontal vástago"), S("qu cara posterior vástago")
Vp, Vt = S("Vu puntera"), S("Vu talón (− hacia abajo)")
Mp, Mt = S("Mu puntera"), S("Mu talón")
P("Con las cargas mayoradas de la tabla 8.1 (columnas Wu y Mu) se calcula la presión última bajo la base. "
  "La puntera y el talón se diseñan como voladizos que salen de las caras del vástago.")
eq(r"e_u=\frac{B}{2}-\frac{\Sigma M_{Ru}-1.6\Sigma M_o}{\Sigma V_u}=\frac{%.2f}{2}-\frac{%.2f-%.2f}{%.2f}=%.3f\ "
   r"\mathrm{m}" % (B_, SMRu, Mou, SVu, eu), 11, 16)
eq(r"q_{u}=\frac{\Sigma V_u}{B}\left(1\pm\frac{6e_u}{B}\right)=%.2f\ /\ %.2f\ \mathrm{kPa}\qquad q_{cara\ frontal}=%.2f"
   r"\qquad q_{cara\ posterior}=%.2f" % (qmu, qnu, qp, qt), 11, 16)
XL("eu = B/2 − (ΣMRu−Mou)/ΣVu", "qu punta", "qu talón", "qu cara frontal vástago")
# diagramas a lo largo de la base
x = np.linspace(0, B_, 400)
qx = qmu + (qnu - qmu) * x / B_
wself = fac["fD"] * mat["gc"] * hz
wsoil = np.where(x > xb, fac["fH"] * soil["g1"] * (H2_ + (x - xb) * ta), 0.0)
net = qx - wself - wsoil  # hacia arriba +
fig, ax = plt.subplots(figsize=(7.8, 3.6))
draw_base(ax, soil_back=False, soil_front=False)
for xx in np.linspace(0.05, B_ - 0.05, 16):
    q = qmu + (qnu - qmu) * xx / B_
    ax.annotate("", xy=(xx, 0), xytext=(xx, -q / qmu * 1.2), arrowprops=dict(arrowstyle="-|>", color=C_PRESS, lw=0.8))
ax.plot([0, B_], [-1.2, -qnu / qmu * 1.2], color="#1F4E79")
ax.text(0, -1.45, f"{qmu:.1f}", fontsize=7.5, color="#1F4E79")
ax.text(B_, -qnu / qmu * 1.2 - 0.25, f"{qnu:.1f} kPa", fontsize=7.5, color="#1F4E79", ha="right")
ax.add_patch(Rectangle((xb, hz), Lt, 1.0, fc=C_FILL, ec="none", alpha=0.6))
ax.text(xb + Lt / 2, hz + 0.5, f"W4u + W5u = {tab[3][8] + tab[4][8]:.1f} kN/m (hacia abajo)", ha="center", fontsize=7)
ax.text(Lp / 2, hz + 0.35, "puntera", ha="center", fontsize=8, fontweight="bold")
ax.set_ylim(-1.8, hz + 1.3)
ax.set_xlim(-0.3, B_ + 0.3)
fig_img(fig, 13, "Figura 10.1 — Presión última (mayorada) bajo la base y carga del relleno sobre el talón.")
# cortante y momento por voladizos (desde cada extremo hacia la cara del vástago)
V = np.zeros_like(x)
M = np.zeros_like(x)
dx = x[1] - x[0]
mt = x <= Lp
cum = np.cumsum(net[mt]) * dx
V[mt] = cum
M[mt] = np.array([np.sum(net[mt][:i + 1] * (x[i] - x[mt][:i + 1])) * dx for i in range(mt.sum())])
ht = x >= xb
xr = x[ht][::-1]
nr = net[ht][::-1]
cum = np.cumsum(nr) * dx
V[ht] = -cum[::-1]
M[ht] = np.array([np.sum(nr[:i + 1] * (xr[:i + 1] - xr[i])) * dx for i in range(len(xr))])[::-1]
V[~mt & ~ht] = np.nan
M[~mt & ~ht] = np.nan
fig, axs = plt.subplots(2, 1, figsize=(7.8, 5.2), sharex=True)
axs = [None, axs[0], axs[1]]
ax = axs[1]
ax.fill_between(x, 0, V, color="#F4B183", alpha=0.6)
ax.plot(x, V, color="#C55A11")
ax.set_ylabel("Vu (kN/m)")
ax.text(Lp, np.nanmax(V[mt]), f" Vp = {Vp:.1f}", fontsize=7.5, va="bottom")
ax.text(xb, V[ht][0], f" VT = {Vt:.1f}", fontsize=7.5, va="top")
ax = axs[2]
ax.fill_between(x, 0, M, color="#A9D18E", alpha=0.6)
ax.plot(x, M, color="#548235")
ax.set_ylabel("Mu (kN·m/m)")
ax.text(Lp, M[mt][-1], f" Mp = {Mp:.1f}", fontsize=7.5, va="bottom")
ax.text(xb, M[ht][0], f" MT = {Mt:.1f}", fontsize=7.5, va="top")
ax.set_xlabel("x desde la punta C (m)")
for a in axs[1:]:
    a.grid(alpha=0.3)
    a.axhline(0, color="k", lw=0.8)
    a.axvspan(Lp, xb, color="#D9D9D9", alpha=0.5)
fig.tight_layout()
fig_img(fig, 14, "Figura 10.2 — Cortante y momento últimos de la puntera y del talón "
                 "(franja gris = vástago). M &gt; 0 tensiona la cara inferior.")
assert abs(M[mt][-1] - Mp) < 1.0 and abs(M[ht][0] - Mt) < 1.5, "diagrama de la zapata no coincide con el Excel"
H2("10.1 Puntera (voladizo hacia la izquierda — acero inferior)")
eq(r"M_p=q_{cf}\frac{L_p^2}{2}+(q_{u,punta}-q_{cf})\frac{L_p}{2}\cdot\frac{2L_p}{3}-1.2\gamma_c H_3\frac{L_p^2}{2}"
   r"=%.2f\ \mathrm{kN\cdot m/m}" % Mp, 11, 16)
eq(r"V_p=\frac{q_{cf}+q_{u,punta}}{2}L_p-1.2\gamma_c H_3 L_p=%.2f\ \mathrm{kN/m}" % Vp, 11, 16)
P(f"Flexión: Rn = {S('Rn = Mu/(φ b d²)', 1):.3f} MPa → ρ = {S('ρ requerida', 1):.5f}; se usa ρ = máx(ρ, ρmín) = "
  f"{S('ρ diseño = máx(ρ, ρmín)', 1):.5f} → As = {S('As = ρ b d', 1):.2f} cm²/m → <b>{S('Refuerzo opción 1', 1)}</b> "
  f"o <b>{S('Refuerzo opción 2', 1)}</b>.")
XL(("Mu puntera", 0), ("As = ρ b d", 1), ("Refuerzo opción 1", 1))
H2("10.2 Talón (voladizo hacia la derecha — acero superior)")
eq(r"M_T=q_{u,talón}\frac{L_t^2}{2}+(q_{cp}-q_{u,talón})\frac{L_t}{2}\cdot\frac{L_t}{3}-W_{5u}\frac{2L_t}{3}-W_{4u}"
   r"\frac{L_t}{2}-1.2\gamma_c H_3\frac{L_t^2}{2}=%.2f\ \mathrm{kN\cdot m/m}" % Mt, 10.5, 16)
eq(r"V_T=-W_{4u}-W_{5u}-1.2\gamma_c H_3 L_t+\frac{q_{cp}+q_{u,talón}}{2}L_t=%.2f\ \mathrm{kN/m}" % Vt, 11, 16)
P("M<sub>T</sub> negativo significa que el peso del relleno sobre el talón supera la reacción del suelo: el talón "
  "se flexiona hacia abajo y la tensión está en la <b>cara superior</b>. "
  f"Rn = {S('Rn = Mu/(φ b d²)', 2):.3f} MPa → ρ = {S('ρ requerida', 2):.5f} → As = {S('As = ρ b d', 2):.2f} cm²/m → "
  f"<b>{S('Refuerzo opción 1', 2)}</b> o <b>{S('Refuerzo opción 2', 2)}</b>.")
XL(("Mu talón", 0), ("As = ρ b d", 2), ("Refuerzo opción 1", 2))
H2("10.3 Cortante en la zapata")
zv = S("φVc = φ·0.17λ√f'c b d")
eq(r"\phi V_c=0.75(0.17)\lambda\sqrt{f'_c}\,b\,d=%.2f\ \mathrm{kN/m}\ \geq\ \max(|V_p|,|V_T|)=%.2f" %
   (zv, max(abs(Vp), abs(Vt))))
P("Resultado: " + ok(max(abs(Vp), abs(Vt)) <= zv) + " (cortante evaluado en la cara del vástago, conservador).")
story.append(PageBreak())

# ================================================================== 11. DESPIECE
H1("11. Esquema de refuerzo")
fig, ax = plt.subplots(figsize=(7.6, 6.6))
draw_base(ax, soil_back=False, soil_front=False, wall_color="#EDEDED")
r_ = mat["rec"]
ax.plot([xb - r_, xb - r_], [r_ + 0.05, hz + H2_ - 0.05], color="#C00000", lw=2.2)          # vástago cara relleno
ax.plot([xb - r_, xb - r_ - 0.0, Lp + 0.2], [r_ + 0.05, r_ + 0.05, r_ + 0.05], color="#C00000", lw=2.2)  # anclaje
ax.plot([0.07, B_ - 0.07], [r_ * 0.9, r_ * 0.9], color="#2F5597", lw=2.2)                     # puntera inferior
ax.plot([xb - 0.3, B_ - 0.07], [hz - r_, hz - r_], color="#548235", lw=2.2)                   # talón superior
ax.plot([xf_top + 0.06, Lp + 0.06], [hz + H2_ - 0.06, hz + 0.05], color="#7F7F7F", lw=1.2, ls="--")
ax.annotate(f"Vástago: {S('Refuerzo opción 1')}\n(cara del relleno, vertical)", xy=(xb - r_, hz + H2_ * 0.55),
            xytext=(xb + 0.6, hz + H2_ * 0.7), fontsize=8, color="#C00000",
            arrowprops=dict(arrowstyle="-|>", color="#C00000"))
ax.annotate(f"Talón: {S('Refuerzo opción 1', 2)}\n(cara superior)", xy=(xb + Lt * 0.6, hz - r_),
            xytext=(xb + 0.4, hz + 1.6), fontsize=8, color="#548235",
            arrowprops=dict(arrowstyle="-|>", color="#548235"))
ax.annotate(f"Puntera: {S('Refuerzo opción 1', 1)}\n(cara inferior)", xy=(Lp * 0.5, r_ * 0.9),
            xytext=(-1.6, -1.0), fontsize=8, color="#2F5597", arrowprops=dict(arrowstyle="-|>", color="#2F5597"))
ax.text(xf_top - 1.6, hz + H2_ * 0.45, "cara frontal:\nrefuerzo de\nretracción\n(no calculado)", fontsize=7,
        color="#595959")
ax.set_xlim(-2.0, B_ + 2.4)
ax.set_ylim(-1.5, Hp + 0.4)
fig_img(fig, 13, "Figura 11.1 — Ubicación del refuerzo principal calculado. Las barras van del lado en tensión.")
P("El acero del vástago va en la cara del relleno (tensión por el empuje) y se ancla en la zapata; el de la puntera "
  "en la cara inferior y el del talón en la cara superior. Falta definir, según NSR-10: refuerzo horizontal y de "
  "retracción del vástago (C.14.3), longitudes de desarrollo y empalmes (C.12) y el refuerzo transversal de la "
  "zapata (ρ mínima por temperatura, C.7.12).")

# ================================================================== 12. NOTAS
H1("12. Notas y diferencias con el ejemplo del documento")
notes = [
    "Los valores de esta memoria coinciden con el ejemplo del documento (Das 7ed): FS volcamiento 2.95, "
    "FS deslizamiento 2.70, e = 0.41 m, q = 190 / 45 kPa, As del vástago 26.71 cm² (No.6 @ 0.10 m), φVc = 425 kN.",
    "En la zapata hay diferencias pequeñas: el documento redondea e<sub>u</sub> a 0.40 m antes de calcular las "
    "presiones; la hoja usa el valor exacto.",
    "En el cálculo de M<sub>p</sub> el documento no mayora el peso propio de la puntera, pero sí lo hace en V<sub>P</sub>; "
    "la hoja usa 1.2 en ambos (consistente con NSR-10 B.2.4-2).",
    "Ka: la ecuación 7.26 da 0.3495 para φ' = 30°, α = 10°; el ejemplo usa 0.3532 (de tabla). Por eso M1 tiene "
    "«Ka manual» = 0.3532.",
    "Posibles erratas tipográficas del documento: en la pág. 4 parece faltar el término −2 sen φ' cos ψ<sub>a</sub> "
    "dentro de la raíz; en la pág. 19, P<sub>a(2)</sub> debería contener H'² − (H' − D')².",
    "La hoja aplica a muros en voladizo con relleno granular (c'1 = 0).",
]
for n_ in notes:
    P("• " + n_)


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("DV", 7.5)
    canvas.setFillColor(colors.grey)
    canvas.drawString(2 * cm, 1.2 * cm, f"Memoria de cálculo — Muro {WALL} — MEMORIA_CALCULO_MUROS.xlsx")
    canvas.drawRightString(letter[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(1.2)
    canvas.line(2 * cm, letter[1] - 1.4 * cm, letter[0] - 2 * cm, letter[1] - 1.4 * cm)
    canvas.restoreState()


doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                        bottomMargin=1.8 * cm, title=f"Memoria de cálculo — Muro {WALL}",
                        author="Memoria de muros (generada desde Excel)")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print("saved", OUT)
