import io
from pathlib import Path
import re
import zipfile
from urllib.parse import quote

import pandas as pd
import plotly.express as px
import streamlit as st
import pycountry
import country_converter as coco
import requests

st.set_page_config(page_title='My Birding Life', page_icon='🦜', layout='wide')
st.markdown('''<style>.stApp{background:#f2f6f1} h1,h2,h3{color:#123f32} [data-testid="stMetric"]{background:white;border:1px solid #dce8dd;border-radius:15px;padding:16px} .birdcard{background:white;border:1px solid #dce8dd;border-radius:16px;padding:12px;margin-bottom:10px} .birdname{font-weight:700;color:#123f32;font-size:1.05rem} .birdmeta{color:#687a70;font-size:.86rem} </style>''', unsafe_allow_html=True)
st.title('🦜 My Birding Life')
st.caption('Jouw eBird-waarnemingen, van eerste vogel tot nieuwste lifer')

# Alleen zuivere binomiale wetenschappelijke namen tellen als soort. De app
# toont geen taxa van het type sp., slash-combinaties, groepen of ondersoorten.
BINOMIAL = re.compile(r'^[A-Z][a-zA-Z-]+ [a-z][a-zA-Z-]+$')
BAD_COMMON = re.compile(r'\b(sp\.|spp\.|group|hybrid|intergrade|slash|domestic type)\b|[/×]', re.I)

def is_species(scientific, common):
    return bool(BINOMIAL.fullmatch(str(scientific).strip())) and not bool(BAD_COMMON.search(str(common)))

@st.cache_data(show_spinner='eBird-waarnemingen verwerken…')
def load_data(raw, filename):
    if filename.lower().endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names=[n for n in z.namelist() if n.lower().endswith('.csv')]
            if not names: raise ValueError('Geen CSV gevonden in ZIP')
            with z.open(names[0]) as f: df=pd.read_csv(f, low_memory=False)
    else: df=pd.read_csv(io.BytesIO(raw),low_memory=False)
    required={'Scientific Name','Common Name','Date','State/Province'}
    if not required.issubset(df.columns): raise ValueError('Geen herkenbare eBird-export')
    df['Date']=pd.to_datetime(df['Date'],errors='coerce')
    df=df.dropna(subset=['Date','Scientific Name']).copy()
    df['Scientific Name']=df['Scientific Name'].astype(str).str.strip()
    df['Country']=df['State/Province'].fillna('').astype(str).str.split('-').str[0].str.upper()
    df['Year']=df['Date'].dt.year
    df['Species valid']=[is_species(s,c) for s,c in zip(df['Scientific Name'],df['Common Name'])]
    return df

@st.cache_data
def country_name(code):
    special={'XK':'Kosovo','CW':'Curaçao','BQ':'Caribisch Nederland','UK':'Verenigd Koninkrijk'}
    if code in special:return special[code]
    obj=pycountry.countries.get(alpha_2=code)
    return obj.name if obj else code

@st.cache_data
def iso3(code):
    special={'UK':'GBR','XK':'XKX'}
    if code in special:return special[code]
    obj=pycountry.countries.get(alpha_2=code)
    return obj.alpha_3 if obj else None

# Centraal-Amerika omvat hier Mexico t/m Panama plus Caribische eilanden.
CENTRAL={'MX','BZ','GT','SV','HN','NI','CR','PA','CU','JM','HT','DO','PR','BS','BB','TT','GD','LC','VC','AG','KN','DM','AW','CW','BQ','SX','MF','GP','MQ','KY','TC','VG','VI','BM','AI','MS','BL'}
SOUTH={'CO','VE','GY','SR','GF','EC','PE','BO','BR','PY','UY','AR','CL','FK'}
NORTH={'CA','US','GL','PM'}
@st.cache_data
def region(code):
    if code in CENTRAL:return 'Midden-Amerika & Cariben'
    if code in SOUTH:return 'Zuid-Amerika'
    if code in NORTH:return 'Noord-Amerika'
    name=coco.convert(names=code,to='continent',not_found='Overig')
    return {'Africa':'Afrika','Asia':'Azië','Europe':'Europa','Oceania':'Oceanië','America':'Overig Amerika'}.get(name,'Overig')

@st.cache_data(ttl=60*60*24*14,show_spinner=False)
def inat_photo(scientific):
    """Alleen een exact overeenkomend species-taxon; anders geen foto."""
    try:
        resp=requests.get('https://api.inaturalist.org/v1/taxa',params={'q':scientific,'per_page':30,'is_active':'true'},timeout=8,headers={'User-Agent':'MyBirdingLife/2.0 (personal bird dashboard)'})
        resp.raise_for_status()
        matches=resp.json().get('results',[])
        taxon=next((t for t in matches if t.get('name','').casefold()==scientific.casefold() and t.get('rank')=='species'),None)
        if not taxon:return None
        photo=taxon.get('default_photo') or {}
        url=photo.get('medium_url') or photo.get('url')
        if not url:return None
        return {'url':url,'attribution':photo.get('attribution',''),'taxon_url':f'https://www.inaturalist.org/taxa/{taxon["id"]}'}
    except (requests.RequestException,ValueError,KeyError):return None

# De meegeleverde export wordt bij iedere herstart automatisch ingelezen.
DATA_FILE = Path(__file__).resolve().parent / 'data' / 'ebird.zip'
with st.sidebar:
    st.header('📁 Gegevens')
    uploaded = st.file_uploader('Optioneel: nieuwere eBird-export (ZIP of CSV)', type=['zip', 'csv'])
    st.caption('Standaard wordt de meegeleverde export automatisch geladen.')
if uploaded is not None:
    source_bytes, source_name = uploaded.getvalue(), uploaded.name
elif DATA_FILE.is_file():
    source_bytes, source_name = DATA_FILE.read_bytes(), DATA_FILE.name
else:
    st.error('Geen standaardbestand gevonden: data/ebird.zip. Upload een eBird-export via de zijbalk.')
    st.stop()
try:
    raw = load_data(source_bytes, source_name)
except Exception as exc:
    st.error(f'Bestand kon niet worden gelezen: {exc}')
    st.stop()
df=raw[raw['Species valid']].copy()
if df.empty:st.error('Geen eenduidig bepaalde soorten gevonden.');st.stop()
first=df.sort_values('Date').drop_duplicates('Scientific Name').copy()
first['First year']=first.Date.dt.year
min_year,max_year=int(df.Year.min()),int(df.Year.max())
countries=sorted(df.Country.unique(),key=country_name)
with st.sidebar:
    chosen=st.multiselect('Filter op land',countries,format_func=country_name)
    period=st.slider('Periode',min_year,max_year,(min_year,max_year))
    st.caption('De Life List en eerste-waarnemingsdatum worden altijd over de volledige historie bepaald.')
    st.caption(f'{len(raw)-len(df):,} waarnemingsregels met niet-eenduidige taxa zijn uitgesloten van de soortentellingen.'.replace(',','.'))
filtered=df[df.Year.between(*period)]
if chosen:filtered=filtered[filtered.Country.isin(chosen)]
filtered_first=first[first['First year'].between(*period)]
if chosen:filtered_first=filtered_first[filtered_first.Country.isin(chosen)]

m1,m2,m3,m4=st.columns(4)
m1.metric('Volledige soorten ooit',f'{df["Scientific Name"].nunique():,}'.replace(',','.'))
m2.metric('Waarnemingsregels (soorten)',f'{len(df):,}'.replace(',','.'))
m3.metric('Landen / gebieden',df.Country.nunique())
m4.metric(f'Nieuwe soorten {max_year}',int((first['First year']==max_year).sum()))

byfirst=first.groupby('First year')['Scientific Name'].nunique().reindex(range(min_year,max_year+1),fill_value=0)
growth=byfirst.cumsum().reset_index();growth.columns=['Jaar','Soorten']
st.subheader('1. Groei van je Life List')
st.caption(f'Totaal: **{df["Scientific Name"].nunique():,} soorten** — van {min_year} tot {max_year}'.replace(',','.'))
fig=px.line(growth,x='Jaar',y='Soorten',markers=True,custom_data=['Soorten'])
fig.update_traces(line_color='#13795b',line_width=3,hovertemplate='%{x}: %{y:,} soorten<extra></extra>')
fig.update_layout(height=400,hovermode='x unified',margin=dict(l=15,r=15,t=20,b=10))
st.plotly_chart(fig,use_container_width=True)

left,right=st.columns(2)
with left:
    st.subheader('2. Nieuwe soorten per jaar')
    new=filtered_first.groupby('First year')['Scientific Name'].nunique().reindex(range(period[0],period[1]+1),fill_value=0).reset_index()
    new.columns=['Jaar','Soorten']
    st.caption(f'**{new.Soorten.sum():,} nieuwe soorten** in de selectie'.replace(',','.'))
    fig=px.bar(new,x='Jaar',y='Soorten',text='Soorten',color_discrete_sequence=['#218b68'])
    fig.update_traces(textposition='outside',textfont_size=10,cliponaxis=False,hovertemplate='%{x}: %{y} nieuwe soorten<extra></extra>')
    fig.update_layout(height=430,margin=dict(l=10,r=10,t=35,b=10),xaxis=dict(type='category',nticks=12))
    st.plotly_chart(fig,use_container_width=True)
with right:
    st.subheader('3. Soorten gezien per jaar')
    annual=filtered.groupby('Year')['Scientific Name'].nunique().reindex(range(period[0],period[1]+1),fill_value=0).reset_index()
    annual.columns=['Jaar','Soorten']
    st.caption(f'**{annual.Soorten.max():,} soorten** in het beste jaar'.replace(',','.'))
    fig=px.bar(annual,x='Jaar',y='Soorten',text='Soorten',color_discrete_sequence=['#218b68'])
    fig.update_traces(textposition='outside',textfont_size=10,cliponaxis=False,hovertemplate='%{x}: %{y} soorten<extra></extra>')
    fig.update_layout(height=430,margin=dict(l=10,r=10,t=35,b=10),xaxis=dict(type='category',nticks=12))
    st.plotly_chart(fig,use_container_width=True)

st.subheader('4. Soorten per continent / regio')
geo=filtered[['Country','Scientific Name']].drop_duplicates().copy()
geo['Regio']=geo.Country.map(region)
cont=geo.groupby('Regio')['Scientific Name'].nunique().reset_index(name='Soorten').sort_values('Soorten',ascending=False)
fig=px.bar(cont,x='Regio',y='Soorten',text='Soorten',color='Soorten',color_continuous_scale='Greens')
fig.update_traces(textposition='outside',textfont_size=14,cliponaxis=False,hovertemplate='%{x}: %{y} soorten<extra></extra>')
fig.update_layout(height=440,margin=dict(l=10,r=10,t=35,b=10),coloraxis_showscale=False)
st.plotly_chart(fig,use_container_width=True)
st.caption('Een soort kan in meerdere regio’s meetellen. Midden-Amerika omvat hier Mexico, Centraal-Amerika en de Cariben.')

st.subheader('5. Interactieve wereldkaart — soorten per land')
country_counts=filtered.groupby('Country')['Scientific Name'].nunique().reset_index(name='Soorten')
country_counts['ISO3']=country_counts.Country.map(iso3)
country_counts['Land']=country_counts.Country.map(country_name)
fig=px.choropleth(country_counts.dropna(subset=['ISO3']),locations='ISO3',color='Soorten',hover_name='Land',hover_data={'ISO3':False,'Soorten':True},color_continuous_scale='YlGn',projection='natural earth')
fig.update_geos(showcoastlines=True,coastlinecolor='#9cb7a9',showframe=False,showcountries=True,countrycolor='#d0ded3')
fig.update_layout(margin=dict(l=0,r=0,t=0,b=0),height=520)
st.plotly_chart(fig,use_container_width=True)
with st.expander('Landenranglijst en soorten bekijken'):
    st.dataframe(country_counts[['Land','Soorten']].sort_values('Soorten',ascending=False),hide_index=True,use_container_width=True)
    detail=st.selectbox('Bekijk soorten uit land',countries,format_func=country_name)
    sub=df[df.Country==detail].sort_values('Date').drop_duplicates('Scientific Name')
    st.dataframe(sub[['Common Name','Scientific Name','Date','Location']].rename(columns={'Common Name':'Engelse naam','Scientific Name':'Wetenschappelijke naam','Date':'Eerste waarneming','Location':'Locatie'}),hide_index=True,use_container_width=True)

# De heatmap staat direct voor de lifergalerij.
from extra_sections import render_heatmap, render_taxonomy
render_heatmap(filtered)

st.subheader('6. Nieuwste lifers met iNaturalist-foto’s')
st.caption('Alleen eenduidige volledige soorten (binomiale namen); geen ondersoorten, hybriden of soortgroepen. Eerste waarneming, nieuwste eerst.')
search=st.text_input('Zoek vogelsoort of locatie')
life=filtered_first.sort_values('Date',ascending=False)
if search:
    mask=life[['Common Name','Scientific Name','Location']].fillna('').astype(str).apply(lambda c:c.str.contains(search,case=False,regex=False)).any(axis=1)
    life=life[mask]
max_items=st.select_slider('Aantal getoonde lifers',options=[12,24,48,100],value=24)
show=life.head(max_items)
for start in range(0,len(show),3):
    cols=st.columns(3)
    for col,(_,r) in zip(cols,show.iloc[start:start+3].iterrows()):
        with col:
            with st.container(border=True):
                photo=inat_photo(r['Scientific Name'])
                if photo:
                    st.image(photo['url'],use_container_width=True)
                    st.caption('Foto: '+(photo['attribution'] or 'iNaturalist'))
                else:
                    st.info('Geen gecontroleerde iNaturalist-foto beschikbaar')
                st.markdown(f'**{r["Common Name"]}**')
                st.markdown(f'*{r["Scientific Name"]}*')
                st.caption(f'{r["Date"]:%d-%m-%Y} · {country_name(r["Country"])} · {r.get("Location","")}')
                if photo:st.link_button('Bekijk foto op iNaturalist',photo['taxon_url'],use_container_width=True)
                else:st.link_button('Zoek op iNaturalist',f'https://www.inaturalist.org/search?q={quote(r["Scientific Name"])}',use_container_width=True)
st.caption('Taxonomische kanttekening: deze strenge naamfilter sluit onduidelijke taxa uit, maar controleert niet volledig tegen de actuele eBird/Clements-taxonomie. Een ondersoortwaarneming wordt niet automatisch omgezet naar een soortwaarneming.')

# Officiele taxonomische dekking
render_taxonomy(df)
