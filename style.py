"""Charte graphique 6t : couleurs, polices, logo et éléments de mise en forme."""
import base64
from html import escape
from pathlib import Path

import streamlit as st

# Palette 6t-2023
MARINE = "#060D53"   # texte, titres
VIOLET = "#6246D3"   # couleur principale
ORANGE = "#FF9433"
TEAL = "#2A9C8E"
BEIGE = "#EEECE1"

# Titres : Brandon Grotesque Bold (si installée sur le poste, sinon Montserrat) ; texte : Inter
POLICE = 'Inter, "Helvetica Neue", Arial, sans-serif'
TITRES = '"6tTitre", Montserrat, "Helvetica Neue", Arial, sans-serif'

LOGO = Path(__file__).resolve().parent / "assets" / "logo_6t.png"

CSS = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Montserrat:wght@600;700&display=swap" rel="stylesheet">
<style>
  @font-face { font-family: "6tTitre"; font-weight: 700; font-style: normal;
               src: local("Brandon Grotesque Bold"), local("BrandonGrotesque-Bold"); }
  html, body, [class*="css"], .stMarkdown, button, input { font-family: @POLICE !important; }
  [data-testid="stMarkdownContainer"] :is(p, li, table.sbp) { font-family: @POLICE !important; }
  h1, h2, h3, [data-testid="stMarkdownContainer"] :is(h1, h2, h3) {
    font-family: @TITRES !important; font-weight: 700 !important; color: @MARINE; }
  .stApp { background: #F8F8FF; }
  .block-container { padding-top: 3rem; max-width: 1480px; }
  [data-testid="stSidebar"] { background: white; border-right: 1px solid @BEIGE; }
  [data-testid="stSidebar"] h1 { font-size: 1.2rem; text-transform: uppercase; letter-spacing: 2px; }

  .hero { display: flex; align-items: center; gap: 1.6rem; color: white; padding: 1.5rem 1.9rem;
          border-radius: 12px; margin-bottom: 1.1rem; box-shadow: 0 6px 18px rgba(98,70,211,.25);
          background: linear-gradient(120deg, @MARINE 0%, #2B2A8F 55%, @VIOLET 100%); }
  .hero-logo { background: white; border-radius: 14px; padding: .6rem; flex: none; line-height: 0;
               box-shadow: 0 2px 8px rgba(6,13,83,.25); }
  .hero-logo img { height: 74px; width: auto; display: block; }
  .hero h1 { color: white; margin: 0; font-size: 1.55rem; text-transform: uppercase;
             letter-spacing: 3px; padding: 0; line-height: 1.3; }
  .hero p { margin: .4rem 0 0 0; opacity: .92; font-size: 1.02rem; }

  .stTabs [data-baseweb="tab-list"] { gap: 1.4rem; border-bottom: 1px solid @BEIGE; }
  .stTabs [data-baseweb="tab"] { font-family: @TITRES !important; font-weight: 700; font-size: 1rem; }

  .bloc { border-radius: 12px; padding: .9rem .8rem; margin-bottom: 1rem; }
  .bloc.b1 { background: rgba(42,156,142,.12); border: 1px solid rgba(42,156,142,.40); }
  .bloc.b2 { background: #EFECFB; border: 1px solid rgba(98,70,211,.32); }
  .etape { display: flex; align-items: flex-start; gap: .6rem; margin-bottom: .5rem; }
  .etape .num { font-family: @TITRES; width: 1.8rem; height: 1.8rem; border-radius: 50%; color: white;
                display: flex; align-items: center; justify-content: center; font-weight: 700; flex: none; }
  .b1 .num { background: @TEAL; }
  .b2 .num { background: @VIOLET; }
  .etape .t { font-family: @TITRES; font-weight: 700; font-size: .85rem; color: @MARINE;
              text-transform: uppercase; letter-spacing: 1px; line-height: 1.35; }
  .soustitre { color: #5C628F; font-size: .78rem; margin-bottom: .5rem; }
  table.sbp { width: 100%; border-collapse: collapse; font-size: .84rem; background: white;
              border-radius: 8px; overflow: hidden; margin: 0; }
  table.sbp th, table.sbp td { border: 0; text-align: right; padding: .4rem .5rem; }
  table.sbp th { color: #5C628F; font-weight: 700; border-bottom: 2px solid @BEIGE; }
  table.sbp td { border-bottom: 1px solid #F4F2EA; font-weight: 700; color: @MARINE; }
  table.sbp th:first-child, table.sbp td:first-child { text-align: left; font-weight: 600; }

  /* carte centrée dans la page */
  iframe[title="streamlit_folium.st_folium"] {
    display: block; margin: 0 auto; width: 1000px !important; max-width: 100%; }
  .pied { color: #8A90B5; font-size: .8rem; text-align: center; margin: 2.5rem 0 .5rem 0; }
</style>
"""


def appliquer_style():
    css = CSS
    for cle, val in {"@POLICE": POLICE, "@TITRES": TITRES, "@MARINE": MARINE,
                     "@VIOLET": VIOLET, "@TEAL": TEAL, "@BEIGE": BEIGE}.items():
        css = css.replace(cle, val)
    # une ligne vide casse le bloc HTML
    css = "\n".join(ligne for ligne in css.splitlines() if ligne.strip())
    st.markdown(css, unsafe_allow_html=True)


def entete(titre, *paragraphes):
    logo = base64.b64encode(LOGO.read_bytes()).decode()
    st.markdown(
        "<div class='hero'>"
        f"<div class='hero-logo'><img src='data:image/png;base64,{logo}' alt='6t'></div>"
        f"<div><h1>{titre}</h1>"
        + "".join(f"<p>{p}</p>" for p in paragraphes)
        + "</div></div>",
        unsafe_allow_html=True,
    )


def bloc_resultats(numero, titre, sous_titre, lignes):
    """lignes : liste de couples (indicateur, valeur déjà mise en forme)."""
    corps = "".join(f"<tr><td>{escape(str(i))}</td><td>{escape(str(v))}</td></tr>"
                    for i, v in lignes)
    st.markdown(
        f"<div class='bloc b{numero}'><div class='etape'><div class='num'>{numero}</div>"
        f"<div class='t'>{escape(titre)}</div></div>"
        f"<div class='soustitre'>{escape(sous_titre)}</div>"
        "<table class='sbp'><tr><th>Indicateur</th><th>Valeur</th></tr>"
        f"{corps}</table></div>",
        unsafe_allow_html=True,
    )


def pied_de_page(texte):
    st.markdown(f"<div class='pied'>{escape(texte)}</div>", unsafe_allow_html=True)
