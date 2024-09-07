import pandas as pd
import numpy as np

# exchange rates
er = pd.read_csv("./base_data/exchange_rates/API_PA.NUS.FCRF_DS2_en_csv_v2_5457514.csv", skiprows = 4)
# population
pop_wb = pd.read_csv("./base_data/population/API_SP.POP.TOTL_DS2_en_csv_v2_5454896.csv", skiprows= 4)
# gdp deflator
gdp_defl = pd.read_csv("./base_data/gdp_deflator/API_NY.GDP.DEFL.ZS_DS2_en_csv_v2_5455800.csv" , skiprows =4)
# gdp per capita
MS_q = pd.read_excel(f"./base_data/results_BGR.xlsx", sheet_name="output" , usecols = ["PROD_COMM","q_hh_base","REG_imp"])

HH_data = pd.read_excel("./base_data/HH_data_with_elas.xlsx")






def pcc_check(er,pop_wb,gdp_defl,MS_q,HH_data):
    """
    Creates xlsx to compare total per capita
    consumption from MINDSET (sum of q_hh_base divided by 2010 population)
    with inflation and population adjusted total per capita consumption from household survey
    
    Run this file for the output table - with files from base_data in Github repo and check that all of the data in base_data is accessible
    
    Inputs:
        - er (df): exchange rates
        - pop_wb (df): population
        - gdp_defl (df): gdp deflator
        - MS_q (df): MINDSET final household demand vector of country of interest from results_BGR.xlsx
        - HH_data (df): Microdata with elasticities
    
    Returns:
        - xlsx file with total per capita consumption from MINDSET and household survey
     
    """

    
    # All countries for which microdata is available
    countries = HH_data["iso3"].unique().tolist()

    # Create an empty DataFrame
    datalist = []

    # Iterate over the countries
    for country in countries:
        # Check if rows with HH_data iso3 exist for the current country
        if (MS_q["REG_imp"] == country).any():
            # Retrieve the HH_data for the current country
            HH_data_country = HH_data.loc[(HH_data["iso3"] == country)]
            # Check if any rows exist for the current country
            # Get the average HH expenditures data: avg. HH
            numeric_columns = HH_data_country.select_dtypes(include=[np.number]).columns
            HH_data_avg = HH_data_country[numeric_columns].mean().to_frame().T
            HH_data_avg.columns = numeric_columns
            
            # Get survey year
            survey_year = int(HH_data_avg["year"].iloc[0])
            
            # Get average HH expenditures
            avg_cons = HH_data_avg["cons_pc_acrent"].iloc[0]
            
            # Get exchange rate in the survey year: LCU per USD
            er_country = er[er["Country Code"] == country]
            # Excahnge rate in survey year
            er_sy = er_country[str(survey_year)].values[0]
            
            # Get  GDP deflator
            gdp_defl_country = gdp_defl[gdp_defl["Country Code"] == country]
            
            # GDP deflator for MINDSET year
            gdp_defl_2019 = gdp_defl_country[str(2019)].values[0]
            
            # GDP deflator for survey year
            gdp_defl_sy = gdp_defl_country[str(survey_year)].values[0]
        
            # GDP deflator ratio b/w survey year and MINDSET year
            gdp_ratio = gdp_defl_2019 / gdp_defl_sy
            
            # Calculate the average per capita consumption in 2019 USD
            avg_pc_cons_2019_dollar = avg_cons * (1/er_sy) * gdp_ratio
        
            # get population in 2019
            pop_country = pop_wb[(pop_wb["Country Code"] == country)]
            pop_2019 = (pop_country["2019"]).iloc[0]
            ## subset REG_IMP == country
            M_hhdemand = MS_q.loc[MS_q["REG_imp"] == country]
            q_hh_base_sum_pc = M_hhdemand["q_hh_base"].sum()/pop_2019 * 1000

            ## calc deviation

            percentage_deviation = abs((q_hh_base_sum_pc - avg_pc_cons_2019_dollar) / avg_pc_cons_2019_dollar) * 100
            perc = "{:.2f} %".format(percentage_deviation)
        
            dict = {'country': country, 'HH_Survey': avg_pc_cons_2019_dollar, 'MINDSET': q_hh_base_sum_pc , 'Percent_Deviation' : perc}
            datalist.append(dict)
        else:
            # Skip to the next country if no rows with reg_imp exist
            continue


    pd.DataFrame(datalist).to_excel('Survey_MINDSET_check.xlsx')

pcc_check(er,pop_wb,gdp_defl,MS_q,HH_data)