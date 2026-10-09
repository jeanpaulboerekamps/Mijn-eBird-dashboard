import io
import math
import pandas as pd
import plotly.express as px
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle
from pathlib import Path

@st.cache_data
def read_taxonomy(data):
    tax = pd.read_csv(io.BytesIO(data), low_memory=False)
    aliases = {'scientific name':['scientific name','scientific_name','sci_name','scientificname'], 'order':['order','order_name'], 'family':['family','family_name'], 'category':['category']}
    cols={str(c).strip().lower():c for c in tax.columns}
    found={key:next((cols[a] for a in options if a in cols),None) for key,options in aliases.items()}
    if not all(found[k] for k in ('scientific name','order','family')):
        raise ValueError('CSV moet kolommen scientific name, order en family bevatten (hoofdletterongevoelig).')
    out=tax.rename(columns={v:k for k,v in found.items() if v is not None}).copy()
    if found['category']:
        out=out[out['category'].astype(str).str.lower().eq('species')]
    out=out.dropna(subset=['scientific name','order','family'])
    out['scientific name']=out['scientific name'].astype(str).str.strip()
    out=out[out['scientific name'].str.fullmatch(r'[A-Z][A-Za-z-]+ [a-z][A-Za-z-]+')]
    return out.drop_duplicates('scientific name')

def render_heatmap(df):
    st.subheader('7. Wereldkaart — soortenrijkdom van je waarnemingen')
    st.caption('Elke cel toont het aantal **verschillende soorten** dat je daar hebt waargenomen; geen optelling van individuele vogels of checklists. Zoom in om hotspots te bekijken.')
    if not {'Latitude','Longitude'}.issubset(df.columns):
        st.warning('Coördinaten ontbreken in deze export.')
        return
    coords=df[['Latitude','Longitude','Scientific Name']].copy()
    coords['Latitude']=pd.to_numeric(coords.Latitude,errors='coerce')
    coords['Longitude']=pd.to_numeric(coords.Longitude,errors='coerce')
    coords=coords.dropna()
    coords=coords[coords.Latitude.between(-90,90)&coords.Longitude.between(-180,180)]
    if coords.empty:
        st.info('Geen waarnemingen met geldige coördinaten.')
        return
    resolution=st.select_slider('Resolutie van de heatmap',options=[0.25,0.5,1,2,5],value=1,format_func=lambda x:f'{x:g}°')
    coords['lat_cell']=((coords.Latitude+90)//resolution*resolution-90+resolution/2).round(5)
    coords['lon_cell']=((coords.Longitude+180)//resolution*resolution-180+resolution/2).round(5)
    cells=coords.groupby(['lat_cell','lon_cell'])['Scientific Name'].nunique().reset_index(name='Soorten')
    fig=px.density_map(cells,lat='lat_cell',lon='lon_cell',z='Soorten',radius=18,zoom=1,map_style='open-street-map',color_continuous_scale='YlGn',hover_data={'Soorten':True,'lat_cell':False,'lon_cell':False})
    fig.update_layout(height=620,margin=dict(l=0,r=0,t=0,b=0),coloraxis_colorbar_title='Soorten')
    st.plotly_chart(fig,use_container_width=True)
    st.caption('De kleur toont een vloeiende weergave van de aantallen per rastercel; naast elkaar liggende cellen kunnen visueel overlappen. Rastercoördinaten zijn afgerond, niet de exacte waarnemingslocaties.')

def render_taxonomy(df):
    st.subheader('8. Vogelordes en zangvogelfamilies — jouw dekking')
    st.caption('Elke cirkel vertegenwoordigt een orde, behalve Passeriformes: die is uitgesplitst in families. Cirkeloppervlak = totaal aantal erkende soorten in de referentielijst. Donker segment = jouw aandeel.')
    path=Path(__file__).resolve().parent/'data'/'taxonomy.csv'
    with st.expander('Taxonomische referentielijst',expanded=not path.exists()):
        st.write('Voor betrouwbare wereldtotalen en percentages is een **volledige wereldwijde vogelchecklist** nodig, met de kolommen `scientific name`, `order`, `family` en liefst `category` (species). De eBird-waarnemingsexport bevat deze taxonomische indeling en wereldtotalen niet.')
        upload=st.file_uploader('Optioneel: complete taxonomische CSV',type=['csv'],key='taxonomy_upload')
        st.caption('Je kunt `data/taxonomy.csv` in GitHub zetten om deze lijst automatisch te laden. Gebruik bij voorkeur dezelfde taxonomie als je eBird-export.')
    if upload:
        taxbytes=upload.getvalue()
    elif path.exists():
        taxbytes=path.read_bytes()
    else:
        st.info('De cirkelkaart verschijnt zodra je een volledige taxonomische checklist toevoegt. Ik toon geen verzonnen wereldtotalen of percentages.')
        return
    try: tax=read_taxonomy(taxbytes)
    except Exception as exc:
        st.error(f'Checklist kon niet worden gelezen: {exc}')
        return
    seen=set(df['Scientific Name'].dropna().unique())
    tax['seen']=tax['scientific name'].isin(seen)
    tax['groep']=tax.apply(lambda r:r['family'] if str(r['order']).strip().casefold()=='passeriformes' else r['order'],axis=1)
    stats=tax.groupby('groep').agg(totaal=('scientific name','nunique'),gezien=('seen','sum')).reset_index()
    stats=stats.sort_values('totaal',ascending=False).reset_index(drop=True)
    unmatched=len(seen-set(tax['scientific name']))
    st.caption(f'{len(tax):,} soorten in de referentielijst · {len(seen & set(tax["scientific name"])):,} van jouw soorten gekoppeld · {unmatched:,} niet gekoppeld (bijvoorbeeld door taxonomische verschillen).'.replace(',','.'))
    if stats.empty:return
    # Geordende cirkels met niet-overlappende rijen; grootte is evenredig met sqrt(soortental).
    maxval=stats.totaal.max()
    stats['r']=stats.totaal.apply(lambda n:0.65+2.15*math.sqrt(n/maxval))
    width=18.0
    x,y,rowheight=0.,0.,0.
    positions=[]
    for r in stats.r:
        if x+2*r>width and x>0:
            y+=2*rowheight+0.35;x=0;rowheight=0
        positions.append((x+r,y+r));x+=2*r+0.35;rowheight=max(rowheight,r)
    fig,ax=plt.subplots(figsize=(15,max(7,(y+2*rowheight)*0.7)))
    fig.patch.set_facecolor('#f2f6f1');ax.set_facecolor('#f2f6f1')
    for (_,s),(cx,cy) in zip(stats.iterrows(),positions):
        r=s.r;p=s.gezien/s.totaal
        ax.add_patch(Circle((cx,cy),r,facecolor='#d6e8dc',edgecolor='#9bbbaa',lw=1.3))
        if p>0:ax.add_patch(Wedge((cx,cy),r,90,90+360*p,facecolor='#147955',edgecolor='none',alpha=.95))
        label=f'{s.groep}\n{s.gezien}/{s.totaal} soorten\n{p:.0%} gezien'
        fs=max(5.3,min(10.5,r*4.0))
        ax.text(cx,cy,label,ha='center',va='center',fontsize=fs,color='#102f26',fontweight='bold',linespacing=1.15,bbox=dict(facecolor='white',alpha=.68,edgecolor='none',pad=1.5))
    ax.set_xlim(-.2,width+.2);ax.set_ylim(y+2*rowheight+.2,-.2);ax.set_aspect('equal');ax.axis('off')
    st.pyplot(fig,use_container_width=True)
    plt.close(fig)
    st.dataframe(stats[['groep','totaal','gezien']].assign(percentage=lambda t:(100*t.gezien/t.totaal).round(1)).rename(columns={'groep':'Orde / familie','totaal':'Wereldtotaal','gezien':'Gezien','percentage':'% gezien'}),hide_index=True,use_container_width=True)
