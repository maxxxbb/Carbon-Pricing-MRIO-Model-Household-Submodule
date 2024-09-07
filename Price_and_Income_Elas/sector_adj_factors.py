import numpy as np
import pandas as pd


def get_weighted_price_adj_factors(country, HH_data, MS_q, MS_p, concordance):
    """
    Returns a dictionary of weighted adjustment factors per consumption category to be reused in the MINDSET
    Household Module.
    First country-specific HH and elasticity data, and MINDSET price changes per consumption category are used
    to calculate the adjustment factor of each expenditure category oer decile. Those are then weighted by the share
    of total expenditure per decile per category.

    Inputs:
        - country (str): The ISO 3 country code for the country of interest
        - HH_data (pd.DataFrame) : Household microdata
        - MS_q(df): MINDSET final demand vector (120 rows x 2 columns) of coubtry of interest

                need columns PROD_COMM and q_hh_base (if those are labelled differently change in code)

        - Ms_p(df): MINDSET price vector 120 rows x 2 columns of country of interest

                need columns TRAD_COMM and delta_p_base (change accordingly in code if labelled differently)

        - concordance (pd.DataFrame) : concordance table between GLORIA sectors and expenditure categories


    Returns:
        - sum_weighted_adj (dict) [0] : wtd. adj. factors per expenditure category
        - sum_old (dict) [1] : for checks: sum of old expenditures per category - for tests
    """
    # def list of consumption categories
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

    ## Read in and perepare countryspecific HH surveydata and elasticities : could be done elsewhere

    HH_data_countryoverall = HH_data.loc[(HH_data["iso3"] == country)].copy()

    # load dictionary containing the price changes per CPAT consumption category
    price_dict = calc_price_changes(MS_q, MS_p, concordance)

    for cons in cons_categories:

        # extract relevant price changes from the price change dictionary
        delta_p = price_dict[cons]
        # convert shares into percent
        share = HH_data_countryoverall[f"{cons}_share"] / 100
        # calculate pre-policy per capita consumption per decile per cons_category
        HH_data_countryoverall[f"old_cons_{cons}"] = (
            share * HH_data_countryoverall["cons_pc_acrent"]
        )
        # elasticity of cons. category
        ela_values = HH_data_countryoverall[f"{cons}_elasticity_price"]
        # calculate price elasticity adjustment factor per decile, per cateory
        adj_factor = (delta_p + 1) ** ela_values
        # add adjustment factor
        HH_data_countryoverall[f"adj_{cons}"] = adj_factor

    # for adjustment factors
    # sum of expenditures per category over all deciles
    sum_old = {
        x: HH_data_countryoverall[f"old_cons_{x}"].sum() for x in cons_categories
    }
    # share of expenditures by decile d per consumption category multiplied by adjustment factor per decile
    for cons in cons_categories:
        HH_data_countryoverall[f"adj_share_{cons}"] = (
            HH_data_countryoverall[f"old_cons_{cons}"]
            / sum_old[cons]
            * HH_data_countryoverall[f"adj_{cons}"]
        )

    # dictionary: consumption categories (keys) and weighted adjustment factors
    sum_weighted_adj = {
        cons: HH_data_countryoverall[f"adj_share_{cons}"].sum()
        for cons in cons_categories
    }

    return sum_weighted_adj, sum_old


def HHdemand_adjustments_price_GLORIA(country, HH_data, MS_q, MS_p, concordance):
    """
    Converts adjustment factors per consumption category into GLORIA sectoral
    demand adjustment factor
    Returns dictionary with GLORIA sectors as keys and adjustment factors
    as values. Adjustment factors are calculated based on decile
    specific price-elasticities of demand and shares of overall expenditures
    per decile and consumption category

    Inputs:
        - country(str): ISO-3 code
        - HH_data(df): prepared Microdata
        - MS_q(df): MINDSET final demand vector (120 rows x 2 columns) of coubtry of interest

                needs columns PROD_COMM and q_hh_base (if those are labelled differently change in code)

        - Ms_p(df): MINDSET price vector 120 rows x 2 columns of country of interest
                needs columns TRAD_COMM and delta_p_base (change accordingly in code if labelled differently)

        - concordance (df) : concordance table between GLORIA sectors and expenditure categories

    Returns:
        - adj_factors_price(df) : Dataframe with GLORIA sectors as the index column and price adjustment factors as the value column ("adj_factor")
    """
    sectors = concordance.copy()
    # [0] to get dictionary of cons_goods and corresponding adjustment factors
    adj_factors_g = get_weighted_price_adj_factors(
        country, HH_data, MS_q, MS_p, concordance
    )[0]

    # 1. Assign adjustment factors to corresponding sectors
    sectors["adj_factor"] = sectors["CPAT Variable"].map(adj_factors_g)

    # 2. for expenditure cat which are mapped to common sectors adjustment factors have to be weighted
    # workaround: drop columns where sector is 21,61,63 and manualy add with weighting
    sectors.drop(
        sectors[sectors["GLORIASector"].isin([62, 63, 21])].index, inplace=True
    )
    sectors.drop("CPAT Variable", axis=1, inplace=True)
    # load shares
    shares = petroleum_coke_frs_shares(country, HH_data)
    # def common sector expenditure categories
    sectors_62_63 = ["die", "gso", "ker", "lpg", "ethanol"]
    sectors_21 = ["ccl", "fwd"]
    # manually add the rows

    new_rows = pd.DataFrame(
        [
            [62, sum(adj_factors_g[key] * shares[key] for key in sectors_62_63)],
            [63, sum(adj_factors_g[key] * shares[key] for key in sectors_62_63)],
            [21, sum(adj_factors_g[key] * shares[key] for key in sectors_21)],
        ],
        columns=["GLORIASector", "adj_factor"],
    )

    # Concatenate the new DataFrame with the existing DataFrame

    adjustment_factor = pd.concat([sectors, new_rows], ignore_index=True)
    adjustment_factor.sort_values("GLORIASector", inplace=True)
    # convert to dictionary: GLORIA (keys) - Adj. factor (values)
    adj_factors_price = pd.DataFrame(
        adjustment_factor.set_index("GLORIASector")["adj_factor"]
    )

    return adj_factors_price


def get_weighted_income_adj_factors(
    country, HH_data, MS_q, MS_rev_inc, concordance, decile_target=10
):
    """
    Calculates decile specific income adjustment factors based on the
    decile specific income elasticities and expenditure shares. The user
    has the option to target a specific decile such that the tax revenue
    is distributed equally among the deciles (default: 10)

    Inputs:
            - country(str): ISO-3 code
            - HH_data(df): household data
            - MS_q(df): MINDSET final demand vector (120 rows x 2 columns) of coubtry of interest

                needs columns PROD_COMM and q_hh_base (if those are labelled differently change in code)
            - MS_rev_inc(float): Tax revenue to be recycled via income tax cut (in 1000 $)
            - concordance(df): concordance between GLORIA and expenditures
            - decile_target(int): decile to target
    Returns:
            - sum_weighted_adj(dict): dictionary with deciles as keys and
                adjustment factors as values
    """
    # 1. Inputs
    # country-specific Microdata
    HH_data = HH_data.loc[(HH_data["iso3"] == country)].copy()
    # transfer for each targeted decile
    revenue_decile = (MS_rev_inc / decile_target) * 1000

    MS_total_demand = calc_tot_demand_g(country, HH_data, MS_q, concordance)

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

    # transfer for targeted decile
    HH_data["revenue_decile"] = np.where(
        HH_data["quant_cons"] <= decile_target, revenue_decile, 0
    )
    # total household demand per expenditure category per decile
    for cons in cons_categories:
        # 1. calculate decile share of total expenditures per category
        HH_data[f"{cons}_sum"] = (
            HH_data[f"{cons}_share"] / 100 * HH_data["cons_pc_acrent"]
        )
        # calcuate share of total expenditures per category per decile
        HH_data[f"{cons}_sharetotal"] = (
            HH_data[f"{cons}_sum"] / HH_data[f"{cons}_sum"].sum()
        )
        # 2. ventilate total MINDSET demand per cons category g on deciles depending on their total shares for aggregate adjustment factor
        HH_data[f"total_{cons}_d"] = HH_data[
            f"{cons}_sharetotal"
        ] * MS_total_demand.get(cons)

    # calculate total expenditures per decile d by summing over all expenditure category totals
    HH_data["total_exp_d"] = HH_data[
        [f"total_{cons}_d" for cons in cons_categories]
    ].sum(axis=1)

    # create copy to avoid fragmentation warning -- can be removed
    HH_data_totalexp = HH_data.copy()

    # share of expenditures by decile d per consumption category to weight adjustment factors
    for cons in cons_categories:
        # calculate income effect of decile d and consumption category g
        HH_data_totalexp[f"income_effect_{cons}_d"] = (
            1 + (HH_data_totalexp["revenue_decile"] / HH_data_totalexp["total_exp_d"])
        ) ** HH_data_totalexp[f"{cons}_elasticity_income"]
        # calculate adjustment factor for decile d and consumption category g
        HH_data_totalexp[f"inc_adj_weighted_{cons}"] = (
            HH_data_totalexp[f"{cons}_sharetotal"]
            * HH_data_totalexp[f"income_effect_{cons}_d"]
        )

    # calculate the sum of the adjustment factors over all deciles weighted by adj_share
    sum_weighted_adj = {
        cons: HH_data_totalexp[f"inc_adj_weighted_{cons}"].sum()
        for cons in cons_categories
    }

    return sum_weighted_adj


def HHdemand_adjustments_income_GLORIA(
    country, HH_data, MS_q, MS_rev_inc, concordance, decile_target=10
):
    """
    Converts adjustment factors per consumption category into GLORIA sectoral
    demand adjustment factor
    Returns dictionary with GLORIA sectors as keys and adjustment factors
    as values. Adjustment factors are calculated based on decile
    specific price-elasticities of demand and shares of overall expenditures
    per decile and consumtion category

    Inputs:
        - country(str): ISO-3 code
        - HH_data(df): household data containing elasticities and expenditure shares
        - MS_q(df): final household demand ( GLORIA sectors x 1) : Mix between imports and exports
        - MS_rev_inc(float): revenue recycled into income tax cuts
        - concordance(df): concordance table between GLORIA and expenditure categories
        - decile_target(int): decile under and including which the tax revenue is distributed (default: 10))
    Returns:
        - adj_factors_g(df): pandas Dataframe with GLORIA sectors as the index column and income adjustment factors as value column ("adj_factor")
    """
    sectors = concordance.copy()
    # [0] to get dictionary of cons_goods and corresponding adjustment factors
    adj_factors_g = get_weighted_income_adj_factors(
        country, HH_data, MS_q, MS_rev_inc, concordance, decile_target
    )

    # 1. Assign adjustment factors to corresponding sectors
    sectors["adj_factor"] = sectors["CPAT Variable"].map(adj_factors_g)

    # 2. for expenditure cat which are mapped to common sectors adjustment factors have to be weighted
    # workaround: drop columns where sector is 21,61,63 and manualy add with weighting
    sectors.drop(
        sectors[sectors["GLORIASector"].isin([62, 63, 21])].index, inplace=True
    )
    sectors.drop("CPAT Variable", axis=1, inplace=True)
    # load shares
    shares = petroleum_coke_frs_shares(country, HH_data)
    # def common sector expenditure categories
    sectors_62_63 = ["die", "gso", "ker", "lpg", "ethanol"]
    sectors_21 = ["ccl", "fwd"]
    # manually add the rows

    new_rows = pd.DataFrame(
        [
            [62, sum(adj_factors_g[key] * shares[key] for key in sectors_62_63)],
            [63, sum(adj_factors_g[key] * shares[key] for key in sectors_62_63)],
            [21, sum(adj_factors_g[key] * shares[key] for key in sectors_21)],
        ],
        columns=["GLORIASector", "adj_factor"],
    )

    # Concatenate the new DataFrame with the existing DataFrame

    adjustment_factor = pd.concat([sectors, new_rows], ignore_index=True)
    adjustment_factor.sort_values("GLORIASector", inplace=True)
    # convert to dictionary: GLORIA (keys) - Adj. factor (values)
    adj_factors_price = pd.DataFrame(
        adjustment_factor.set_index("GLORIASector")["adj_factor"]
    )

    return adj_factors_price


######### AUXILIARY FUNCTIONS #############


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
            - 'delta_p_base': The change in price for the given GLORIA sector
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

    Returns:

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
    # multiply sector shares (q_hh_base) by price changes and add them per CPAT Variable, reset index to get delta_p_CPAT as output variable
    delta_p_CPAT = cpat_group.apply(
        lambda x: (x["sector_share"] * x["delta_p_base"]).sum()
    ).reset_index(name="delta_p_CPAT")
    # Return
    cpat_dict = dict(zip(delta_p_CPAT["CPAT Variable"], delta_p_CPAT["delta_p_CPAT"]))
    return cpat_dict


def petroleum_coke_frs_shares(country, HH_data):
    """
    Calculates shares for refined petroleum
    and coke oven products: Multiple consumption
    categories mapped to two GLORIA sectors so
    final GLORIA demand has to be split up accordingly

    Inputs:

    - country : country of interest
    - HH_data : household expenditure data

    Returns:

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

    # list of categories
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
        - HH_data (df): Microdata containing expenditure shares
        - MS_q(df): MINDSET final demand vector (120 rows x 2 columns)
                    needs columns PROD_COMM and q_hh_base (if those are
                    labelled differently change in code)
        - concordance(df): concordance table between GLORIA and expenditure categories
    Returns:
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
