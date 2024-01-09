import pyam
import pandas as pd
import time
import warnings

warnings.filterwarnings("ignore")

start_time = time.time()

#%% downloading data from IIAS's server
# connecting to openentrance platform
conn              = pyam.iiasa.Connection('openentrance')

# querying data from openENTRANCE Platform
openTEPES_query   = conn.query(model = 'openTEPES 2.0.5', scenario = ['TF2030|00LEC','TF2030|Final Results|CS3|00 LEC'],
                               variable = ['Network|Electricity|Maximum Flow','Network|Electricity|Investment',
                                           'Final Energy|Electricity','Capacity|Electricity|{Electricity Input}',
                                           'Active Power|Electricity|{ Electricity Input}','Flow|Electricity',
                                           'Active Power|Electricity|{Electricity Input}','Capacity|Electricity|{ Electricity Input}',
                                           'Network|Electricity|Active Power Flow','Network|Electricity|Length','Network|Electricity|Capacity']
                                           )
openTEPES_pd      = openTEPES_query.as_pandas()

#%% converting the data from IIAS's format to InfraFair's format
# data transformation
variables   = openTEPES_pd['variable'].unique()

network_df  = openTEPES_pd.loc[openTEPES_pd[openTEPES_pd['variable'] == 'Final Energy|Electricity'].index,:]
assets_df   = openTEPES_pd.loc[openTEPES_pd[openTEPES_pd['variable'] == 'Network|Electricity|Capacity'].index,:]
# flow_df     = openTEPES_pd.loc[openTEPES_pd[openTEPES_pd['variable'] == 'Flow|Electricity'].index,:]

# converting values from GW to MW
network_df['value'] = network_df['value'].where(network_df['unit'] == 'MWh', network_df['value'].astype(float)*1000)
assets_df['value']  = assets_df['value'].where(assets_df['unit'] == 'MW', assets_df['value'].astype(float)*1000)
# flow_df['value']    = flow_df['unit'].where(flow_df['unit'] == 'MWh', flow_df['value'].astype(float)*1000)

# number of snapshots
flow_snapshots      = assets_df['subannual'].unique()   # this should be flow_df and there is no hourly snapshots for assets_df
n_flow_snapshots    = len(flow_snapshots)
network_snapshots   = network_df['subannual'].unique()
n_network_snapshots = len(network_snapshots)

# mapping the regions
assets_df['From']   = assets_df['region'].str.split('>', expand = True)[0]
assets_df['To']     = assets_df['region'].str.split('>', expand = True)[1]
regions             = set(assets_df['From']).union(set(assets_df['To']))
region_to_node      = dict(zip(sorted(regions),range(50,50 +len(regions))))
node_to_region      = dict(zip(range(50,50 +len(regions)),regions))
region_mapping      = pd.DataFrame(region_to_node, index = [1]).transpose()
region_mapping      = region_mapping.reset_index()
region_mapping      = region_mapping.rename(columns={"index":"Region",1: "Mapped Node"})

# processing the flow input data, in reality, this should be different and based on the variable Flow|Electricity
assets_df['From'].replace(region_to_node,inplace=True)
assets_df['To'].replace(region_to_node,inplace=True)
assets_df['Line'] = ""+assets_df['From'].astype(str)+"-"+assets_df['To'].astype(str)

if n_flow_snapshots == 1:    # single snapshot (annual)
    flow_tab = pd.DataFrame({'Line':assets_df['Line'].to_list(),'Flow sn1':assets_df['value'].to_list()})
else:                           # subannual snapshot
    # subannual mapping
    flow_subannual_snapshot  = dict(zip(sorted(set(assets_df['subannual'])),range(1,1 +len(assets_df['subannual'].unique()))))
    flow_subannual_mapping   = pd.DataFrame(flow_subannual_snapshot, index = [1]).transpose()
    flow_subannual_mapping   = flow_subannual_mapping.reset_index()
    flow_subannual_mapping   = flow_subannual_mapping.rename(columns={"index":"Subannual",1: "Snapshot"})
    
    # Here hourly flow data should be processed, similar to network hourly snapshots below (data not available now)

# assets attributes input data (in reality, this should be based on the variable Network|Electricity|Maximum Flow)
assets_attributes_tab = pd.DataFrame({'Line':assets_df['Line'].to_list(),'Capacity':assets_df['value'].to_list(),'Type':1})

# processing network data 
if n_network_snapshots == 1: # single snapshot (annual)
    # In reality, generation data, based on the variable Capacity|Electricity|{ Electricity Input}, should also be processed (not available now)
    network_tab = pd.DataFrame({"Node":network_df['region'].replace(region_to_node), "Demand sn1":network_df['value'], 
                                "Country":network_df['region'].str.split('|', expand = True)[0]})  
else:   # subannual snapshot
    # subannual mapping
    network_subannual_snapshot  = dict(zip(sorted(set(network_df['subannual'])),range(1,1 +len(network_df['subannual'].unique()))))
    network_subannual_mapping   = pd.DataFrame(network_subannual_snapshot, index = [1]).transpose()
    network_subannual_mapping   = network_subannual_mapping.reset_index()
    network_subannual_mapping   = network_subannual_mapping.rename(columns={"index":"Subannual",1: "Snapshot"})

    network_tab                 = network_df.pivot(index ='region',columns='subannual', values='value').reset_index() # later, before resetting the index, I can add the generation data
    network_tab.rename(columns=network_subannual_snapshot, inplace=True)
    network_tab                 = network_tab.add_prefix("Demand sn")
    network_tab.rename(columns={"Demand snregion":"Region"},inplace=True)
    network_tab['Node']         = network_tab['Region'].replace(region_to_node)
    network_tab['Country']      = network_tab['Region'].str.split('|', expand = True)[0]

# check data compatibility
if n_flow_snapshots != n_network_snapshots:
    print("ERROR: Flow input data are not compatible with network input data. The number of snapshots should be the same!")

#%% exporting converted data
# constructing an excel writer
writer      = pd.ExcelWriter("InfraFair_input_ready.xlsx", engine="xlsxwriter")
workbook    = writer.book

worksheet                           = workbook.add_worksheet("Flows")
writer.sheets["Flows"]              = worksheet
worksheet                           = workbook.add_worksheet("Assets attributes")
writer.sheets["Assets attributes"]  = worksheet
worksheet                           = workbook.add_worksheet("Network")
writer.sheets["Network"]            = worksheet

flow_tab.index+=1
flow_tab.to_excel(writer, sheet_name="Flows", startrow=0, startcol=0)
assets_attributes_tab.index+=1
assets_attributes_tab.to_excel(writer, sheet_name="Assets attributes", startrow=0, startcol=0)
network_tab.index+=1
network_tab.to_excel(writer, sheet_name="Network", startrow=0, startcol=0)

# Close the Pandas Excel writer and output the Excel file.
writer.close()

# exporting mapping files
writer      = pd.ExcelWriter("InfraFair_mapping.xlsx", engine="xlsxwriter")
workbook    = writer.book

worksheet                                       = workbook.add_worksheet("Region mapping")
writer.sheets["Region mapping"]                 = worksheet
region_mapping.index+=1
region_mapping.to_excel(writer, sheet_name="Region mapping", startrow=0, startcol=0)

if n_flow_snapshots > 1:
    worksheet                                   = workbook.add_worksheet("Flow subannual mapping")
    writer.sheets["Flow subannual mapping"]     = worksheet
    flow_subannual_mapping.index+=1
    flow_subannual_mapping.to_excel(writer, sheet_name="Flow subannual mapping", startrow=0, startcol=0)
    
if n_network_snapshots > 1:
    worksheet                                   = workbook.add_worksheet("Network subannual mapping")
    writer.sheets["Network subannual mapping"]  = worksheet
    network_subannual_mapping.index+=1
    network_subannual_mapping.to_excel(writer, sheet_name="Network subannual mapping", startrow=0, startcol=0)

worksheet                                       = workbook.add_worksheet("Others")
writer.sheets["Others"]                         = worksheet
# assuming one scenario and one year is processed (annual data)
pd.DataFrame({'Attribute':['Model','Scenario',"Year","Unit"], 'Value':["InfraFair 1.0.0",openTEPES_pd['scenario'][0],openTEPES_pd['year'][0],"MW,thousand USD_2010/yr"]}).to_excel(writer, sheet_name="Others", startrow=0, startcol=0)

# Close the Pandas Excel writer and output the Excel file.
writer.close()

#%% constructing control inputs for the model (with default values)
if n_flow_snapshots == 1:
    sn_weight = "1:8760"
if n_flow_snapshots >= 2:
    weight_factor = int(8760/n_flow_snapshots)
    sn_weight = [""+str(x)+":"+str(weight_factor)+"," for x in range(1,n_flow_snapshots+1)]

inputs_list             = ["Nodal Aggregation", "Demand Cost Responsibility (%)", "Generation Cost Responsibility (%)", "Length per Reactance (PU)", "Voltage Threshold (kV)", 
                            "Number of Snapshots", "Snapshots Weights", "Cost Allocation Option", "Utilization Threshold (%)", "Cost of Unused Capacity", 
                            "Demand Socialized Cost Responsibility (%)", "Generation Socialized Cost Responsibility (%)","Asset Types", "Snapshots Results", 
                            "Agent Results", "Country Results", "SO Results", "Intermediary Results", "Aggregated Results",]
values_list             = [0, 50, 50, 5, 132, n_flow_snapshots, ("".join(sn_weight))[:-1], 2, 20, 0, 100, 0, "Transmission line:1", 
                            0, 1, 0, 0, 0, 0,]
control_inputs          = pd.DataFrame({"Inputs":inputs_list,"Values":values_list})
control_inputs.index    = control_inputs.index + 1
control_inputs.to_excel("InfraFair control inputs.xlsx")

#%% end
print("EXECUTION TIME %s seconds"%(time.time() - start_time))
