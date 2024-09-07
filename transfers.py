import os

import numpy as np
import pandas as pd
from auxiliary import get_pop
from tax_burden_scaled import tax_burden_MS

#### Direct transfers


def targeted_transfer(
    country, HH_data, MS_q, MS_p, MS_rev_inc, concordance,pop_data, decile_target
):
    """
    Calculates tax burden after revenue recycling via direct targeted per capita transfers
    Absolute tax burden after revenue recycling is calculated as pre-revenue recycling tax burden
    calculated by tax_burden_MS() minus the received per capita transfer.


    Inputs:
        - country (str): 3-digit iso code
        - HH_data (df): Microdata
        - MS_q(df): MINDSET final household demand vector of country of interest:
                    Has to include columns "PROD_COMM" and "q_hh_base"
        - Ms_p(df): MINDSET sectoral price changes in country of interest:
                    Has to include columns "TRAD_COMM" and "delta_p"
                    "delta_p" depends on scenario (base, techn, trade) - column is renamed when
                    specifying scenario in main file
        - MS_rev_inc(float) : total tax revenue to be recycled via direct transfers
        - concordance (df): concordance table between GLORIA and expenditure categories
        - pop_data (df): Population data
        - decile_target (int): OPTIONAL-targeted deciles for per capita transfers (default = 10 )

    Output;

        - tb (df): Dataframe containing absolute and relative tax burdens for each decile
                    after revenue recycling in form of direct per capita transfers
    """

    tb = tax_burden_MS(
        country=country, HH_data=HH_data, MS_q=MS_q, MS_p=MS_p, concordance=concordance , pop_data=pop_data
    )

    # GLORIA population
    population = get_pop(country, pop_data)

    ## per capita transfer for deciles
    targeted_population = population * decile_target / 10
    # avg. transfer for targeted deciles capita decile (in 2019 $)
    pc_transfer = MS_rev_inc * 1000 / targeted_population

    tb["abs_inc_RR"] = np.where(
        tb["quant_cons"] <= decile_target,
        tb["abs_inc_MS"] - pc_transfer,
        tb["abs_inc_MS"],
    )
    tb["rel_inc_RR"] = tb["abs_inc_RR"] / tb["cons_pc_MS"]
    # with price reactions
    tb["abs_inc_ela_RR"] = np.where(
        tb["quant_cons"] <= decile_target,
        tb["abs_inc_ela_MS"] - pc_transfer,
        tb["abs_inc_ela_MS"],
    )
    tb["rel_inc_ela_RR"] = tb["abs_inc_ela_RR"] / tb["cons_pc_MS"]
    tb["pc_transfer"] = np.where(tb["quant_cons"] <= decile_target, pc_transfer, 0)

    return tb


def public_investment(country, HH_data, MS_rev_govt, shares, countrynames, public_inv , pop_data):
    """

    Distribution of public investment in infrastructure access spending - proxied as
    cash transfers towards deciles with non-existing access.
    Proxied transfers are received by households without pre-existing
    access to infrastructure type i:

    Inputs:
        - country(str): 3 digit iso code of country
        - HH_data (df): Microdata
        - MS_rev_govt (float) : total tax revenue to be recycled into government spending
        - shares(df): Dataframe with shares of revenue recycled into government spending
                    per GLORIA sector. From Templates_tax_BTA_{country}_GLORIA.xlsx,
                    sheet "govt_spending"
        - countrynames(df): Dataframe mapping countrynames and ISO3 codes.
                            From "REGIONS" sheet of GTAPtoGLORIA.xlsx.
        - public_inv(df): Dataframe with other investment into infrastructure categories
        - pop_data(df): Population data

    Returns:
        - HH_data_country(df):  Dataframe with per proxied per capita transfers when investing in public infrastructure

    """
    HH_data_country = HH_data.loc[(HH_data["iso3"] == country)]

    # Load shares of government spending per infrastructure category
    share_dict = get_publ_inv_shares(country, shares)
    # Load other investment into infrastructure categories and mulitply by 1000 (in 2019 1000$)
    total_dict = get_other_investment(country, countrynames, public_inv)
    # Read MINDSET tax revenues

    spending = MS_rev_govt * 1000

    # Get population data
    population = get_pop(country,pop_data)

    # List of infrastructure categories
    infr_list = list(share_dict.keys())

    # Calculate population without access for each infrastructure category
    for i in infr_list:
        HH_data_country[f"pop_no_acs_{i}"] = (
            (1 - HH_data_country[f"{i}_acs_share"] / 100) * population / 10
        )

    # Save total population without access for each infrastructure category as dictionary
    pop_no_access_i = {i: HH_data_country[f"pop_no_acs_{i}"].sum() for i in infr_list}
    # Calculate per capita transfer for each infrastructure category : share of gov i * spending i / targeted population - pop with no access to category i
    per_cap_transfer_i = {
        key: ((share_dict[key] * spending )+ total_dict[key]) / pop_no_access_i[key]
        for key in infr_list
    }

    for i in infr_list:
        HH_data_country[f"per_cap_transfer_{i}"] = HH_data_country.apply(
            lambda row: (1 - row[f"{i}_acs_share"] / 100) * per_cap_transfer_i[i],
            axis=1,
        )

    # sum transfers for different categories
    HH_data_country["total_publ_infr_transfer"] = HH_data_country.filter(
        like="per_cap_transfer_"
    ).sum(axis=1)
    # drop intermediate columns
    per_cap_cols = [
        col for col in HH_data_country.columns if col.startswith("per_cap_transfer")
    ] + ["total_publ_infr_transfer", "quant_cons"]

    HH_data_country.drop(
        columns=[col for col in HH_data_country.columns if col not in per_cap_cols],
        inplace=True,
    )

    return HH_data_country


def get_publ_inv_shares(country, shares):
    """
    Retrieves shares of revenue recycled into government spending
    used for each infrastructure category from tax template.
    GLORIA sectors are mapped as follows:

    "wtr" : 60% of total investment into water sector [95]
    "sani" : [95] * 40% + [96] * 20%
    "ely" = [93] ,
    "ICT" : [110,111]
    "transpub" = [101,102,104,106]

    Inputs:
        -country(str): 3 digit iso code of country
        -shares(df): Dataframe with shares of revenue recycled into government spending
                    per GLORIA sector. From Templates_tax_BTA_{country}_GLORIA.xlsx,
                    sheet "govt_spending"
    Outputs:
        -pi_share_dict(dict): Dictionary with shares of revenue recycled [value] per consumption category i [key]

    """
    shares = shares.loc[shares["REG"] == country]
    pi_share_dict = {
        "wtr": 0.6 * shares.loc[shares["PROD_COMM"] == 95, "govt_spend"].values[0],
        "sani": 0.4 * shares.loc[shares["PROD_COMM"] == 95, "govt_spend"].values[0]
        + 0.2 * shares.loc[shares["PROD_COMM"] == 96, "govt_spend"].values[0],
        "ely": shares.loc[shares["PROD_COMM"] == 93, "govt_spend"].values[0],
        "ICT": shares.loc[shares["PROD_COMM"] == 110, "govt_spend"].values[0]
        + shares.loc[shares["PROD_COMM"] == 111, "govt_spend"].values[0],
        "transp_pub": shares.loc[shares["PROD_COMM"] == 101, "govt_spend"].values[0]
        + shares.loc[shares["PROD_COMM"] == 102, "govt_spend"].values[0]
        + shares.loc[shares["PROD_COMM"] == 104, "govt_spend"].values[0]
        + shares.loc[shares["PROD_COMM"] == 106, "govt_spend"].values[0],
    }
    return pi_share_dict


def get_other_investment(country, countrynames, public_inv):
    """
    Gets total bulk, debt or else financed public investment
    per infrastructure category

    Inputs:
        - country(str): 3 digit iso code of country
        - countrynames(df): Dataframe with countrynames and iso codes.
                            From last sheet of GTAPtoGLORIA.xlsx.
        - public_inv(df): Dataframe containing public investment in 1000 US$ per
                          GLORIA sector and country. From Public_inv.csv(
                            first row has to be excluded
                          )

    Outputs:
      - public_inv_dict(dict): Dictionary with other public investment per infrastructure category in $

    """

    # Get countryname corresponding to ISO3 code
    countryname = countrynames.loc[
        countrynames["Region_acronyms"] == country, "Region_names"
    ].values[0]

    # rename index column from unnamed:0 to countryname
    public_inv.rename(columns={"Unnamed: 0": "Region_names"}, inplace=True)

    # use column where countryname is in the row
    public_inv = public_inv.loc[public_inv["Region_names"] == countryname]

    pi_other_dict = {
        "wtr": 1000 * 0.6 * public_inv["95"].values[0],
        "sani": 1000* (0.4 * public_inv["95"].values[0] +  0.2 * public_inv["96"].values[0]),
        "ely": 1000* public_inv["93"].values[0],
        "ICT": 1000*(public_inv["110"].values[0] + public_inv["111"].values[0]),
        "transp_pub": 1000*public_inv["101"].values[0]
        + 1000*public_inv["102"].values[0]
        + 1000*public_inv["104"].values[0]
        + 1000*public_inv["106"].values[0],
    }

    return pi_other_dict


def save_results_target(
    country, HH_data, MS_q, MS_p, MS_rev_inc, concordance, pop_data, decile_target=10
):
    """
    Saves sector shares , price changes by consumption categories and absolute and relative incidence
    by decile as csv to be used for further analysis or plots.

    Parameters:
        - country (str): 3-digit iso code
        - HH_data (df): Microdata
        - MS_q(df): MINDSET final household demand vector of country of interest:
                    Has to include columns "PROD_COMM" and "q_hh_base"
        - Ms_p(df): MINDSET sectoral price changes in country of interest:
                    Has to include columns "TRAD_COMM" and "delta_p"
                    "delta_p" depends on scenario (base, techn, trade) - column is renamed when
                    specifying scenario in main file
        - MS_rev_inc(float) : total tax revenue to be recycled via direct transfers
        - concordance (df): concordance table between GLORIA and expenditure categories
        - pop_data (df): population data
        - decile_target (int): OPTIONAL-targeted deciles for per capita transfers (default = 10 )


    """
    # Create the subfolder path in current working directory
    folder_path = os.path.join(os.getcwd(), f"{country}_household_results")

    # Create the subfolder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    pct = targeted_transfer(
        country, HH_data, MS_q, MS_p, MS_rev_inc, concordance, pop_data, decile_target
    )

    targeted_transfer_path = os.path.join(folder_path, "transfers.xlsx")
    pct.to_excel(targeted_transfer_path, index=False)
    print(f"Saved DataFrame 'transfers' as XLSX: {targeted_transfer_path}")


def save_results_public(
    country, HH_data, MS_rev_govt, shares, countrynames, public_inv , pop_data
):
    """
    Function to save results of public investment in infrastructure access spending
    as xlsx. Change working directory to folder where you want to save the results.

    Inputs:
        - country(str): 3 digit iso code of country
        - HH_data (df): Microdata
        - MS_rev_govt (float) : total tax revenue to be recycled into government spending
        - shares(df): Dataframe with shares of revenue recycled into government spending
                    per GLORIA sector. From Templates_tax_BTA_{country}_GLORIA.xlsx,
                    sheet "govt_spending"
        - countrynames(df): Dataframe mapping countrynames and ISO3 codes.
                            From "REGIONS" sheet of GTAPtoGLORIA.xlsx.
        - public_inv(df): Dataframe containing public investment per country /sector
        - pop_data(df) : Dataframe containing population per country

    Saves per proxied per capita transfers when investing in public infrastructure as xlsx to be used for further analysis or plots.

    """
    # Create the subfolder path in current working directory
    folder_path = os.path.join(os.getcwd(), f"{country}_household_results")

    # Create the subfolder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Public transfer

    pia = public_investment(
        country, HH_data, MS_rev_govt, shares, countrynames, public_inv, pop_data
    )

    public_transfer_path = os.path.join(folder_path, "public_infr.xlsx")
    pia.to_excel(public_transfer_path, index=False)
    print(f"Saved DataFrame 'public_infr' as XLSX: {public_transfer_path}")
