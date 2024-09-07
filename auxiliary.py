import numpy as np
import pandas as pd


def calculate_sectorshares(MS_q, concordance):
    """
    Calculate sector shares of final demand per CPAT category for a given country using MINDSET final
    household demand vector and concordance table prodced by concordance_GLORIA_CPAT(). Finally it merges
    the dataframe with MINDSET price changes for the relevant GLORIA sectors.


    Inputs:

        - country(str): the iso-3 code of the country for which to calculate sector shares.

        - MS_q(df): MINDSET final demand vector (120 rows x 2 columns) of coubtry of interest

                need columns PROD_COMM and q_hh_base (if those are labelled differently change in code)

        - concordance(df): concordance table between GLORIA and expenditure categories

    Outputs:

        df_prices : pandas.DataFrame
            A DataFrame with the following columns:
            - 'CPAT Variable': The CPAT consumption category
            - 'GLORIASector': The GLORIA sector
            - 'sector_share': Share of final HH demand of GLORIA sectors within the CPAT category
    """

    # Load concordance table : INPUT
    cpat_glor = concordance

    # merge exploded concordance table with MINDSET Household demand results
    merged = pd.merge(
        cpat_glor, MS_q, left_on="GLORIASector", right_on="PROD_COMM", how="inner"
    )
    # Calculate sector shares of final demand per CPAT category and convert into dataframe

    sectorshares = pd.DataFrame(
        merged.groupby(["CPAT Variable", "GLORIASector"])["q_hh_base"].sum()
        / merged.groupby("CPAT Variable")["q_hh_base"].sum()
    )
    # reset index to get single index df
    sectorshares.reset_index(inplace=True)
    sectorshares.rename(columns={"q_hh_base": "sector_share"}, inplace=True)

    return sectorshares


def calc_price_changes(MS_q, MS_p, concordance):
    """
    Calculate the price changes per CPAT consumption category for a given country.
    The function calls calculate_sectorshares() which returns a dataframe including mapped
    CPAT cons. categories , GLORIA Sectors and their corresponding MINDSET price changes.

    Inputs:

        - country(str): the iso-3 code of the country for which to calculate sector shares.

        - MS_q(df): MINDSET final demand vector (120 rows x 2 columns)

                need columns PROD_COMM and q_hh_base (if those are labelled differently change in code)

        - Ms_p(df): MINDSET price vector 120 rows x 2 columns

                need columns TRAD_COMM and delta_p_base (change accordingly in code if labelled differently)

        - concordance(df): concordance table between GLORIA and expenditure categories

    Outputs:

        delta_p_CPAT(dict): A dictionary containing the price changes as values and CPAT consumption categories as keys
    """
    # load sectorshares
    sectorshares = calculate_sectorshares(MS_q, concordance)
    # merge with MINDSET price changes
    df_prices = pd.merge(
        sectorshares, MS_p, left_on="GLORIASector", right_on="TRAD_COMM"
    )
    # drop duplicate sector col
    df_prices.drop(columns="TRAD_COMM", inplace=True)
    # group by CPAT Variable again to calculate price changes per CPAT consumption category
    cpat_group = df_prices.groupby("CPAT Variable")

    # define price column name : named differently in different scenarios
    delta_p_column = [col for col in df_prices.columns if col.startswith("delta_p")][0]
    # multiply sector shares (q_hh_base) by price changes and add them per CPAT Variable, reset index to get delta_p_CPAT as output variable
    delta_p_CPAT = cpat_group.apply(
        lambda x: (x["sector_share"] * x[delta_p_column]).sum()
    ).reset_index(name="delta_p_CPAT")
    # Return
    cpat_dict = dict(zip(delta_p_CPAT["CPAT Variable"], delta_p_CPAT["delta_p_CPAT"]))

    return cpat_dict


def petroleum_coke_frs_shares(country, HH_data):
    """
    Calculates expenditure shares for refined petroleum
    and coke oven products within the respective GLORIA sectors: Multiple consumption
    categories mapped to two GLORIA sectors so
    final GLORIA demand has to be split up accordingly

    Inputs:

    - country : country of interest
    - HH_data : household expenditure data containing budget shares

    Outputs:

    - shares_cp (dict): expenditure categories (keys) , shares (values)
    """
    HH_data_country = HH_data.loc[(HH_data["iso3"] == country)]
    ## create column for average hh
    HH_data_country = HH_data[HH_data["iso3"] == "BGR"]

    ## Add average row to split up
    numeric_columns = HH_data_country.select_dtypes(include=[np.number])

    # Calculate the average values for numeric columns
    average_values = numeric_columns.mean()

    # Create new avg row
    average = pd.DataFrame(average_values).T
    average["quant_cons"] = "avg"

    # list of categories mapped to p_c
    pc_list = ["die", "ethanol", "gso", "ker", "lpg"]
    # calculate sum of shares for expenditure categories in g_list+
    sharesum_pc = sum(average[f"{g}_share"].values[0] for g in pc_list)
    # shares dictionary for coke and petroleum products
    shares_pc = {g: average[f"{g}_share"].values[0] / sharesum_pc for g in pc_list}
    # same for charcoal and firewood
    frs_list = ["ccl", "fwd"]
    sharesum_frs = sum(average[f"{g}_share"].values[0] for g in frs_list)
    shares_frs = {g: average[f"{g}_share"].values[0] / sharesum_frs for g in frs_list}

    shares_pc.update(shares_frs)

    return shares_pc


def calc_tot_demand_g(country, HH_data, MS_q, concordance):
    """
    Returns the total household demand per consumption category G
    based on MINDSETS final household demand per GLORIA sector.

    Inputs:
        - country (str): 3-digit iso code
        - HH_data (df): Microdata
        - MS_q(df): MINDSET final demand vector (120 rows x 2 columns)
                    needs columns PROD_COMM and q_hh_base (if those are
                    labelled differently change in code)
        - concordance(df): concordance table between GLORIA and expenditure categories
    Output:
        - total_hh_demand_g (dict): dictionary containing total hh demand (values)
                                    in 2019 US$ for each consumption category (G)

    """

    cpat_glor = concordance

    # merge exploded concordance table with MINDSET Household demand results
    merged = pd.merge(
        cpat_glor, MS_q, left_on="GLORIASector", right_on="PROD_COMM", how="inner"
    )
    # Calculate sector shares of final demand per CPAT category and convert into dataframe
    total_hh_demand_G = merged.groupby("CPAT Variable")["q_hh_base"].sum().to_dict()

    # multiply by 1000 and by expenditure shares within sector
    # when refined petroleum or coke oven products

    p_c_shares = petroleum_coke_frs_shares(country, HH_data)

    result = {}

    # for all sectors mapped to multiple cons categories:  multiply hh demand with share
    for key in total_hh_demand_G:
        if key in p_c_shares:
            result[key] = total_hh_demand_G[key] * p_c_shares[key] * 1000
        else:
            result[key] = total_hh_demand_G[key] * 1000

    return result


def get_pop(country,pop_data):
    """
    Reads and returns official 2019 population of country
    from https://data.worldbank.org/indicator/SP.POP.TOTL

    Inputs:
        - country (str) : 3-digit iso code
    Outputs:
        - pop2019 (int) : population in 2019
    """
    pop_wb = pop_data
    # select country and year
    pop_country = pop_wb[(pop_wb["Country Code"] == country)]
    pop_2019 = (pop_country["2019"]).iloc[0].astype(int)

    return pop_2019


def calc_pc_exp_dg(country, HH_data, MS_q, concordance , pop_data):
    """
    Calculates per capita expenditures per decile and consumption category g
    based on expenditure shares and shares of total expenditures
    per decile from household survey data and final HH_demand per
    cons. category G from MINDSET to have absolute tax burdens which
    are consistent with MINDSET revenue results.

    Inputs:
        - country (str): 3-digit iso code
        - HH_data (df): Microdata
        - MS_q(df): MINDSET final household demand vector of country of interest:
                    Has to include columns "PROD_COMM" and "q_hh_base"

        - concordance : concordance table between GLORIA and expenditure categories
    Outputs:

        - HH_cdf(df): HH survey dataframe with added decile shares of total consumption
        for each category, total consumption per category/decile (in 2019 US$) and per capita expenditures
        per decile/category (in 2019 US$).

    """

    # subset country of interest
    HH_df = HH_data.loc[(HH_data["iso3"] == country)].copy()
    # list of consumption categories
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
    # load dictionary with total demand by category g ( in 1000 US$ )
    MS_total_demand = calc_tot_demand_g(country, HH_data, MS_q, concordance)
    # load 2019 population
    pop2019 = get_pop(country,pop_data)

    for cons_category in cons_categories:
        # 1. calculate decile share of total expenditures per category
        HH_df[f"{cons_category}_sum"] = (
            HH_df[f"{cons_category}_share"] / 100 * HH_df["cons_pc_acrent"]
        )
        HH_df[f"{cons_category}_sharetotal"] = (
            HH_df[f"{cons_category}_sum"] / HH_df[f"{cons_category}_sum"].sum()
        )
        # 2. ventilate total MINDSET demand per cons category g on deciles depending on their total shares
        HH_df[f"total_{cons_category}_d"] = HH_df[
            f"{cons_category}_sharetotal"
        ] * MS_total_demand.get(cons_category)
        # 3. divide by tenth of 2019 population
        HH_df[f"{cons_category}_pc"] = HH_df[f"total_{cons_category}_d"] * (
            10 / pop2019
        )

    return HH_df
