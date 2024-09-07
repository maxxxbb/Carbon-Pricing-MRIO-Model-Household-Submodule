import numpy as np
import pandas as pd
import pytest
from auxiliary import calc_pc_exp_dg
from auxiliary import calc_price_changes
from auxiliary import calc_tot_demand_g
from auxiliary import calculate_sectorshares
from auxiliary import get_pop
from dataprep import concordance_GLORIA_CPAT
from numpy.testing import assert_almost_equal
from Price_and_Income_Elas.sector_adj_factors import get_weighted_price_adj_factors
from Price_and_Income_Elas.sector_adj_factors import HHdemand_adjustments_price_GLORIA
from Price_and_Income_Elas.sector_adj_factors import HHdemand_adjustments_income_GLORIA 
from Price_and_Income_Elas.sector_adj_factors import get_weighted_income_adj_factors
from tax_burden_scaled import tax_burden_MS
from transfers import public_investment
from transfers import targeted_transfer


## if you want to run tests paths need to be adjusted : all fixtures rely on results_BGR.xlsx in base_data folder


@pytest.fixture(scope="module")
def HH_data():
    out = pd.read_excel("./base_data/HH_data_with_elas.xlsx")
    return out


@pytest.fixture(scope="module")
def MS_q():
    MS_Q = pd.read_excel("./base_data/Results_BGR.xlsx", sheet_name="output" , usecols = ["PROD_COMM","q_hh_base","REG_imp"])
    out = MS_Q.loc[MS_Q["REG_imp"] == "BGR"]
    return out


@pytest.fixture(scope="module")
def MS_p():
    MS_P = pd.read_excel("./base_data/Results_BGR.xlsx", sheet_name="price")
    out = MS_P.loc[MS_P["REG_exp"] == "BGR", ["TRAD_COMM", "delta_p_base"]]
    return out


@pytest.fixture(scope="module")
def MS_rev_inc():
    MS_REV = pd.read_excel("./base_data/Results_BGR.xlsx", sheet_name="revenue")
    out = MS_REV["recyc_inc"].loc[1]
    return out

@pytest.fixture(scope="module")
def MS_rev_govt():
    MS_REV = pd.read_excel("./base_data/Results_BGR.xlsx", sheet_name="revenue")
    out = MS_REV["recyc_govt"].loc[1]
    return out

@pytest.fixture(scope="module")
def concordance():
    out = pd.read_excel("./base_data/GLORIA_CPAT_concordance.xlsx")
    return out

@pytest.fixture()
def public_inv():
    out = pd.read_csv("./base_data/Public_inv.csv", skiprows=1)
    return out

@pytest.fixture()
def countrynames():
    out = pd.read_excel("./base_data/GTAPtoGLORIA.xlsx", sheet_name="Regions")
    return out

@pytest.fixture()
def shares():
    out = pd.read_excel(f"./base_data/Templates_tax_BTA_BGR_GLORIA.xlsx", sheet_name="govt_spending")
    return out
@pytest.fixture()
def pop_data():
    out = pd.read_csv(
        "./base_data/population/API_SP.POP.TOTL_DS2_en_csv_v2_5454896.csv", skiprows=4)
    return out

def test_sector_mapping():
    """
    Asserts 5 test GLORIA sectors
    are correctly mapped into their corresponding
    consumption category by concordance_GLORIA_CPAT.

    """
    expected_mappings = {
        5: "food",  # Growing rice
        12: "food",  # Growing fruits
        47: "food",  # Other meat products
        57: "clothing",  # Textiles and clothing
        101: "transp_pub",  # Road transport
    }

    actual_df = concordance_GLORIA_CPAT()

    for sector, cpat_category in expected_mappings.items():
        matching_row = actual_df[actual_df["GLORIASector"] == sector]
        assert matching_row["CPAT Variable"].values[0] == cpat_category


def test_sector_shares_add_up_to_one(MS_q,concordance):
    """
    Asserts that sector shares within a consumption category add up to one.
    """

    df = calculate_sectorshares( MS_q, concordance)
    sector_share_sum = df.groupby("CPAT Variable")["sector_share"].transform("sum")
    assert all(np.isclose(value, 1.0, rtol=1e-5) for value in sector_share_sum)


def test_calc_pricechanges(MS_q, MS_p,concordance):
    """
    Asserts that price changes are calculated correctly:

    Took appliances category and calculated price changes by hand

    -- If price vector changes, fixtures have to be changed too
    """
    deltap = calc_price_changes(MS_q,MS_p,concordance)

    expected = (
        0.044204 * 0.012625
        + 0.239944 * 0.012417
        + 0.019038 * 0.026704
        + 0.047707 * 0.016329
        + 0.001227 * 0.040966
        + 0.000979 * 0.054620
        + 0.065299 * 0.022106
        + 0.137560 * 0.008095
        + 0.110461 * 0.006952
        + 0.146042 * 0.004105
        + 0.187538 * 0.006463
    )

    actual = deltap["appliances"]

    assert_almost_equal(actual, expected, decimal=4)


def test_sector_shares(MS_q, concordance):
    """
    Check whether sector shares are correctly calculated by
    function: fixtures self calculated for paper cons. category.
    (GLORIA sectors 59,60,61)

    """

    papersum = 376850.5723 + 556864.9243 + 340833.4062
    expected = 376850.5723 / papersum
    sectors = calculate_sectorshares(MS_q,concordance)
    actual = sectors.loc[sectors["GLORIASector"] == 59, "sector_share"].values[0]

    assert_almost_equal(actual, expected, decimal=4)


def test_conspc(HH_data, MS_q, MS_p,concordance):
    """
    Tests weighted adj. factor function: Sum of decile total expenditures should
    be roughly similar (sum of budget shares not always sums to 1
    ) to the sum of expenditures
    """
    HH = HH_data[HH_data["iso3"] == "BGR"]
    expected = HH["cons_pc_acrent"].sum()

    sum_old = get_weighted_price_adj_factors("BGR", HH_data, MS_q, MS_p, concordance)[1]
    # old values calculated as sum over all deciles (share * cons_pc_acrent)
    actual = sum(sum_old.values())

    assert actual == pytest.approx(expected, abs=100)


def test_decile_shares(HH_data, MS_q,concordance, pop_data):
    """
    Tests whether shares of expenditures on category g
    for decile d add up to 1 for each category.
    """

    expected = 1.0
    df = calc_pc_exp_dg("BGR", HH_data, MS_q,concordance, pop_data)
    # Get the column names ending with 'share'
    share_columns = [col for col in df.columns if col.endswith("sharetotal")]

    # Calculate the actual sum for each column
    actual = df[share_columns].sum()

    # Check if the sum of each column is equal to the expected value
    assert np.isclose(actual, expected).all()


def test_calc_total_demand_g(HH_data, MS_q,concordance):
    """
    Tests whether
    total final hh demand for category g is calculated correctly
    and whether sum of total decile expenditures add up to
    sum of q_hh_base of the corresponding categories
    """


    expected = MS_q["q_hh_base"].sum() * 1000

    actual = sum(calc_tot_demand_g("BGR", HH_data, MS_q, concordance).values())

    assert np.isclose(actual, expected, rtol=0.0001)


def test_total_shares(HH_data, MS_q, concordance, pop_data):
    """
    Tests whether decile
    shares for all categories
    add up to 1
    """

    HH_full = calc_pc_exp_dg("BGR", HH_data, MS_q, concordance , pop_data)

    sharetotal_columns = HH_full.filter(regex="sharetotal$")

    column_sum = sharetotal_columns.sum(axis=0)

    actual = column_sum
    expected = 1

    assert np.isclose(actual, expected).all()


def test_calc_pc_exp_dc(HH_data, MS_q, concordance, pop_data):
    """
    Tests whether sum of per capita expenditures
    per consumption category per decile
    adds up to total demand per consumption
    category


    """

    HH_data_pc = calc_pc_exp_dg("BGR", HH_data, MS_q, concordance , pop_data)

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

    actual = {}
    for cons in cons_categories:

        key = cons
        actual[key] = (HH_data_pc[f"{cons}_pc"] * (1 / 10 * get_pop("BGR" , pop_data))).sum()

    expected = calc_tot_demand_g("BGR", HH_data, MS_q,concordance)

    for key in actual.keys():
        assert np.isclose(actual[key], expected[key], rtol=0.01)


def test_price_change_g(HH_data, MS_q, MS_p,concordance):
    """
    Tests whether price changes per GLORIA sector
    are the same as price changes per cons category

    with 1 % tolerance

    """
    # merge on GLORIA sectors
    merged = MS_p.merge(MS_q, left_on="TRAD_COMM", right_on="PROD_COMM")

    merged["expected_price_effect"] = merged["delta_p_base"] * merged["q_hh_base"]

    expected = (merged["expected_price_effect"].sum()) * 1000

    delta_p = calc_price_changes(MS_q, MS_p,concordance)
    demand_g = calc_tot_demand_g("BGR", HH_data, MS_q,concordance)

    # add price change * final demand
    actual = 0
    for key in delta_p:
        actual += delta_p[key] * demand_g[key]

    assert np.isclose(actual, expected, rtol=0.01)


def test_tax_burden(HH_data, MS_q, MS_p,concordance, pop_data):
    """
    Tests whether price changes * HH demand in GLORIA final demand vector
    is roughly equal to the sum of all decile tax burdens

    """
    pop2019 = get_pop("BGR", pop_data)
    tb = tax_burden_MS("BGR",HH_data, MS_q, MS_p,concordance , pop_data)
    
    # merge on GLORIA esctors
    merged = MS_p.merge(MS_q, left_on="TRAD_COMM", right_on="PROD_COMM")

    # Create a new column for the multiplication result
    merged["expected_price_effect"] = (
        merged["delta_p_base"] * merged["q_hh_base"]
    ) * 1000

    actual = (tb["abs_inc_MS"] * (pop2019 / 10)).sum()
    expected = merged["expected_price_effect"].sum()

    assert np.isclose(actual, expected, rtol=0.001)


def test_price_adj_factors_taxburden(HH_data, MS_q, MS_p,concordance, pop_data):
    """
    Test whether individual demand after price elasticites 
    elasticities (New expenditures) adds up to adjustment factors per category
    * total demand per expenditure category
    """

    hh_demand = calc_tot_demand_g("BGR", HH_data, MS_q,concordance)
    adj_factors = get_weighted_price_adj_factors("BGR", HH_data, MS_q, MS_p,concordance)[0]

    expected = sum(hh_demand[key] * adj_factors[key] for key in hh_demand)

    tb = tax_burden_MS("BGR",HH_data, MS_q, MS_p, concordance , pop_data)
    pop = get_pop("BGR", pop_data)
    # sum of new individual consumption
    actual = np.sum((tb["price_reaction"]) * pop / 10)

    assert np.isclose(actual, expected, rtol=0.01)


def test_price_adj_factors(HH_data, MS_q, MS_p, concordance):
    """
    Tests whether adjustment factors *q_hh_base at sectoral level
    add up to same change as at the cons category level
    """
    
    hh_demand = calc_tot_demand_g("BGR", HH_data, MS_q, concordance)
    adj_factors = get_weighted_price_adj_factors("BGR",HH_data, MS_q, MS_p, concordance)[0]

    expected = sum(hh_demand[key] * adj_factors[key] for key in hh_demand)

    adj_factors_GLORIA = HHdemand_adjustments_price_GLORIA(
        "BGR", HH_data, MS_q, MS_p, concordance
    )

    demand = MS_q
    
    actual = sum(demand["PROD_COMM"].map(adj_factors_GLORIA.squeeze()) * demand["q_hh_base"]) * 1000

    assert np.isclose(actual, expected, rtol=0.001)



def test_income_adj_factors(HH_data,MS_q,MS_rev_inc,concordance):
    """
    Tests whether income adjustment factors *q_hh_base at sectoral level
    add up to the same change as at cons category level
    """

    concordance = concordance_GLORIA_CPAT()
    hh_demand = calc_tot_demand_g("BGR", HH_data, MS_q,concordance)
    adj_factors = get_weighted_income_adj_factors("BGR", HH_data, MS_q,MS_rev_inc,concordance,decile_target= 3)

    expected = sum(hh_demand[key] * adj_factors[key] for key in hh_demand)

    adj_factors_GLORIA = HHdemand_adjustments_income_GLORIA(
        "BGR", HH_data, MS_q,MS_rev_inc,concordance,decile_target= 3
    )

    demand = MS_q
    actual = sum(demand["PROD_COMM"].map(adj_factors_GLORIA.squeeze()) * demand["q_hh_base"]) * 1000
    assert np.isclose(actual, expected, rtol=0.001)


def test_pc_transfer(HH_data,MS_q,MS_p,MS_rev_inc,concordance, pop_data):
    """
    Tests whether sum of per capita transfers
    sum up to the total revenue used for
    income tax cuts

    """

    expected = MS_rev_inc * 1000

    pop = get_pop("BGR" , pop_data)
    tb = targeted_transfer("BGR", HH_data, MS_q, MS_p, MS_rev_inc,concordance, pop_data,5)

    actual = np.sum(tb["pc_transfer"] * (pop / 10))

    assert np.isclose(actual, expected, rtol=0.0001)


def test_public_transfer(HH_data, MS_rev_govt, shares, countrynames , public_inv , pop_data):

    """
    tests whether transfers add up to share *
    revnue recycled into government spending

    THIS test only is suitable when all of the government spending goes into
    mapped infrastructure sectors (apart from waste)- as in running BGR example data-
    otherwise the test will fail as the expected transfer is the total government revenue
    recycling
    """
    
    country = "BGR"
    pop = get_pop(country, pop_data)

    transfer = public_investment(
        country, HH_data, MS_rev_govt, shares, countrynames , public_inv , pop_data
    )

    expected = MS_rev_govt*1000

    actual = actual = np.sum((transfer["total_publ_infr_transfer"]) * pop / 10)

    assert np.isclose(actual, expected, rtol=0.0001)
