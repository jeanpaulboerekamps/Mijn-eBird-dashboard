import io
import zipfile
from functools import lru_cache
import pandas as pd
import plotly.express as px
import streamlit as st
import pycountry

st.set_page_config(page_title='My Birding Life',page_icon='🦜',layout='wide')
st.markdown('''<style> .stApp {background:#f2f6f1} h1,h2,h3 {color:#123f32} [data-testid="stMetric"] {background:white;border:1px solid #dce8dd;border-radius:15px;padding:16px} </style>''',unsafe_allow_html=True)
st.title('🦜 My Birding Life')
st.caption('Jouw eBird-waarnemingen, van eerste vogel tot nieuwste lifer')

@st.cache_data(show_spinner='eBird-waarnemingen verwerken…')
def load_data(raw,filename):
    if filename.lower().endswith('.zip'):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names=[n for n in z.namelist() if n.lower().endswith('.csv')]
            if not names: raise ValueError('Geen CSV in het ZIP-bestand gevonden')
            with z.open(names[0]) as f: df=pd.read_csv(f,low_memory=False)
    else: df=pd.read_csv(io.BytesIO(raw),low_memory=False)
    required={'Scientific Name','Common Name','Date','State/Province'}
    if not required.issubset(df.columns): raise ValueError('Dit lijkt geen eBird MyEBirdData-export te zijn')
    df['Date']=pd.to_datetime(df['Date'],errors='coerce')
    df=df.dropna(subset=['Date','Scientific Name']).copy()
    df['Country']=df['State/Province'].fillna('').astype(str).str.split('-').str[0].str.upper()
    df['Year']=df['Date'].dt.year
    return df

@lru_cache(maxsize=256)
def country_name(code):
    special={'XK':'Kosovo','CW':'Curaçao','BQ':'Caribbean Netherlands','UK':'United Kingdom'}
    if code in special:return special[code]
    try:return pycountry.countries.get(alpha_2=code).name
    except:return code

@lru_cache(maxsize=256)
def iso3(code):
    special={'UK':'GBR','XK':'XKX'}
    if code in special:return special[code]
    try:return pycountry.countries.get(alpha_2=code).alpha_3
    except:return None

# Continents are assigned from country codes using the countryinfo dataset.
@lru_cache(maxsize=256)
def continent(code):
    try:
        import country_converter as coco
        result=coco.convert(names=code,to='continent',not_found='Overig')
        return result if result not in ('not found','Overig') else 'Overig'
    except Exception:return 'Overig'

with st.sidebar:
    st.header('📁 Gegevens')
    uploaded=st.file_uploader('Upload je eBird-export (ZIP of CSV)',type=['zip','csv'])
    st.caption('Je bestand wordt alleen voor deze appsessie verwerkt. Publiceer je persoonlijke waarnemingen niet in een openbare GitHub-repository.')
    st.divider()
    st.caption('Kaarten tonen unieke soorten per gebied. Eén soort kan in meerdere landen voorkomen.')

if uploaded is None:
    st.info('👈 Upload links je oorspronkelijke eBird ZIP-bestand om je dashboard te openen.')
    st.stop()
try: df=load_data(uploaded.getvalue(),uploaded.name)
except Exception as e: st.error(f'Bestand kon niet worden gelezen: {e}');st.stop()

countries=sorted(df['Country'].dropna().unique(),key=country_name)
with st.sidebar:
    chosen=st.multiselect('Filter op land',countries,format_func=country_name)
    min_year,max_year=int(df.Year.min()),int(df.Year.max())
    period=st.slider('Periode',min_year,max_year,(min_year,max_year))
    st.caption('De liferberekening gebruikt altijd de volledige historie, ook als je op periode filtert.')

first=df.sort_values('Date').drop_duplicates('Scientific Name',keep='first').copy()
first['First year']=first.Date.dt.year
filtered=df[df.Year.between(*period)]
if chosen: filtered=filtered[filtered.Country.isin(chosen)]
filtered_first=first[first['First year'].between(*period)]
if chosen: filtered_first=filtered_first[filtered_first.Country.isin(chosen)]

m1,m2,m3,m4=st.columns(4)
m1.metric('Life List totaal',f'{df["Scientific Name"].nunique():,}'.replace(',','.'))
m2.metric('Waarnemingsregels',f'{len(df):,}'.replace(',','.'))
m3.metric('Landen / gebieden',df.Country.nunique())
m4.metric(f'Nieuwe soorten {max_year}',int((first['First year']==max_year).sum()))

left,right=st.columns(2)
byfirst=first.groupby('First year')['Scientific Name'].nunique().reindex(range(min_year,max_year+1),fill_value=0)
with left:
    st.subheader('1. Groei van je Life List')
    growth=byfirst.cumsum().reset_index();growth.columns=['Jaar','Soorten']
    fig=px.line(growth,x='Jaar',y='Soorten',markers=True)
    fig.update_traces(line_color='#13795b');fig.update_layout(hovermode='x unified')
    st.plotly_chart(fig,use_container_width=True)
with right:
    st.subheader('2. Nieuwe soorten per jaar')
    new=filtered_first.groupby('First year')['Scientific Name'].nunique().reset_index()
    fig=px.bar(new,x='First year',y='Scientific Name',labels={'First year':'Jaar','Scientific Name':'Nieuwe soorten'},color_discrete_sequence=['#218b68'])
    st.plotly_chart(fig,use_container_width=True)
st.subheader('3. Soorten gezien per jaar')
annual=filtered.groupby('Year')['Scientific Name'].nunique().reset_index()
fig=px.bar(annual,x='Year',y='Scientific Name',labels={'Year':'Jaar','Scientific Name':'Unieke soorten'},color_discrete_sequence=['#218b68'])
st.plotly_chart(fig,use_container_width=True)

st.subheader('4. Soorten per continent')
geo=df[['Country','Scientific Name']].drop_duplicates().copy()
geo['Continent']=geo.Country.map(continent)
cont=geo.groupby('Continent')['Scientific Name'].nunique().reset_index().sort_values('Scientific Name',ascending=False)
fig=px.bar(cont,x='Continent',y='Scientific Name',labels={'Scientific Name':'Unieke soorten'},color='Scientific Name',color_continuous_scale='Greens')
st.plotly_chart(fig,use_container_width=True)

st.subheader('5. Interactieve wereldkaart — soorten per land')
country_counts=filtered.groupby('Country')['Scientific Name'].nunique().reset_index(name='Soorten')
country_counts['ISO3']=country_counts.Country.map(iso3)
country_counts['Land']=country_counts.Country.map(country_name)
fig=px.choropleth(country_counts.dropna(subset=['ISO3']),locations='ISO3',color='Soorten',hover_name='Land',hover_data={'ISO3':False},color_continuous_scale='YlGn',projection='natural earth')
fig.update_geos(showcoastlines=True,coastlinecolor='#9cb7a9',showframe=False,showcountries=True,countrycolor='#d0ded3')
fig.update_layout(margin=dict(l=0,r=0,t=0,b=0),height=520)
st.plotly_chart(fig,use_container_width=True)
st.caption('Beweeg over landen om aantallen te zien. Selecteer een land in de zijbalk voor de bijbehorende soorten en lifers.')
with st.expander('Landenranglijst en soorten bekijken'):
    st.dataframe(country_counts[['Land','Soorten']].sort_values('Soorten',ascending=False),hide_index=True,use_container_width=True)
    detail=st.selectbox('Bekijk soorten uit land',countries,format_func=country_name)
    sub=df[df.Country==detail].sort_values('Date').drop_duplicates('Scientific Name')
    st.dataframe(sub[['Common Name','Scientific Name','Date','Location']].rename(columns={'Common Name':'Engelse naam','Scientific Name':'Wetenschappelijke naam','Date':'Eerste waarneming','Location':'Locatie'}),hide_index=True,use_container_width=True)

st.subheader('6. Nieuwste lifers')
st.caption('Eerste waarneming per wetenschappelijke naam, nieuwste eerst. Foto’s via links naar iNaturalist en Macaulay Library.')
search=st.text_input('Zoek vogelsoort of locatie')
life=filtered_first.sort_values('Date',ascending=False)
if search:
    mask=life[['Common Name','Scientific Name','Location']].fillna('').astype(str).apply(lambda c:c.str.contains(search,case=False,regex=False)).any(axis=1)
    life=life[mask]
max_items=st.select_slider('Aantal getoonde lifers',options=[12,24,48,100,250],value=24)
for _,r in life.head(max_items).iterrows():
    with st.container(border=True):
        c1,c2=st.columns([3,1])
        with c1:
            st.markdown(f'**{r["Common Name"]}** · *{r["Scientific Name"]}*')
            st.caption(f'{r["Date"]:%d-%m-%Y} · {country_name(r["Country"])} · {r.get("Location","")}')
        with c2:
            from urllib.parse import quote
            st.link_button('📷 iNaturalist',f'https://www.inaturalist.org/observations?taxon_name={quote(str(r["Scientific Name"]))}',use_container_width=True)
            st.link_button('📷 Macaulay',f'https://search.macaulaylibrary.org/catalog?taxonCode=&q={quote(str(r["Scientific Name"]))}',use_container_width=True)
st.caption('Opmerking: ondersoorten, hybriden en soortgroepen in eBird kunnen als aparte wetenschappelijke namen meetellen; dit kan afwijken van de officiële eBird Life List.')
