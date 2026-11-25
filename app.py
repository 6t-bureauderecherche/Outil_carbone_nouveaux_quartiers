#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 20 12:19:11 2023

@author: 6tchmacbook
"""
#------------------------------------------------------------------------------
# 0. Import packages
from typing import List

import folium
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium

import pandas as pd
import geopandas as gpd

from shapely.geometry import Polygon

import datetime

from io import BytesIO
from openpyxl.styles import Font

from style import appliquer_style, entete, bloc_resultats, pied_de_page

import warnings
warnings.filterwarnings("ignore", "is_categorical_dtype")

#------------------------------------------------------------------------------
# 1. Functions
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# 1.1. Set basemap and add draw controls
def _show_map(center: List[float], zoom: int) -> folium.Map:
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        control_scale=True,
        tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        attr='Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)',  # noqa: E501
    )
    Draw(
        export=False,
        position="topleft",
        draw_options={
            "polyline": False,
            "poly": False,
            "circle": False,
            "polygon": True,
            "marker": False,
            "circlemarker": False,
            "rectangle": False,
        },
    ).add_to(m)
    return m
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# 1.2. User drawing to geodataframe
def _drawing_to_gdf(output):
    polygon = output['last_active_drawing']['geometry']['coordinates'][0]
    polygon_geom = Polygon(polygon)
    last_polygon = gpd.GeoDataFrame(index=[0], crs='epsg:4326', 
                                    geometry=[polygon_geom])
    return last_polygon

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# 1.3. Check if drawing in area and compute average
def drawing_in_boundary(grid,drawing):
    grid_limits = grid.dissolve()
    if grid_limits.contains(drawing.geometry)[0]:
        return True

@st.cache_data(show_spinner = False)
def fetch_data(url):
    data = gpd.read_file(url)
    return data
    
def _compute_avg(grid,drawing,progress_bar):
    if drawing.geometry is None:
        st.sidebar.warning("⛔️  Dessinez d'abord un polygone sur la carte !")
    
    # Intersect gridded data with user drawing
    drawing_buffer = gpd.GeoDataFrame(index = [0], crs = grid.crs,
                                      geometry = drawing.buffer(500))
    intersection = gpd.overlay(grid, drawing_buffer, how='intersection')
    intersection['intersection_area'] = intersection.area
    intersection['percent_area']=intersection['intersection_area']/intersection['intersection_area'].sum()
    
    # Initialize dict in which aggregated value will be stored
    var_aggr_dict = {}
    i = 0
    var_names = RESULT_VARIABLES
    
    for var_name in var_names:
        i =+ 1 # for progress bar
        
        # Copy intersection to drop values where variable == 0
        df_calc_i = intersection[[var_name,'percent_area']].copy()
        df_calc_i.dropna(inplace=True)
        dtype_calc_i = intersection.dtypes[var_name]
        
        # If user has uploaded geopackage for this layer: compute weighed avg with user data
        if st.session_state[f'{var_name}_uploaded']:
            user_layer_clipped = st.session_state[f'{var_name}_df'][['geometry',
                                                              st.session_state[f'{var_name}_selected_colname']]]
            user_layer_clipped = user_layer_clipped.rename(columns = {st.session_state[f'{var_name}_selected_colname']:var_name})
            intersection_user_layer = gpd.overlay(user_layer_clipped,
                                                  drawing_buffer,
                                                  how = 'intersection')
            intersection_user_layer['intersection_area'] = intersection_user_layer.area
            intersection_user_layer['percent_area'] = intersection_user_layer['intersection_area'] / intersection_user_layer['intersection_area'].sum()
            
            df_calc_i = intersection_user_layer[[var_name,'percent_area']].copy()
            df_calc_i.dropna(inplace=True)
            
            dtype_calc_i = intersection_user_layer.dtypes[var_name]
        
        # Calculate area weighed average
        if len(df_calc_i) > 0: 
            if dtype_calc_i in ['float64','int64']:
                var_i_area_w = df_calc_i[var_name] * df_calc_i['percent_area']
                var_aggr_dict[var_name] = round(var_i_area_w.sum(),3)
            else:
                grouped = df_calc_i.groupby([var_name]).sum()
                var_aggr_dict[var_name] = grouped.idxmax().iloc[0]
            
        else:
            var_aggr_dict[var_name] = intersection[var_name].mean()
        
        # Update progress bar
        progress_bar.progress(55+ i,text = "Calcul en cours de la valeur agrégée" 
                              " des variables territoriales...")
    
    # Make dataframe from dictionary in which aggregated values are stored
    var_aggr_df = pd.DataFrame.from_dict(var_aggr_dict, orient = 'index').reset_index()
    var_aggr_df = var_aggr_df.round(3)
    
    
    # Save results in session state
    st.session_state.aggregated_values = True
    st.session_state.calcul_message = ('success', "Valeurs agrégées calculées !")
    st.session_state.aggregated_values_df = var_aggr_df
    st.session_state.drawing_buffer = drawing_buffer


def _check_area_and_compute_avg(geo_drawing,grid_url, progress_bar: st.progress) -> None: 
    progress_bar.progress(0,text = 'Télécharger variables territoriales...')
    progress_bar.progress(10,text = 'Télécharger variables territoriales...')
    
    grid_data = fetch_data(grid_url)
    
    progress_bar.progress(50,text = 'Télécharger variables territoriales...')
    
    crs = grid_data.crs
    geo_drawing = geo_drawing.to_crs(crs)
    
    progress_bar.progress(55,text = 'Télécharger variables territoriales...')
    
    
    if not drawing_in_boundary(grid_data,geo_drawing):
        st.session_state.calcul_message = (
            'warning',
            "Le polygone dessiné n'est pas situé dans le Canton de Genève, "
            "veuillez vous assurer que cela est le cas.")
        if st.session_state.aggregated_values:
            st.session_state.aggregated_values_df = pd.DataFrame()
        
    else:
        _compute_avg(grid_data, geo_drawing, progress_bar)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# 1.4. Upload geopackage of new layer    
def _set_clicked_uploader(k): 
    
    st.session_state[f'{k}_uploaded'] = True

    if st.session_state[f'{k}_uploaded'] and st.session_state[f'{k}_uploaded_file'] is not None:
        st.session_state[f'{k}_df'] = gpd.read_file(st.session_state[f'{k}_uploaded_file'])
        st.session_state[f'{k}_filename'] = st.session_state[f'{k}_uploaded_file'].name
        st.session_state[f'{k}_colnames'] = list(st.session_state[f'{k}_df'].columns)
        if 'geometry' in st.session_state[f'{k}_colnames']:
            st.session_state[f'{k}_colnames'].remove('geometry')
        
    elif st.session_state[f'{k}_uploaded'] and st.session_state[f'{k}_uploaded_file'] is None:
        _remove_uploaded_layer(k)

def _remove_uploaded_layer(k):
    st.session_state[f'{k}_uploaded'] = False
    st.session_state[f'{k}_filename'] = ''
    st.session_state[f'{k}_df'] = None
    st.session_state[f'{k}_colnames'] = ['','']

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# 1.5. Split aggregated results into the presentation blocks
def _block_table(df, variables):
    # df: first column = variable name, second column = aggregated value
    values = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
    return pd.DataFrame({'Indicateur': [dict_colnames[v] for v in variables],
                         'Valeur': [values.get(v) for v in variables]})

def _format_value(value):
    if pd.isna(value):
        return '–'
    if isinstance(value, str):
        return value
    return f'{round(float(value), 3):.12g}'

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# 1.6. Convert aggregated results dataframe to excel file
def convert_df(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        sheet = writer.book.create_sheet('Résultats')
        for title, variables in RESULT_BLOCKS:
            sheet.append([title])
            sheet.cell(sheet.max_row, 1).font = Font(bold=True)
            sheet.append([RESULT_SUBTITLE])
            sheet.cell(sheet.max_row, 1).font = Font(italic=True)
            table = _block_table(df, variables)
            sheet.append(list(table.columns))
            for cell in sheet[sheet.max_row]:
                cell.font = Font(bold=True)
            for label, value in table.itertuples(index=False):
                sheet.append([label, None if pd.isna(value) else value])
            sheet.append([])
        sheet.column_dimensions['A'].width = 45
        sheet.column_dimensions['B'].width = 18
    return output.getvalue()
    
#------------------------------------------------------------------------------
# 2. Page configuration
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# 2.1. Set parameters
ABOUT = r"""
# Téléchargement de données territoriales
Pour le volet mobilité de l'outil de quantification d'émissions de carbone des nouveaux quartiers à Genève, une relation causale (empirique) a été établie entre des variables territoriales et les émissions des habitants des quartiers. 

Pour cela, les données du [MRMT 2015](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&ved=2ahUKEwiZzPDThOSCAxVY1AIHHR7BDAsQFnoECAgQAQ&url=https%3A%2F%2Fwww.bfs.admin.ch%2Fbfs%2Ffr%2Fhome%2Fstatistiques%2Fmobilite-transports%2Fenquetes%2Fmzmv.html&usg=AOvVaw0snDMao1E2kQdzhXFcBms1&opi=89978449) (Microrecensement mobilité et transports) ont été analysés : dans ces données, le lieu d'habitation ainsi que les déplacements journaliers (distance + mode) et les facteurs socio-économique de chaque ménage sont connus. L'information sur le lieu d'habitation nous permet ensuite de faire le lien entre les déplacements journaliers et leurs émissions conséquentes, et les variables territoriales. En utilisant la méthodologie [causal-curve](https://causal-curve.readthedocs.io/en/latest/), nous avons pu établir une relation causale entre les variables territoriales et les émissions, tout en contrôlant pour les facteurs socio-économiques.

Pour établir cette relation, nous avons agrégé les données territoriales dans des cellules de 500x500m, vu que la littérature indique que le rayon opérationnel d'un quartier se situe autour de 500 m. 

Cet outil web permet à l'utilisateur de dessiner son quartier sur la carte ; ensuite, un buffer de 500 m est dessiné autour du quartier. Une moyenne pondérée est ensuite calculée pour les cellules contenant les valeurs des variables territoriales qui sont dans ce buffer, avec le poids relatif au chevauchement entre la cellule et le buffer. Ces moyennes pondérées sont ensuite affichées dans un tableau.

Voici une liste de la source des données:
* Densité de population: [STATPOP](https://map.geo.admin.ch/?lang=fr&topic=ech&bgLayer=ch.swisstopo.pixelkarte-farbe&layers=ch.swisstopo.zeitreihen,ch.bfs.gebaeude_wohnungs_register,ch.bav.haltestellen-oev,ch.swisstopo.swisstlm3d-wanderwege,ch.astra.wanderland-sperrungen_umleitungen,ch.are.gueteklassen_oev,ch.bfs.volkszaehlung-bevoelkerungsstatistik_einwohner&layers_opacity=1,1,1,0.8,0.8,0.75,1&layers_visibility=false,false,false,false,false,false,true&layers_timestamp=18641231,,,,,,2021&E=2497243.70&N=1114412.56&zoom=7.626143810225274)
* Densité de bâtiments: [StatBL](https://map.geo.admin.ch/?lang=fr&topic=ech&bgLayer=ch.swisstopo.pixelkarte-farbe&layers=ch.swisstopo.zeitreihen,ch.bfs.gebaeude_wohnungs_register,ch.bav.haltestellen-oev,ch.swisstopo.swisstlm3d-wanderwege,ch.astra.wanderland-sperrungen_umleitungen,ch.are.gueteklassen_oev,ch.bfs.volkszaehlung-bevoelkerungsstatistik_einwohner,ch.bfs.volkszaehlung-gebaeudestatistik_gebaeude&layers_opacity=1,1,1,0.8,0.8,0.75,1,1&layers_visibility=false,false,false,false,false,false,false,true&layers_timestamp=18641231,,,,,,2021,2021&E=2497243.70&N=1114412.56&zoom=7.626143810225274&time=2021)
* Ratio emplois/habitants: [STATENT](https://map.geo.admin.ch/?lang=fr&topic=ech&bgLayer=ch.swisstopo.pixelkarte-farbe&layers=ch.swisstopo.zeitreihen,ch.bfs.gebaeude_wohnungs_register,ch.bav.haltestellen-oev,ch.swisstopo.swisstlm3d-wanderwege,ch.astra.wanderland-sperrungen_umleitungen,ch.are.gueteklassen_oev,ch.bfs.volkszaehlung-bevoelkerungsstatistik_einwohner,ch.bfs.betriebszaehlungen-beschaeftigte_vollzeitaequivalente&layers_opacity=1,1,1,0.8,0.8,0.75,1,1&layers_visibility=false,false,false,false,false,false,false,true&layers_timestamp=18641231,,,,,,2021,2020&E=2497243.70&N=1114412.56&zoom=7.626143810225274)
* Territoire de courtes distances: [Grand Genève](https://www.ge.ch/document/territoire-courtes-distances-diagnostic-enjeux-canton-geneve-grand-geneve)
* Accessibilité (gravitaire): [en TIM](https://map.geo.admin.ch/?lang=fr&topic=ech&bgLayer=ch.swisstopo.pixelkarte-farbe&layers=ch.swisstopo.zeitreihen,ch.bfs.gebaeude_wohnungs_register,ch.bav.haltestellen-oev,ch.swisstopo.swisstlm3d-wanderwege,ch.astra.wanderland-sperrungen_umleitungen,ch.are.gueteklassen_oev,ch.bfs.volkszaehlung-bevoelkerungsstatistik_einwohner,ch.bfs.betriebszaehlungen-beschaeftigte_vollzeitaequivalente,ch.swisstopo.vec200-landcover,ch.are.erreichbarkeit-oev,ch.are.erreichbarkeit-miv&layers_opacity=1,1,1,0.8,0.8,0.75,1,1,0.75,0.75,0.75&layers_visibility=false,false,false,false,false,false,false,false,false,false,true&layers_timestamp=18641231,,,,,,2021,2020,,,&E=2496976.13&N=1113393.32&zoom=7.699477143558599) et [en TP](https://map.geo.admin.ch/?lang=fr&topic=ech&bgLayer=ch.swisstopo.pixelkarte-farbe&layers=ch.swisstopo.zeitreihen,ch.bfs.gebaeude_wohnungs_register,ch.bav.haltestellen-oev,ch.swisstopo.swisstlm3d-wanderwege,ch.astra.wanderland-sperrungen_umleitungen,ch.are.gueteklassen_oev,ch.bfs.volkszaehlung-bevoelkerungsstatistik_einwohner,ch.bfs.betriebszaehlungen-beschaeftigte_vollzeitaequivalente,ch.swisstopo.vec200-landcover,ch.are.erreichbarkeit-oev&layers_opacity=1,1,1,0.8,0.8,0.75,1,1,0.75,0.75&layers_visibility=false,false,false,false,false,false,false,false,false,true&layers_timestamp=18641231,,,,,,2021,2020,,&E=2496486.58&N=1113929.06&zoom=7.699477143558599)

Vous trouverez [ici](https://github.com/6t-bureauderecherche/Outil_carbone_nouveaux_quartiers) le code source de cette application web.
"""
BTN_LABEL_CALCULATE = "Calculer les valeurs agrégées"
BTN_LABEL_DOWNLOAD = "Télécharger les données "
MAP_CENTER = [46.201815,6.147738]
MAP_ZOOM = 12
grid_url = './Data/Grid_All_Vars_Geneve_27_11_2023.gpkg'
dict_colnames = {'P_comb_tim':'Accessibilité en TIM',
                 'P_comb_tc': 'Accessibilité en TP',
                 'B_DENS':'Dens. bâtiments (bât/m2)',
                 'B15BTOT':'Dens. population (pop/ha)',
                 'ENTROPY':"Entropie utilisation du sol",
                 'FEUX_R_ARE':"N. intersections feux rouges (/km2)",
                 'MAX_DTV':'Charge max. du réseau (voit/j)', 
                 'R_EMPHAB':'Ratio emplois - habitants',
                 'ROAD_DENS':'Densité routière (km/km2)',
                 'TROTT_DENS':'Surf. couverte par trottoirs (km2/km2)',
                 'TYPO_TD':'Territoire de courtes distances',
                 'KLASSE':'Classe de desserte TP'}

# Presentation of the results: (block title, variables in display order)
RESULT_SUBTITLE = "Etat actuel du périmètre, sans tenir compte du projet de quartier"
RESULT_BLOCKS = [
    ("1 - BLOC D'ENTRÉE - CARACTÉRISTIQUES DU NOUVEAU QUARTIER",
     ['B_DENS', 'B15BTOT', 'R_EMPHAB', 'TYPO_TD']),
    ("2 - BLOC D'ENTRÉE - CARACTÉRISTIQUES DE L'ENVIRONNEMENT DE PROXIMITÉ "
     "DU NOUVEAU QUARTIER",
     ['P_comb_tim', 'P_comb_tc']),
]
# Variables computed and open to user upload
RESULT_VARIABLES = [v for _, variables in RESULT_BLOCKS for v in variables]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# 2.2. Initialize page
st.set_page_config(
        page_title="Nouveaux quartiers outil CO2",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={"About": ABOUT},
    )
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# 2.3. Main window
appliquer_style()
entete("Outil de quantification carbone des nouveaux quartiers du canton de Genève",
       "Cette application web facilite la saisie des données du volet Mobilité "
       "de l’outil carbone des quartiers.",
       "Suivez les étapes indiquées dans la colonne de gauche pour obtenir un "
       "tableau récapitulatif des indicateurs territoriaux agrégés à l’échelle "
       "de votre quartier.")

tab1,tab2 = st.tabs(['Indicateurs','Importer des données'])

with tab1:
    m = _show_map(center=MAP_CENTER, zoom=MAP_ZOOM)

with tab2:
    st.write("Afin d'ajouter vos propres données, cliquez sur la variable pour laquelle vous voulez remplacer les géodonnées. Pour enlever les données que vous avez ajoutées, cliquez sur la croix rouge (qui apparaîtra une fois que vous avez chargé des données) en dessous du bouton 'Browse files'.")
    for k in RESULT_VARIABLES:
        if f'{k}_uploaded' not in st.session_state:
            st.session_state[f'{k}_uploaded'] = False
        
        if f'{k}_filename' not in st.session_state:
            st.session_state[f'{k}_filename'] = ''
        
        if f'{k}_df' not in st.session_state:
            st.session_state[f'{k}_df'] = None
        
        if f'{k}_colnames' not in st.session_state:
            st.session_state[f'{k}_colnames'] = ['','']
        
        if f'{k}_selected_colname' not in st.session_state:
            st.session_state[f'{k}_selected_colname'] = None

        
        with st.expander(dict_colnames[k]):
            uploaded_file = st.file_uploader("Choisissez un geopackage",
                                             'gpkg',
                                             key = f'{k}_uploaded_file',
                                             on_change = _set_clicked_uploader,
                                             args = (k,),
                                             disabled = st.session_state[f'{k}_uploaded'])
                
                
            if st.session_state[f'{k}_uploaded']:
                col_name = st.selectbox(f'Quelle colonne correspond à la variable {dict_colnames[k]} ?',
                                        st.session_state[f'{k}_colnames'],
                                        key = f'{k}_selected_colname',
                                        placeholder = 'Sélectionnez la colonne correspondante',
                                        disabled = not st.session_state[f'{k}_uploaded'])
                if st.session_state[f'{k}_selected_colname'] is not None:
                    st.write('Le document : ',st.session_state[f'{k}_filename'],
                             ' a été ajouté. La colonne', 
                             st.session_state[f'{k}_selected_colname'],
                             'sera utilisée.')

        

        
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# 2.4. Add progress bar to top op sidebar
# ensure progress bar resides at top of sidebar and is invisible initially
progress_bar = st.sidebar.progress(0)
progress_bar.empty()


#------------------------------------------------------------------------------
# 3. Get drawing and analyse data
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# 3.1. Get user drawing
geo_drawing = None
    
with tab1:
    output = st_folium(m,
                       key="init",
                       width=1000,
                       height=600)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# 3.2. Get user drawing and convert it to geojson
if output:
    if output["all_drawings"] is not None:
        geo_drawing = _drawing_to_gdf(output)


# Getting Started container
    with st.sidebar.container():
        st.markdown(
            f"""# Marche à suivre

1. Localisez votre quartier en zoomant sur la carte.
2. Sélectionnez l’outil de dessin en cliquant sur l’icône du polygone noir dans la barre d’outils à gauche de la carte.
3. Délimitez votre quartier en dessinant un polygone sur la carte, puis cliquez sur « Finish » pour terminer.
4. Cliquez sur « {BTN_LABEL_CALCULATE} » pour obtenir les résultats à l’échelle de votre quartier.
"""
        )
        st.button(
            BTN_LABEL_CALCULATE,
            key="calculer",
            on_click=_check_area_and_compute_avg,
            kwargs={"geo_drawing" : geo_drawing,
                    "grid_url" : grid_url, 
                    "progress_bar" : progress_bar},
            disabled=False if geo_drawing is not None else True,
        )
        if 'calcul_message' in st.session_state:
            kind, text = st.session_state.pop('calcul_message')
            getattr(st, kind)(text)
        st.markdown(
            f"""**Optionnel : personnalisation des données d'entrée**

Vous pouvez également remplacer les données géospatiales existantes par vos propres données dans l’onglet « Importer des données ».

Après avoir ajouté ou supprimé des données, cliquez à nouveau sur « {BTN_LABEL_CALCULATE} » pour actualiser les résultats.
"""
        )

        st.sidebar.markdown("---")
            
    if 'aggregated_values' not in st.session_state:
        st.session_state.aggregated_values = False
    
    if st.session_state.aggregated_values:
        with st.sidebar.container():
            st.markdown("""# Résultats : valeurs agrégées des variables territoriales """)
            df = st.session_state.aggregated_values_df
            if len(df)>0:
                for number, (title, variables) in enumerate(RESULT_BLOCKS, 1):
                    table = _block_table(df, variables)
                    table['Valeur'] = table['Valeur'].map(_format_value)
                    # the block number is shown in the coloured badge
                    bloc_resultats(number, title.split(' - ', 1)[1],
                                   RESULT_SUBTITLE,
                                   table.itertuples(index=False))
                f_name = datetime.datetime.now().strftime('%d%m%Y_%H%M%S')
                st.download_button(label = "Télécharger données agrégées",
                                   data = convert_df(df),
                                   file_name = 'DonneesAgregees_'+f_name+'.xlsx')
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

pied_de_page("6t · Outil de quantification carbone des nouveaux quartiers du canton de Genève")
