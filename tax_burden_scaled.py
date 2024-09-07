import os

import numpy as np
import pandas as pd
from auxiliary import calc_pc_exp_dg
from auxiliary import calc_price_changes


#### ALL PATHS will be have to be reset
#### functions can be called here or in another script

################### FUNCTIONS ###########################################


def tax_burden_MS(country, HH_data, MS_q, MS_p, concordance , pop_data):
    """
    Calculates and returns tax burdens per expenditure decile for plots and returns:

    1. absolute and scaled to MINDSET hh demand
    2. relative tax burden (scaled to MINDSET hh demand) in percent of pretax (scaled to MINDSET expenditures)

    This function calls on multiple other functions, so all of the input data specified at the beginning of the script is needed

    Inputs:
        - country (str): 3-digit iso code
        - HH_data (df): Microdata
        - MS_q(df): MINDSET final household demand vector of country of interest:
                    Has to include columns "PROD_COMM" and "q_hh_base"
        - Ms_p(df): MINDSET sectoral price changes in country of interest:
                    Has to include columns "TRAD_COMM" and "delta_p"
                    "delta_p" depends on scenario (base, techn, trade) - column is renamed when
                    specifying scenario in main file
        - concordance : concordance table between GLORIA and expenditure categories
        - pop_data : Population data
    Returns:
        - HH_data_country_all (Pd.Dataframe): Dataframe containing following columns:
            - "iso3" : 3-digit iso code
            - "quant_cons" : expenditure decile
            -"abs_inc_MS" : absolute tax burden
            -"rel_inc_MS": tax burden relative to pretax expenditures
            -"abs_inc_ela_MS" : absolute tax burden with price-reaction
            -"rel_inc_ela_MS": absolute tax burden with price-reaction relative to pretax expenditures
            -"cons_pc_MS" : total consumption per capita per decile pre-policy
            -"price_reaction" : price reaction only -> for tests

    """

    # Get household data with expenditures scaled to Mindset demand
    HH_data_country_all = calc_pc_exp_dg(country, HH_data, MS_q, concordance, pop_data)

    # load dictionary containing the price changes per CPAT consumption category
    delta_p_g = calc_price_changes(MS_q, MS_p, concordance)

    # create a list of column names to iterate over
    cons_categories = [
        "appliances",
        "chemicals",
        "clothing",
        "communications",
        "education",
        "food",
        "health_srv",
        "housing",
        "other",
        "paper",
        "pharma",
        "rectourism",
        "transp_eqt",
        "transp_pub",
        "ely",
        "gso",
        "die",
        "ker",
        "lpg",
        "nga",
        "ethanol",
        "oil",
        "coa",
        "ccl",
        "fwd",
    ]
    # colnames with per capita consumption for all categories
    pc_cols = [col for col in HH_data_country_all.columns if col.endswith("_pc")]
    # total consumption per capita per decile
    HH_data_country_all["cons_pc_MS"] = HH_data_country_all[pc_cols].sum(axis=1)

    # containers
    abs_inc_MS = np.zeros(len(HH_data_country_all))
    rel_inc_MS = np.zeros(len(HH_data_country_all))
    abs_inc_ela_MS = np.zeros(len(HH_data_country_all))
    rel_inc_ela_MS = np.zeros(len(HH_data_country_all))
    price_reaction = np.zeros(len(HH_data_country_all))

    for cons in cons_categories:
        # extract relevant price changes from the price change dictionary
        delta_p = delta_p_g[cons]
        # convert HH survey expenditure shares into percent
        # for absoulte incidence multiply with total consumption per category (scaled to MINDSET)
        abs_inc_MS += delta_p * HH_data_country_all[f"{cons}_pc"]
        # for relative incidence multiply HH survey expenditure share (pre-scale) with prices
        rel_inc_MS += (
            delta_p
            * HH_data_country_all[f"{cons}_pc"]
            / HH_data_country_all["cons_pc_MS"]
        )
        col_ela = cons + "_elasticity_price"
        # price adjustment factors of demand with elasticites
        ela_values = HH_data_country_all[col_ela]
        adj_factor = (delta_p + 1) ** ela_values

        abs_inc_ela_MS += adj_factor * delta_p * HH_data_country_all[f"{cons}_pc"]
        rel_inc_ela_MS += (
            adj_factor
            * delta_p
            * HH_data_country_all[f"{cons}_pc"]
            / HH_data_country_all["cons_pc_MS"]
        )
        price_reaction += adj_factor * HH_data_country_all[f"{cons}_pc"]

    HH_data_country_all.loc[:, "abs_inc_MS"] = abs_inc_MS
    HH_data_country_all.loc[:, "rel_inc_MS"] = rel_inc_MS
    HH_data_country_all.loc[:, "abs_inc_ela_MS"] = abs_inc_ela_MS
    HH_data_country_all.loc[:, "rel_inc_ela_MS"] = rel_inc_ela_MS
    HH_data_country_all.loc[:, "price_reaction"] = price_reaction

    keep_columns = [
        "iso3",
        "quant_cons",
        "abs_inc_MS",
        "rel_inc_MS",
        "abs_inc_ela_MS",
        "rel_inc_ela_MS",
        "cons_pc_MS",
        "price_reaction",
    ]

    HH_data_country_all.drop(
        columns=[col for col in HH_data_country_all.columns if col not in keep_columns],
        inplace=True,
    )

    return HH_data_country_all


def save_results(country, HH_data, MS_q, MS_p, concordance , pop_data):
    """
    Saves sector shares , price changes by consumption categories and absolute and relative incidence
    by decile as xlsx to be used for further analysis or plots.

    """
    # Create the subfolder path in current working directory
    folder_path = os.path.join(os.getcwd(), f"{country}_household_results")

    # Create the subfolder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    pricechange = pd.DataFrame.from_dict(
        calc_price_changes(MS_q, MS_p, concordance),
        orient="index",
        columns=["price changes"],
    )
    pricechangecsv = pricechange.reset_index().rename(
        columns={"index": "consumption category"}
    )

    incidence = tax_burden_MS(country, HH_data, MS_q, MS_p, concordance , pop_data)

    # save all dataframes as csv

    pricechange_file_path = os.path.join(folder_path, "pricechange.xlsx")
    pricechangecsv.to_excel(pricechange_file_path, index=False)
    print(f"Saved DataFrame 'pricechange' as XLSX: {pricechange_file_path}")

    incidence_file_path = os.path.join(folder_path, "incidence.xlsx")
    incidence.to_excel(incidence_file_path, index=False)
    print(f"Saved DataFrame 'incidence' as XLSX: {incidence_file_path}")
