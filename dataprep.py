
import pandas as pd
import numpy as np


def prepare_Microdata():
    """
    Merges expenditure data with price and income
    elasticity data on country and decile
    
    Inputs:
        - HH_Data_CPAT_ALL.dta
        - HH_Elasticities.xlsx
        - Income Elasticities_CPAT.xlsx
    """
    HH_survey = pd.read_stata("./base_data/HH_Data_CPAT_ALL.dta")
    HH_price_elasticities = pd.read_excel("./base_data/HH_Elasticities.xlsx")
    HH_income_elasticities = pd.read_excel("./base_data/Income Elasticities_CPAT.xlsx")

    # Merge elasticities: Suppose ethanole elasticity same as lpg elasticity
    HH_price_elasticities.loc[:,"ethanol_elasticity"] = HH_price_elasticities.loc[:,"lpg_elasticity"]
    HH_income_elasticities.loc[:,"ethanol_elasticity"] = HH_income_elasticities.loc[:,"lpg_elasticity"]
    
    HH_income_elasticities.drop(['code', 'year', 'sample', 'type', 'stat_type'],inplace=True, axis = "columns")
    
    HH_elasticities = pd.merge(HH_price_elasticities,HH_income_elasticities, on=['iso3', 'quant_cons'], suffixes=('_price', '_income'))

    # Prepare HH_survey
    HH_survey= HH_survey.loc[(HH_survey["stat_type"] == "mean") & (HH_survey["sample"] == "Overall") & (HH_survey['quant_cons'] != 9999)].copy()

    full_microdata = pd.merge(left = HH_survey , right = HH_elasticities, on = ['iso3', 'quant_cons'] , how = "left" , suffixes = (None,"_elas"))

    return full_microdata


    
def concordance_GLORIA_CPAT():    
    """
    Creates concordance table between GLORIA Sectors and CPAT consumption categories using
    GTAP 10 codes as a bridge

    Inputs: 
        - CPAT_GTAP.xlsx
        - GTAPtoGLORIA.xlsx

    Returns:
        CPAT_GLORIA(df) : Concordance between GLORIA and CPAT 
    """
    CPAT_GTAP = pd.read_excel("./base_data/CPAT_GTAP.xlsx", usecols= ["CPAT Variable", "GTAP10 code"])
    GTAP_GLORIA = pd.read_excel("./base_data/GTAPtoGLORIA.xlsx",sheet_name="Sectors")
    # merge concordance tables
    CPAT_GLORIA = pd.merge(GTAP_GLORIA[["Lfd_Nr","GTAP_Sector"]],CPAT_GTAP, left_on= "GTAP_Sector", right_on="GTAP10 code")
    CPAT_GLORIA.drop(columns=["GTAP_Sector","GTAP10 code"], inplace=True)
    CPAT_GLORIA.rename(columns={"Lfd_Nr": "GLORIASector"} , inplace = True)
    CPAT_GLORIA.drop_duplicates(inplace=True)
    CPAT_GLORIA.sort_values('GLORIASector', inplace=True, ascending=True)
    
    return CPAT_GLORIA


# both to excel


prepare_Microdata().to_excel("HH_data_with_elas.xlsx")