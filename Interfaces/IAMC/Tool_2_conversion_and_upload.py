import numpy as np
import pandas as pd
import time
import warnings

warnings.filterwarnings("ignore")

start_time = time.time()

def variable_Data(variable:pd.DataFrame, mapping:dict, variable_name:str, variable_unit:str) -> pd.DataFrame:
    "This function convert the data formate related to one variable to the IAMC formate"

    variable_df = variable.reset_index()
    variable_df["Node"].replace("", np.nan, inplace=True)

    # dropping empty rows
    variable_df.dropna(subset=["Node"], inplace=True)

    # dropping the last row of the total value
    variable_df.drop(index=variable_df[variable_df["Node"]=="Total flow"].index, inplace=True)

    # dropping unnamed columns
    variable_df    = variable_df.loc[:, ~variable_df.columns.str.contains('^Unnamed')]

    # transforming to the IAMC structure
    variable_df   = pd.melt(variable_df, id_vars='Node', value_vars=list(variable_df.columns[1:]), var_name='Region', value_name='value')

    # remove zero values
    variable_df   = variable_df.loc[~(variable_df['value'] == 0)]

    variable_df['Node']     = variable_df['Node'].astype(int)
    variable_df['From']     = variable_df['Region'].str.split('-', expand = True)[0].astype(int)
    variable_df['To']       = variable_df['Region'].str.split('-', expand = True)[1].astype(int)

    variable_df.replace(mapping,inplace=True)
    variable_df.reset_index(inplace=True)

    variable_df['region']   = ""+variable_df["Node"]+":"+variable_df["From"]+">"+variable_df["To"]
    variable_df['variable'] = variable_name
    variable_df['unit']     = variable_unit

    return variable_df.drop(columns=["Node","Region","From","To","index"])


# reading the output data file from InfraFair
region_mapping_pd   = pd.read_excel("InfraFair_mapping.xlsx", index_col=0, sheet_name="Region mapping") 
general_mapping_pd  = pd.read_excel("InfraFair_mapping.xlsx", index_col=0, sheet_name="Others")
investment_g        = pd.read_csv("Generation agents overall cost per asset.csv", index_col=0) 
investment_d        = pd.read_csv("Demand agents overall cost per asset.csv", index_col=0) 
flow_g              = pd.read_csv("Generation agents overall flow contribution per asset.csv", index_col=0) 
flow_d              = pd.read_csv("Demand agents overall flow contribution per asset.csv", index_col=0) 

# extracting result parameters
region_mapping_pd   = region_mapping_pd.set_index(["Mapped Node"])
general_mapping_pd  = general_mapping_pd.set_index(["Attribute"])
node_to_region_dic  = region_mapping_pd["Region"].to_dict()
model_name          = general_mapping_pd.loc["Model"][0]
scenario_name       = general_mapping_pd.loc["Scenario"][0]
unit_name           = general_mapping_pd.loc["Unit"][0].split(",")
year_name           = general_mapping_pd.loc["Year"][0]

# defining other parameters
subannual_name      = 'Year'
investment_g_var    = 'Network|Electricity|Investment|Allocated Investment|Generation'
investment_d_var    = 'Network|Electricity|Investment|Allocated Investment|Demand'
flow_d_var          = 'Network|Electricity|Active Power Flow|Flow Contribution|Demand'
flow_g_var          = 'Network|Electricity|Active Power Flow|Flow Contribution|Generation'

# Formate to IAMC  
investment_gt       = variable_Data(investment_g,node_to_region_dic,investment_g_var,unit_name[1])
investment_dt       = variable_Data(investment_g,node_to_region_dic,investment_d_var,unit_name[1])
flow_dt             = variable_Data(flow_d,node_to_region_dic,flow_d_var,unit_name[0])
flow_gt             = variable_Data(flow_g,node_to_region_dic,flow_g_var,unit_name[0])

InfraFair_IAMC      = pd.concat([investment_gt, investment_dt, flow_dt, flow_gt], ignore_index=True)

InfraFair_IAMC["model"]     = model_name
InfraFair_IAMC["scenario"]  = scenario_name
InfraFair_IAMC["model"]     = model_name
# InfraFair_IAMC["year"]      = year_name
# InfraFair_IAMC["subannual"] = subannual_name

# ordering the columns
InfraFair_IAMC              = InfraFair_IAMC[["model","scenario","region","variable","unit","value"]]
InfraFair_IAMC.rename(columns={"value":year_name}, inplace=True)
InfraFair_IAMC.to_excel("InfraFair IAMC.xlsx", index=False)

#%% end
print("EXECUTION TIME %s seconds"%(time.time() - start_time))

