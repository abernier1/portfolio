from shiny.express import input, render, ui
from shiny import reactive
from shinywidgets import render_widget  
from shinyswatch import theme
import urllib.request
import pandas as pd
import json
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from shapely.geometry import MultiPolygon
import plotly.express as px


# Shiny resources
# Deploy: https://shiny.posit.co/py/docs/deploy-cloud.html 
 

## Pull shape files data 
gadm=gpd.read_file('https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_ETH_1.json.zip')

# DHS API Documentation is here: https://api.dhsprogram.com/#/index.html

# Define a function for pulling data from the api and converting to dataframes
def pull_DHS(url):
    req = urllib.request.urlopen(url)
    resp = json.loads(req.read())
    my_data = resp['Data']
    df=pd.DataFrame(my_data)
    return df

#Query the API for a full list of indicators.-------
#indicator_list_url= "https://api.dhsprogram.com/rest/dhs/indicators?returnFields=IndicatorId,Label,Definition"
#indicator_list_df=pull_DHS(indicator_list_url)
#indicator_list_df.columns

# Restrict to a small set of indicators data ----------------
# There were 8 indicators that were selected for this project: 
# Percentage of households with electricity	HC_ELEC_H_ELC	Households with electricity
# Percentage of households with no electricity	HC_ELEC_H_NEL	Households with no electricity
# Percentage of the de jure population living in households with electricity	HC_ELEC_P_ELC	Population with electricity
# Percentage of the de jure population living in households with no electricity	HC_ELEC_P_NEL	Population with no electricity
# Percentage of households whose main source of drinking water is an improved source	WS_SRCE_H_IMP	Households using an improved water source
# Percentage of households with an improved water source on the premises	WS_SRCE_H_IOP	Households with improved water source on the premises
# Percentage of the de jure population living in households whose main source of drinking water is an improved source	WS_SRCE_P_IMP	Population using an improved water source
# Percentage of the de jure population living in households with an improved water source on the premises	WS_SRCE_P_IOP	Population with improved water source on the premises


# Import the data from Ethiopia's DHS surveys
ethiopia_url='http://api.dhsprogram.com/rest/dhs/data?breakdown=subnational&countryIds=ET&indicatorIds=HC_ELEC_H_ELC,HC_ELEC_H_NEL,HC_ELEC_P_ELC,HC_ELEC_P_NEL,WS_SRCE_H_IMP,WS_SRCE_H_IOP,WS_SRCE_P_IMP,WS_SRCE_P_IOP'
ethiopia_df=pull_DHS(ethiopia_url)
## Create mapping file to connect our data sources
mapping_admin1=pd.DataFrame({"CharacteristicLabel":['Tigray', 'Afar', 'Amhara', 'Oromia', 'Somali', 'Benishangul-Gumuz', 'SNNPR', 'Gambela', 'Harari', 'Addis Ababa', 'Dire Dawa'],"NAME_1":['Tigray', 'Afar', 'Amhara', 'Oromia', 'Somali', 'Benshangul-Gumaz', 'SouthernNations,Nationalities', 'GambelaPeoples', 'HarariPeople', 'AddisAbeba', 'DireDawa']})

### Combine data sources
gadm1 = pd.merge(gadm, mapping_admin1,  how="left")  
mapped_df = pd.merge(ethiopia_df, gadm1, on="CharacteristicLabel", how="left")  

# Get list of var_options for below
var_options = mapped_df.Indicator.unique().tolist()

# Sort options
var_options = sorted(var_options,reverse=True)

# Set initial value for var
var= var_options[0]




ui.page_opts(
    title="Demographic Health Surveys of Ethiopia",
    theme=theme.morph  
)



# Filter var_options to include only items containing "households"
hh_options = [option for option in var_options if "households" in option.lower()]
pop_options = [option for option in var_options if "population" in option.lower()]
CHOICES = {
  "Households": hh_options,
  "Populations": pop_options
}

with ui.sidebar():
    #ui.h3("Select an indicator to explore")
    ui.input_switch("households", "Swap to household data", value=False)
    ui.input_selectize("var", None, choices=CHOICES["Populations"])

    @reactive.effect
    def _():
        choices = "Households" if input.households() else "Populations"
        ui.update_selectize("var", label= "Select an indicator:", choices=CHOICES[choices])


   


with ui.navset_pill(id="tab"):  
    with ui.nav_panel("Map the most recent data"):
        with ui.layout_columns(col_widths=[7, 5]): #height="350px"):
            @render.plot(alt="A Map")  
            def plot():  
                map_df = mapped_df.copy()  

                # Keep most recent year only 
                map_df=map_df[map_df['SurveyYear']==map_df['SurveyYear'].max()]

                map_df= map_df[map_df['Indicator']==input.var()]

                title=map_df['Indicator'].to_list()[0] + ", " + str(map_df['SurveyYear'].to_list()[0])
                map_df = map_df[['Indicator','CharacteristicLabel','Value','geometry']]


                gdf = gpd.GeoDataFrame(map_df)
                # Plot Choropleth Map
                fig, ax = plt.subplots(figsize=(12, 6))
                gdf.plot(column="Value", cmap='Purples', linewidth=1, legend=False,edgecolor="grey", ax=ax)

                # Customize the plot
                ax.set_title(title, fontsize=14)
                ax.axis("off")  # Remove axis
                #plt.show(block=True)# Will print in console



                # Add labels for each region
                for idx, row in gdf.iterrows():
                    x, y = row.geometry.centroid.x, row.geometry.centroid.y  # Get centroid of each region
                    if row['CharacteristicLabel'] in ["Addis Ababa", "Dire Dawa"]:
                        y=y+.45
                    if row['CharacteristicLabel'] in ["Harari"]:
                        y=y-1
                    label = f"{row['CharacteristicLabel']}\n{row['Value']:.1f}%"  # Format label with one decimal place and percent sign
                    ax.annotate(label, xy=(x, y), xytext=(0, 0), textcoords="offset points",
                                ha='center', fontsize=6, color="black", weight="bold", bbox=dict(facecolor='white', alpha=0.5, edgecolor='none'))

                return fig





            @render_widget  
            def plot2(): 
                ## Filter the data
                ethiopia_df2= ethiopia_df[ethiopia_df['Indicator']==input.var()]
                # Keep most recent year only 
                ethiopia_df2=ethiopia_df2[ethiopia_df2['SurveyYear']==ethiopia_df2['SurveyYear'].max()]
                df = ethiopia_df2[['Indicator','CharacteristicLabel','Value']]
                df= pd.DataFrame(df)


                # Sort Data by 'Value' in Descending Order
                df = df.sort_values(by="Value", ascending=False)

                # Create Horizontal Bar Chart
                fig = px.bar(df, 
                            x="Value", 
                            y="CharacteristicLabel", 
                            orientation="h", 
                            text="Value",
                            title= "", #input.var(), #title was redundant
                            labels={"Value": "", "CharacteristicLabel": ""},
                            color="Value",  # Optional: color by value
                            color_continuous_scale='Purples'  
                            )

                # Improve Layout
                fig.update_traces(
                    textposition="outside",  # Show values outside bars
                    marker_line_color="grey",  # Add grey outline
                    marker_line_width=1  # Set outline width
                )
                fig.update_layout(yaxis=dict(categoryorder="total ascending"))  # Ensure highest is at top
                # Show Figure
                #fig.show() #Uncomment to print in browser window
                return fig
            


    with ui.nav_panel("Explore trends over time"):
        with ui.layout_columns(): #(height="250px"):
            @render_widget  
            def plot3():  
                # Create a line chart
                ethiopia_df3= ethiopia_df[ethiopia_df['Indicator']==input.var()]

                # Filter the data for the last year for each CharacteristicLabel
                last_year = ethiopia_df3['SurveyYear'].max()
                last_year_data = ethiopia_df3[ethiopia_df3['SurveyYear'] == last_year]

                # Create the line chart
                fig = px.line(
                    ethiopia_df3,
                    x="SurveyYear",  # X-axis: Year
                    y="Value",            # Y-axis: Value
                    color="CharacteristicLabel",  # Separate lines by CharacteristicLabel
                    title="Trends Over Time by Region",
                    labels={"SurveyYear": "Year", "Value": "Value (%)", "CharacteristicLabel": "Region"},
                    color_discrete_sequence=["#eac435", "#49416d", "#e08d79", "#23967f", "#4971C0",
                                             "#eac435", "#49416d", "#e08d79", "#23967f", "#4971C0",
                                             "#eac435", "#49416d", "#e08d79", "#23967f", "#4971C0",
                                             "#eac435", "#49416d", "#e08d79", "#23967f", "#4971C0"]  # Custom colors
                )

                # Add labels for the last year's data points
                for i, row in last_year_data.iterrows():
                    fig.add_annotation(
                        x= last_year, #len(ethiopia_df3.SurveyYear.unique())-1, #last_year,  # Last year
                        y=row['Value'],  # Value for the last year
                        text=row['CharacteristicLabel'],  # Label with CharacteristicLabel
                        showarrow=False,
                        font=dict(size=8, color="black"),
                        xanchor="left",
                        yanchor="auto"
                    )
                    
                # Improve layout
                fig.update_layout(
                    xaxis_title=" ",
                    yaxis_title="Value (%)",
                    title_x = 0.5,  # Center the title
                    legend_title=None,  # Remove legend
                    template="plotly_white",
                    showlegend=False  # Hide legend
                )

                # Show the figure
                #fig.show()
                return fig
            
            
            #ui.h2("All data retrieved from the API")
            @render.data_frame  
            def alldata_df():
                ethiopia_df4= ethiopia_df[['Indicator','SurveyYear','CharacteristicLabel','Value']]
                return render.DataTable(ethiopia_df4)
    with ui.nav_panel("About"):
        ui.markdown(
            """
            # About 
            This dashboard was created using the Shiny Python library. It pulls data from USAID's Demographic Health Surveys (DHS) API for Ethiopia and displays it in various ways. The map is generated using the Database of Global Administrative Areas (GADM)'s geometry. 
            The DHS Program has collected, analyzed, and disseminated accurate and representative data on population, health, HIV, and nutrition through more than 300 surveys in over 90 countries. GADM provides maps and spatial data for all countries and their sub-divisions.  
            The DHS API has data available for over 4500 indicators, but this dashboard focuses on a subset of 8 indicators related to electricity and water sources as it is intended to be a quick demo dashboard. These 8 indicators were selected because they are understood by a wide audience and have data for all Ethiopian regions. 

            ## Data Sources
            - [ICF. “The DHS Program website." Funded by USAID. http://www.dhsprogram.com. Accessed 03-21-2025.](https://dhsprogram.com/data/)
            - [The DHS Program Indicator Data API, The Demographic and Health Surveys (DHS) Program. ICF International. Funded by the United States Agency for International Development (USAID). Accessed 03-21-2025.](https://api.dhsprogram.com/#/index.html)
            - [GADM data (version 4.1), 2022.](https://gadm.org/)

            ## Packages used
            - [Shiny](https://shiny.posit.co/)
            - [ShinyWidgets](https://shinywidgets.posit.co/)
            - [ShinySwatch](https://shinyswatch.posit.co/)
            - [GeoPandas](https://geopandas.org/)
            - [Matplotlib](https://matplotlib.org/)
            - [Plotly](https://plotly.com/)
            - [Pandas](https://pandas.pydata.org/)
            - [Numpy](https://numpy.org/)
            - [Requests](https://docs.python-requests.org/en/master/)
            - [JSON](https://docs.python.org/3/library/json.html)

            ## Author
            This dashboard was created by Anne Bernier, a former USAID Data Scientist. 
            You can find the code on my [GitHub](https://github.com/abernier1/portfolio/) and you can find me on [LinkedIn](https://www.linkedin.com/in/anne-bernier-42338017/).
            
            """
        )


