from dash import Dash, html, dcc, dash_table, Input, Output
import pandas as pd
import dash_bootstrap_components as dbc
import geopandas as gpd
import json
import folium
from io import BytesIO
import base64

# Create the Dash app with a Bootstrap stylesheet
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Load the CSV data
csv_file_path = r"D:\projects\map\UNIGE_RESIDENTI_20240101 Editted.csv"
df = pd.read_csv(csv_file_path, encoding='latin1', low_memory=False)

# Load the shapefile
shapefile_path = r"D:\projects\map\MEDIATORE_V_SEZ_CENS_Comune\MEDIATORE_V_SEZ_CENS_Comune\V_SEZ_CENS_2011Polygon.shp"
gdf = gpd.read_file(shapefile_path)


# Ensure the column names match between DataFrame and GeoDataFrame
df = df.rename(columns={
    'SEZIONE_CENSIMENTO': 'SEZIONE_20',
    'CODICE_MUNICIPIO': 'CODICE_MUN',
    'NOME_MUNICIPIO': 'NOME_MUNIC',
    'CODICE_CIRCOSCRIZIONE': 'CODICE_CIR',
    'NOME_CIRCOSCRIZIONE': 'NOME_CIRCO',
    'CODICE_UNITA_URBANISTICA': 'CODICE_UNI',
    'NOME_UNITA_URBANISTICA': 'NOME_UNITA'
})

# Convert columns to the same data type
df['SEZIONE_20'] = df['SEZIONE_20'].astype(float)
gdf['SEZIONE_20'] = gdf['SEZIONE_20'].astype(float)

# Perform the merge
merged_gdf = gdf.merge(df, on='SEZIONE_20', how='inner')
merged_gdf = gpd.GeoDataFrame(merged_gdf, geometry='geometry')

# Ensure CRS is set correctly
if gdf.crs is None:
    gdf.set_crs(epsg=4326, inplace=True)
if merged_gdf.crs is None:
    merged_gdf.set_crs(gdf.crs, inplace=True)
if merged_gdf.crs != 'EPSG:4326':
    merged_gdf = merged_gdf.to_crs(epsg=4326)

# Convert GeoDataFrame to GeoJSON format for Plotly
geojson = json.loads(merged_gdf.to_json())

# Get min and max of 'Eta'
Eta_min = df['Eta'].min()
Eta_max = df['Eta'].max()

# Layout of the Dash app
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Residenti Genova"), width=12)
    ]),
    dbc.Row([
        dbc.Col(dcc.RangeSlider(
            id='eta-slider',
            min=Eta_min,
            max=Eta_max,
            value=[Eta_min, Eta_max],
            marks={i: str(i) for i in range(Eta_min, Eta_max + 1, 5)}
        ), width=12)
    ]),
    dbc.Row([
        dbc.Col(html.Div(id='map-figure'), width=12)
    ]),
    dbc.Row([
        dbc.Col(dash_table.DataTable(
            id='datatable',
            columns=[{"name": i, "id": i} for i in df.columns],
            data=df.to_dict('records'),
            page_size=10,
        ), width=12)
    ])
])

# Callback to update the map and table based on the range slider
@app.callback(
    [Output('map-figure', 'children'),
     Output('datatable', 'data')],
    [Input('eta-slider', 'value')]
)
def update_output_div(selected_Eta):
    filtered_df = df[
        (df['Eta'] >= selected_Eta[0]) &
        (df['Eta'] <= selected_Eta[1])
    ]

    # Merge the filtered DataFrame with the GeoDataFrame
    filtered_gdf = gdf.merge(filtered_df, on='SEZIONE_20', how='inner')
    filtered_gdf = gpd.GeoDataFrame(filtered_gdf, geometry='geometry')

    # Ensure CRS is correct
    if filtered_gdf.crs != 'EPSG:4326':
        filtered_gdf = filtered_gdf.to_crs(epsg=4326)

    def get_color(eta):
        if eta < 25:
            return 'green'
        elif eta < 50:
            return 'orange'
        elif eta < 75:
            return 'blue'
        elif eta < 90:
            return 'yelow'
        elif eta < 105:
            return 'black'
        else:
            return 'red'

    m = folium.Map(location=[44.407, 8.917], zoom_start=15)

    # Add the GeoJSON layer to the map
    folium.GeoJson(
        json.loads(filtered_gdf.to_json()),
        style_function=lambda feature: {
            'fillColor': get_color(feature['properties']['Eta']),
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.6,
        }
    ).add_to(m)

    # Save the map as HTML string
    folium_map_html = m._repr_html_()

    return html.Iframe(srcDoc=folium_map_html, width='100%', height='600'), filtered_df.to_dict('records')

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)
