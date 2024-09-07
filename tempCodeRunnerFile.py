### Main script to calculate tax burden and transfers
"""
Calls on functions from other scripts
and saves the incidence results in a xlsx file

"""
import subprocess

import pandas as pd
from tax_burden_scaled import save_results
from transfers import save_results_public
from transfers import save_results_target


# INPUT DATA

# Country
country = "BGR"

# 1. INPUT DATA
# 1.1 MICRODATA

HH_data = pd.read_excel(f"./base_data/HH_data_with_elas.xlsx")

# 1.2 LOAD MINDSET RESULTS

MS = pd.read_excel(f"./base_data/results_{country}.xlsx", sheet_name=None)

# 1.2.4 PUBLIC INFRASTRUCTURE INVESTMENT -- If not applicable remove

public_inv = pd.read_csv("./base_data/Public_inv.csv", skiprows=1)

countrynames = pd.read_excel("./base_data/GTAPtoGLORIA.xlsx", sheet_name="Regions")

shares = pd.read_excel(
    f"./base_data/Templates_tax_BTA_{country}_GLORIA.xlsx", sheet_name="govt_spending"
)

# 1.3 CONCORDANCE TABLE

concordance = pd.read_excel(f"./base_data/GLORIA_CPAT_concordance.xlsx")

# 1.4 

pop_data = pd.read_csv(
        "./base_data/population/API_SP.POP.TOTL_DS2_en_csv_v2_5454896.csv", skiprows=4)

# 1.2.1 FINAL HOUSEHOLD DEMAND VECTOR -- Path/naming of variables has to be changed to location of MINDSET results

MS_final_demand = MS["output"]

MS_q = MS_final_demand.loc[
    MS_final_demand["REG_imp"] == country, ["PROD_COMM", "q_hh_base", "REG_imp"]
]

# 1.2.2 PRICE CHANGE VECTOR -- might have to be  - Path/naming of variables has to be changed to location of MINDSET results

# Price scenario
"""
Indicator variable which of MINDSETS price vectors is used,
depending on which price scenario the user wants to analyze

1: delta_p_base : Total price changes prior to any changes in technical coefficient for each sector TRAD_COMM in REG_exp
2: delta_p_0 : Total price changes after technological effect for each sector TRAD_COMM in REG_exp
3: delta_p_1: Total price changes after technological and trade effect for each sector TRAD_COMM
"""
scen = 3

MS_prices = MS["price"]

if scen == 1:
    MS_p = MS_prices.loc[MS_prices["REG_exp"] == country, ["TRAD_COMM", "delta_p_base"]]
elif scen == 2:
    MS_p = MS_prices.loc[MS_prices["REG_exp"] == country, ["TRAD_COMM", "delta_p0"]]
elif scen == 3:
    MS_p = MS_prices.loc[MS_prices["REG_exp"] == country, ["TRAD_COMM", "delta_p1"]]

# 1.2.3 REVENUE recycled into government spending and into direct transfers

MS_revenue = MS["revenue"]
MS_rev_inc = MS_revenue["recyc_inc"].loc[1]
MS_rev_govt = MS_revenue["recyc_govt"].loc[1]

# 1.2.4 OPTIONAL: Targeted deciles
"""
All deciles smaller or equal the chosen decile target
receive the transfer
"""

decile_target = 10

# 2. SAVE RESULTS

"""
Saves results into xlsx file in your current working directory
in a folder named "ISO3_household_results" . If the name of the
folder already exists, the results are appended to the existing file,
if not the folder is created.
Should the naming of the folder be changed, please adapt the path in the
save_results functions at the bottom of tax_burden_scaled.py and transfers.py


"""

# 2.1 SAVE ABSOLUTE AND RELATIVE TAX BURDEN + PRICE CHANGES PER CONS. CATEGORY
save_results(country = country, HH_data = HH_data, MS_q = MS_q, MS_p = MS_p, concordance = concordance , pop_data = pop_data)

# 2.2 SAVE TAX BURDEN WITH REVENUE RECYCLING

save_results_target(
    country = country, HH_data = HH_data, MS_q = MS_q, MS_p = MS_p, MS_rev_inc = MS_rev_inc, concordance = concordance, pop_data = pop_data ,decile_target = decile_target
)

# 2.3 SAVE TRANSFER PROXIES FOR INFRASTRUCTURE DISTRIBUTIONAL ANALYSIS

# if the share_rev_govt is not zero call the function
if not public_inv.empty:
    save_results_public(country = country, HH_data = HH_data, MS_rev_govt = MS_rev_govt, shares = shares, countrynames = countrynames, public_inv = public_inv , pop_data = pop_data)


# 2.4 Create Plots

subprocess.run(["Rscript", "plots.R"])
