"""
InfraFair: Modelling tool for Infrastructure Cost Allocation
Developed by: Mohamed A.Eltahir Elabbas - November 23, 2023

mabbas@comillas.edu
mohamed.a.eltahir@hotmail.com
https://www.iit.comillas.edu/people/mabbas

Instituto de Investigacion Tecnologica
Escuela Tecnica Superior de Ingenieria - ICAI
UNIVERSIDAD PONTIFICIA COMILLAS
C. de Sta. Cruz de Marcenado, 26
28015 Madrid, Spain
"""

from lib2to3.pgen2.pgen import NFAState
from xml.sax.saxutils import prepare_input_source
from matplotlib.collections import Collection
from collections import Counter
import pandas as pd
import numpy as np
import os
import sys
import warnings
import time
from typing import Tuple  # For Python 3.8
import argparse

warnings.filterwarnings("ignore")

#%% definitions
parser = argparse.ArgumentParser(description='Introducing main parameters...')
parser.add_argument('--case',   type=str, default=None)
parser.add_argument('--dir',    type=str, default=None)
parser.add_argument('--config', type=str, default=None)

DIR     = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))
CASE    = 'Examples\Simple_ex\Simple_Example'
CONFIGF = 'InfraFair control inputs'

# Thanks to http://patorjk.com/software/taag/
logo = r"""
$$$$$$\            $$$$$$\                      $$$$$$$$\           $$\           
\_$$  _|          $$  __$$\                     $$  _____|          \__|          
  $$ |  $$$$$$$\  $$ /  \__| $$$$$$\   $$$$$$\  $$ |       $$$$$$\  $$\  $$$$$$\  
  $$ |  $$  __$$\ $$$$\     $$  __$$\  \____$$\ $$$$$\     \____$$\ $$ |$$  __$$\ 
  $$ |  $$ |  $$ |$$  _|    $$ |  \__| $$$$$$$ |$$  __|    $$$$$$$ |$$ |$$ |  \__|
  $$ |  $$ |  $$ |$$ |      $$ |      $$  __$$ |$$ |      $$  __$$ |$$ |$$ |      
$$$$$$\ $$ |  $$ |$$ |      $$ |      \$$$$$$$ |$$ |      \$$$$$$$ |$$ |$$ |      
\______|\__|  \__|\__|      \__|       \_______|\__|       \_______|\__|\__|      
"""

#%% utility/auxiliary functions

def get_line_index(lines: pd.DataFrame, node1: int, node2: int) -> int:
    "This function return the index of the line, from the lines matrix, connecting two nodes"
    # Note: The assumption here is that there is no two lines with the same nodes, i.e., no double circuits

    line_name   = str(node1) + "-" + str(node2)
    temp        = lines[lines["Line"]  == line_name].index.values
    if not temp: # if it is empty
        line_name   = str(node2) + "-" + str(node1)
    
    return lines[lines["Line"]  == line_name].index.values[0]


def get_node_index(node: int, nodes_matrix: pd.DataFrame) -> int:
    "This function return the index of a node"

    return nodes_matrix[nodes_matrix["Node"] == node].index.values[0]


def get_total_nodal_flows(flows: np.ndarray, gen: np.ndarray, dem: np.ndarray) -> np.ndarray:
    "This function return a flow matrix with the generation and demand as inflows and outflows, respectively"

    nodal                   = dem - gen
    flows_node              = np.zeros(flows.shape)
    flows_node[:, :]        = flows[:, :]
    for i in range(len(flows_node)):
        flows_node[i, i]    = nodal[i, 0]
    
    return flows_node


def get_node_owner(node: int, nodes_matrix: pd.DataFrame, column: str) -> int:
    "This function return the country of a node"

    return nodes_matrix[column][nodes_matrix[nodes_matrix["Node"] == node].index.values[0]]


def get_line_SOs(Line_name:str, attribute_DF: pd.DataFrame, nodes_DF: pd.DataFrame, attribute_dict:dict) -> Tuple[str,str]:
    "This functions return the name of the SOs owning the line"

    node1, node2    = Line_name.split("-")
    node1, node2    =  int(node1), int(node2)
    SO1,  SO2       = "",""
    L_Type          = attribute_DF["Type"][attribute_DF[attribute_DF.index == Line_name].index.values[0]]
    
    if "Three-winding Transformer" in attribute_dict:
        if attribute_dict[L_Type] == "Three-winding Transformer":     # check if it is 3 winding transformer
            if isinstance(get_node_owner(node2, nodes_DF, "SO 2"),str):
                SO1 = get_node_owner(node2, nodes_DF, "SO 1")
                SO2 = get_node_owner(node2, nodes_DF, "SO 2")
            else:
                SO1 = get_node_owner(node1, nodes_DF, "SO 1")
                SO2 = get_node_owner(node1, nodes_DF, "SO 2")
    else:
        SO1 = get_node_owner(node1, nodes_DF, "SO 1")
        SO2 = get_node_owner(node2, nodes_DF, "SO 1")
    
    return SO1, SO2 
        

def extract_negative_demand(demand: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    "This function separates the negative demand (generation) from the normal demand"

    n_demand = np.zeros(demand.shape)
    for index in range(len(demand)):
        if demand[index] < 0:
            n_demand[index] = demand[index]

    p_demand = demand - n_demand
    
    return n_demand, p_demand


def get_flow_direction(line_matrix: pd.DataFrame, contribution_matrix)-> pd.DataFrame:
    "This function returns the contribution matrix with the direction of the flow as the direction of the input flow"

    flow_signs = np.sign(line_matrix["Flow"].to_numpy())[None]
    if isinstance(contribution_matrix, pd.DataFrame):
        matrix_with_direction = pd.DataFrame(index=contribution_matrix.index)
        for column in contribution_matrix.columns:
            matrix_with_direction[column] = (contribution_matrix[column].to_numpy()[None] * flow_signs).transpose()
    elif isinstance(contribution_matrix, np.ndarray):
        matrix_with_direction = contribution_matrix * flow_signs

    return matrix_with_direction


def get_negative_demand_contribution(negative_demand: np.ndarray, generation: np.ndarray, contribution_matrix: np.ndarray, 
                                    nodes_matrix: pd.DataFrame, lines_matrix: pd.DataFrame) -> pd.DataFrame:
    "This functions gives separate accounts to the contribution of the generation and the negative demand at the same node"

    indices_with_negative_demand                = np.nonzero((negative_demand < 0) * negative_demand)[0]
    indices_with_negative_demand_and_generation = np.nonzero(((negative_demand < 0) & (generation > 0)))[0]
    indices_with_negative_demand_only           = [i for i in indices_with_negative_demand if i not in indices_with_negative_demand_and_generation]
    indices_with_negative_demand_only_panda     = [1+i for i in indices_with_negative_demand if i not in indices_with_negative_demand_and_generation]

    ngd_contribution = pd.DataFrame(
        contribution_matrix[indices_with_negative_demand_only],
        index=nodes_matrix["Node"][indices_with_negative_demand_only_panda].astype(str)
        + "ND",
        columns=lines_matrix["Line"],
    )
    temp = pd.DataFrame(contribution_matrix[indices_with_negative_demand_and_generation], columns=lines_matrix["Line"],)
    for i in range(len(indices_with_negative_demand_and_generation)):
        node_index      = indices_with_negative_demand_and_generation[i]
        node            = nodes_matrix["Node"][node_index+1]

        ngd             = -negative_demand[node_index]
        g               = generation[node_index]
        sum             = ngd + g
        ngd_ratio       = ngd / sum
        g_ratio         = g / sum

        ngd_ser         = temp.xs(i) * ngd_ratio
        ngd_ser.name    = str(node) + "ND"
        g_ser           = temp.xs(i) * g_ratio
        g_ser.name      = str(node) + "G"

        ngd_contribution = ngd_contribution.append(ngd_ser)
        ngd_contribution = ngd_contribution.append(g_ser)

    return ngd_contribution


def get_aggregation_per_category(group_contribution_per_asset:pd.DataFrame, attributes_DF:pd.DataFrame) -> pd.DataFrame:
    "This function receive the contribution per asset and aggregate them according to asset type and voltage level"

    summation   = pd.DataFrame(index=group_contribution_per_asset.columns)
    asset_types = Counter(sorted(attributes_DF["Type"]))
    for a_type in asset_types:
        a_type_indices      = attributes_DF.index[attributes_DF["Type"] == a_type].tolist()
        selected_asset_type = attributes_DF.loc[a_type_indices,:]
        asset_voltages      = Counter(sorted(selected_asset_type["Voltage"], reverse=True))
        for a_voltage in asset_voltages:
            a_voltage_indices   = selected_asset_type.index[selected_asset_type["Voltage"] == a_voltage].tolist()
            summation[f'Asset Type:{a_type},Voltage:{a_voltage} kV'] = group_contribution_per_asset.loc[a_voltage_indices,:].sum().to_list()

    return summation


def get_utilization_per_category(flow_km_contribution:pd.DataFrame, flow_contribution:pd.DataFrame, flow_km_matrix:pd.DataFrame, flow_matrix:pd.DataFrame, attribute_dic:dict) -> pd.DataFrame:
    "This functions return the utilization of asset per category by using flow-Km for lines and flow for other assets"

    transmission_key            = [key for key, val in attribute_dic.items() if val == 'Transmission line']
    columns_to_drop1            = [col for col in flow_contribution.columns if col.startswith("Asset Type:"+str(transmission_key[0]))]
    columns_to_drop2            = [col for col in flow_km_contribution.columns if not col.startswith("Asset Type:"+str(transmission_key[0]))]
    flow_contribution_joint     = pd.concat([flow_km_contribution.drop(columns=columns_to_drop2), flow_contribution.drop(columns=columns_to_drop1)], axis=1)
    flow_rated_joint            = pd.concat([flow_km_matrix.drop(columns=columns_to_drop2), flow_matrix.drop(columns=columns_to_drop1)], axis=1)
    output                      = 100*flow_contribution_joint.to_numpy()/flow_rated_joint.to_numpy().transpose()[:,0]
    output[np.isnan(output)]    = 0
    output[np.isinf(output)]    = 0
    
    return  pd.DataFrame(output, index=flow_contribution_joint.index, columns=flow_contribution_joint.columns)
          

def remove_zero_rows_and_columns(data_frame:pd.DataFrame, rows:bool=True, columns:bool=True) -> pd.DataFrame:
    "This functions remove empty rows and/or columns from a DataFrame"

    df = data_frame.copy()# I would need to rename the index
    if rows:
        # Remove rows where all values are zero
        df = df.loc[(df != 0).any(axis=1)]
    if columns:
        # Remove columns where all values are zero
        df = df.loc[:, (df != 0).any(axis=0)]

    return df


def print_to_csv(name: str, matrix: np.ndarray, index: pd.Series, columns: pd.Series, total: bool = False, remove_zeros: bool = False):
    "This function exporting/printing the result of numpy array to a csv file"

    Data_frame = pd.DataFrame(matrix, index=index, columns=columns)
    if total:
        Data_frame                  = Data_frame.transpose()
        last_row                    = Data_frame.sum(axis=1)
        Data_frame["Total flow"]    = last_row
        Data_frame                  = Data_frame.transpose()
    if remove_zeros:
        # Remove rows where all values are zero
        Data_frame = Data_frame.loc[(Data_frame != 0).any(axis=1)]
        # Remove columns where all values are zero
        Data_frame = Data_frame.loc[:, (Data_frame != 0).any(axis=0)]
    
    Data_frame.to_csv("%s.csv" % name)


#%% primary functions

def get_input_matrices(lines_matrix: pd.DataFrame, nodes_matrix: pd.DataFrame, attribute_matrix: pd.DataFrame, attribute_dic:dict, SO_owner: bool = False, process_line_ownership: bool = False, reactance: bool = False) -> Tuple[np.ndarray, np.ndarray, list, np.ndarray, np.ndarray, np.ndarray, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    "This function prepares the basic input matrices from the excel file and also returns interconnections between countries and owners of the lines"

    gen                 = nodes_matrix["Generation"].to_numpy()[None].transpose()         # The generation matrix
    dem                 = nodes_matrix["Demand"].to_numpy()[None].transpose()               # The demand matrix
    phi                 = lines_matrix["Flow"].to_numpy()[None].transpose()                 # The flow matrix
    phi_positive        = np.absolute(phi)                                                  # Positive flow matrix
    interconnections_C  = pd.DataFrame(columns=["Line","Country 1", "Country 2", "Flow"])   # Interconnection matrix between countries
    interconnections_T  = pd.DataFrame(columns=["Line","SO 1", "SO 2", "Flow"])           # Interconnection matrix between SOs
    ownership           = pd.DataFrame(lines_matrix["Line"],index = lines_matrix.index)

    if reactance:
        react = lines_matrix["React"].to_numpy().tolist()  # The reactance matrix
    else:
        react = []

    flows_matrix                    = np.zeros((nodes_matrix.shape[0], nodes_matrix.shape[0]))  # Flow matrix that shows the inflows (negative) and outflows (positive) of each node
    ownership["Country 1"]          = ownership["Country 2"] = ""
    if process_line_ownership and SO_owner:
        ownership["SO Owner 1"]     = ownership["SO Owner 2"]      = ""
        ownership["SO 1 Ownership"] = ownership["SO 2 Ownership"]  = 0.0
    
    for index in lines_matrix.index:
        node1, node2 = lines_matrix["Line"][index].split("-")
        node1, node2 =  int(node1), int(node2)
        flows_matrix[get_node_index(node1, nodes_matrix) - 1, get_node_index(node2, nodes_matrix) - 1] = lines_matrix["Flow"][index]
        flows_matrix[get_node_index(node2, nodes_matrix) - 1, get_node_index(node1, nodes_matrix) - 1] = -lines_matrix["Flow"][index]

        # extracting interconnections and ownership
        country1                        = get_node_owner(node1, nodes_matrix, "Country")
        country2                        = get_node_owner(node2, nodes_matrix, "Country")
        ownership["Country 1"][index]   = country1
        ownership["Country 2"][index]   = country2
        if country1 != country2:
            interconnections_C = interconnections_C.append({"Line": lines_matrix["Line"][index], "Country 1": country1, "Country 2": country2, "Flow": lines_matrix["Flow"][index]}, ignore_index=True)
        if SO_owner:
            L_SO1, L_SO2           = get_line_SOs(lines_matrix["Line"][index],attribute_matrix, nodes_matrix,attribute_dic)
            if L_SO1 != L_SO2 and isinstance(L_SO2,str):
                interconnections_T = interconnections_T.append({"Line": lines_matrix["Line"][index], "SO 1": L_SO1, "SO 2": L_SO2, "Flow": lines_matrix["Flow"][index]}, ignore_index=True)
      
        if process_line_ownership and SO_owner:
            ownership["SO Owner 1"][index], ownership["SO Owner 2"][index] = L_SO1, L_SO2
            if not isinstance(L_SO2,str):  # fill in the empty SO
                ownership["SO Owner 2"][index]     = L_SO1
            if L_SO1 == L_SO2 or isinstance(L_SO2,float):
                ownership["SO 1 Ownership"][index] = 1
            else:
                ownership["SO 1 Ownership"][index] = 0.5
                ownership["SO 2 Ownership"][index] = 0.5
    
    interconnections_C  = interconnections_C.set_index(["Line"])
    interconnections_T  = interconnections_T.set_index(["Line"]) 
    

    return gen, dem, react, flows_matrix, phi, phi_positive, interconnections_C, interconnections_T, ownership


def get_pout_pg_matrices(lines_matrix: pd.DataFrame, nodes_matrix: pd.DataFrame, flows: np.ndarray, gen: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    "This function calculates the contribution of inflows to outflows"

    number_of_lines = int(lines_matrix.shape[0])
    pout            = np.zeros((number_of_lines, number_of_lines)).astype(float)
    pg              = np.zeros((number_of_lines, len(gen))).astype(float)

    sum_of_outflows_and_withdrawals = ((flows < 0) * flows).sum(1) * -1.0

    for index in lines_matrix.index:
        temp = lines_matrix["Line"][index].split("-")
        flow_on_the_line = 0.0

        if lines_matrix["Flow"][index] > 0:
            sending_node = int(temp[0])
            flow_on_the_line = lines_matrix["Flow"][index]
        else:
            sending_node = int(temp[1])
            flow_on_the_line = -lines_matrix["Flow"][index]

        sending_node_index                  = get_node_index(sending_node, nodes_matrix)
        sending_nodes_indices               = np.nonzero((flows[sending_node_index - 1, :] < 0) * flows[sending_node_index - 1, :])[0]
        sending_nodes_indices               += 1  # adding +1 because these are matrix indices, starts from 0, from flows to indices in nodes_matrix, starts from 1.
        sending_nodes_of_line_sending_node  = nodes_matrix["Node"][sending_nodes_indices].tolist()

        if sum_of_outflows_and_withdrawals[sending_node_index - 1] > 0:
            contribution = flow_on_the_line/ sum_of_outflows_and_withdrawals[sending_node_index - 1]
        else:
            contribution = 0.0

        for j in range(len(sending_nodes_of_line_sending_node)):
            if sending_node != sending_nodes_of_line_sending_node[j]:
                temp_index = get_line_index(lines_matrix, sending_nodes_of_line_sending_node[j], sending_node)
                pout[index - 1, temp_index - 1] = contribution

        if gen[sending_node_index - 1, 0] != 0:
            pg[index - 1, sending_node_index - 1] = contribution

    return pout, pg


def get_pin_pd_matrices(lines_matrix: pd.DataFrame, nodes_matrix: pd.DataFrame, flows: np.ndarray, dem: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    "This function calculates the contribution of outflows to inflows"

    number_of_lines = int(lines_matrix.shape[0])
    pin             = np.zeros((number_of_lines, number_of_lines)).astype(float)
    pd              = np.zeros((number_of_lines, len(dem))).astype(float)

    sum_of_inflows_and_injections = ((flows > 0) * flows).sum(1)

    for index in lines_matrix.index:
        temp                = lines_matrix["Line"][index].split("-")
        flow_on_the_line    = 0.0

        if lines_matrix["Flow"][index] < 0:
            receiving_node      = int(temp[0])
            flow_on_the_line    = -lines_matrix["Flow"][index]
        else:
            receiving_node      = int(temp[1])
            flow_on_the_line    = lines_matrix["Flow"][index]

        receiving_node_index                    = get_node_index(receiving_node, nodes_matrix)
        receiving_nodes_indices                 = np.nonzero((flows[receiving_node_index - 1, :] > 0) * flows[receiving_node_index - 1, :])[0]
        receiving_nodes_indices                 += 1
        receiving_nodes_of_line_receiving_node  = nodes_matrix["Node"][receiving_nodes_indices].tolist()

        if sum_of_inflows_and_injections[receiving_node_index - 1] > 0:
            contribution = flow_on_the_line/sum_of_inflows_and_injections[receiving_node_index - 1]
        else:
            contribution = 0.0

        for j in range(len(receiving_nodes_of_line_receiving_node)):
            if receiving_node != receiving_nodes_of_line_receiving_node[j]:
                temp_index                      = get_line_index(lines_matrix, receiving_node, receiving_nodes_of_line_receiving_node[j])
                pin[index - 1, temp_index - 1]  = contribution

        if dem[receiving_node_index - 1, 0] != 0:
            pd[index - 1, receiving_node_index - 1] = contribution

    return pin, pd


def get_contribution_per_asset(contribution_matrix: np.ndarray, nodes_matrix: pd.DataFrame, lines_matrix: pd.DataFrame, grouping: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    "This function aggregates the contribution of a group, countries, SOs or even zones"

    groups               = Counter(nodes_matrix[grouping])  # type: Collection.Counters
    groups_contribution  = pd.DataFrame(index = lines_matrix["Line"])
    group_node           = pd.DataFrame(nodes_matrix["Node"], index = nodes_matrix.index)
    for x in groups: # countries loop
        group_node[x]                       = 0.0
        group_nodes_indices                 = nodes_matrix.index[nodes_matrix[grouping] == x].tolist()
        group_node[x][group_nodes_indices]  = 1
        group_nodes_indices                 = [i - 1 for i in group_nodes_indices]
        groups_contribution[x]              = np.sum(np.array(contribution_matrix[group_nodes_indices]), 0)
    
    return groups_contribution, group_node


def get_contribution_per_group(contribution_by_group_matrix: pd.DataFrame, reactance: list, factor: float, Ownership_DF: pd.DataFrame, group_interconnections: pd.DataFrame, grouping: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    "This function calculates the contribution of each group, countries or SOs or even zones, per group"

    intermediate_matrix1    = pd.DataFrame(index=contribution_by_group_matrix.index)
    Line_country_owner      = pd.DataFrame(0.0, index=Ownership_DF.index, columns=contribution_by_group_matrix.columns)

    for group in contribution_by_group_matrix:
        if len(reactance) > 0:
            intermediate_matrix1[group] = (contribution_by_group_matrix[group] * reactance * factor)
        else:
            intermediate_matrix1[group] = contribution_by_group_matrix[group]

        country_line_indices                                        = Ownership_DF.index[Ownership_DF[grouping+" 1"] == group].tolist()
        Line_country_owner[group][country_line_indices]             = 1
        country_line_indices                                        = Ownership_DF.index[Ownership_DF[grouping+" 2"] == group].tolist()
        Line_country_owner[group][country_line_indices]             = 1
        Line_country_owner[group][group_interconnections.index]     *= 0.5  

    countries_responsibility_matrix                     = pd.DataFrame(np.matmul(intermediate_matrix1.to_numpy().transpose(),Line_country_owner.to_numpy()), index=contribution_by_group_matrix.columns, columns=contribution_by_group_matrix.columns)
    diagonal                                            = np.diag(countries_responsibility_matrix)
    use_of                                              = countries_responsibility_matrix.sum(axis=1) - diagonal
    use_by                                              = countries_responsibility_matrix.sum() - diagonal
    countries_responsibility_matrix["Use by others"]    = use_by
    countries_responsibility_matrix["Use of others"]    = use_of
    countries_responsibility_matrix["Net use"]          = use_by - use_of

    return countries_responsibility_matrix, Line_country_owner


#%% running the model function

def InfraFair_run(directory_file:str, case_file:str, config_file:str) -> float:
    "This is the main function to run the model"

    start_time = time.time()

    #%% read inputs
    # data inputs
    input_file                  = os.path.join(directory_file, case_file + '.xlsx')
    nodes_sn                    = pd.read_excel(input_file, sheet_name ="Network", index_col=0) 
    lines_sn                    = pd.read_excel(input_file, sheet_name ="Flows", index_col=0)
    lines_sn                    = lines_sn.groupby(["Line"]).sum()                              # removing double circuit lines
    lines_attributes            = pd.read_excel(input_file, sheet_name ="Assets attributes", index_col=0)
    lines_attributes            = lines_attributes.set_index(["Line"])
    lines_attributes.sort_index(inplace=True)                                                   # important in matrix multiplication, so that the order matches the lines matrix when later in the loop grouped by Line
    lines_sn.reset_index(inplace=True)
    lines_sn.index +=1

    # control inputs
    config_path                     = os.path.abspath(os.path.join(input_file, '..'))
    configuration_file              = os.path.join(config_path, config_file + '.xlsx')
    control_inputs                  = pd.read_excel(configuration_file, index_col=0) 
    control_inputs                  = control_inputs.set_index(["Inputs"])
    nodal_aggregation               = control_inputs.loc["Nodal Aggregation"][0]                                    # binary 0/1   
    demand_weight                   = control_inputs.loc["Demand Cost Responsibility (%)"][0]/100                   # percentage 0-100 
    generation_weight               = control_inputs.loc["Generation Cost Responsibility (%)"][0]/100               # percentage 0-100
    demand_socialized_weight        = control_inputs.loc["Demand Socialized Cost Responsibility (%)"][0]/100        # percentage 0-100 
    generation_socialized_weight    = control_inputs.loc["Generation Socialized Cost Responsibility (%)"][0]/100    # percentage 0-100  
    length_per_reactance            = control_inputs.loc["Length per Reactance (PU)"][0]                            # integer
    asset_types                     = control_inputs.loc["Asset Types"][0].split(",")                               # list
    n_snapshots                     = control_inputs.loc["Number of Snapshots"][0]                                  # integer
    snapshots_weights               = control_inputs.loc["Snapshots Weights"][0].split(",")                         # list with length equals n_snapshots
    voltage_threshold               = control_inputs.loc["Voltage Threshold (kV)"][0]                               # Float
    cost_assignment_op              = control_inputs.loc["Cost Allocation Option"][0]                               # integer equals 1 or 2 or 3 or 4                     
    utilization_threshold           = control_inputs.loc["Utilization Threshold (%)"][0]                            # percentage 0-100, only if cost_assignment_op equals 4 
    show_snapshot_results           = control_inputs.loc["Snapshots Results"][0]                                    # binary 0/1
    show_agent_results              = control_inputs.loc["Agent Results"][0]                                        # binary 0/1
    show_country_results            = control_inputs.loc["Country Results"][0]                                      # binary 0/1
    show_SO_results                 = control_inputs.loc["SO Results"][0]                                           # binary 0/1
    show_aggregated_results         = control_inputs.loc["Aggregated Results"][0]                                   # binary 0/1
    show_intermediary_results       = control_inputs.loc["Intermediary Results"][0]                                 # binary 0/1
    cost_of_unused_capacity_op      = control_inputs.loc["Cost of Unused Capacity"][0]                              # integer equals 0 or 1 or 2 or 3

    # initializing control variables
    remove_zero_values                      = False                                             # internal setting to input variable to remove the zero value from the results 
    usage_result    = fraction_result       = cost_result       = False
    ownership_processing                    = True
    SO_aggregation = category_aggregation   = asset_type_cost   = False
    asset_type_dic                          = {int(asset_types[i].split(":")[1]):asset_types[i].split(":")[0] for i in range(len(asset_types))} 
    snapshots_weights_dic                   = {int(snapshots_weights[i].split(":")[0]):int(snapshots_weights[i].split(":")[1]) for i in range(len(snapshots_weights))} 

    # checking control inputs
    if length_per_reactance == 0:
        length_per_reactance = 1        # It doesn't have an effect on the calculation in this case
    if cost_assignment_op == 1:
        cost_of_unused_capacity_op = 0  # don't calculate the socialized cost if the full cost is allocated
    
    # checking the optional provided attributes
    attributes_provided = lines_attributes.columns
    if "Length" in attributes_provided and show_intermediary_results:
        usage_result                 = True                      # for calculating the usage MW*Km
        line_length_matrix           = lines_attributes['Length'].to_numpy()[None].transpose()
    if "Capacity" in attributes_provided:
        fraction_result              = True                      # for calculating the fraction of asset used Flow[Mw]/rated capacity[MW] %
        line_capacity_matrix         = lines_attributes['Capacity'].to_numpy()[None].transpose()
    if "Cost" in attributes_provided:
        cost_result                  = True * fraction_result    # the fraction_result needs to be true to calculate the cost results
        if "Voltage" in attributes_provided and voltage_threshold > 0:                               # excluding the assets below the voltage threshold by making their costs zeros
            excluded_asset_indices                              = lines_attributes.index[lines_attributes["Voltage"] < voltage_threshold].tolist()
            lines_attributes["Cost"][excluded_asset_indices]    = 0
        line_cost_matrix             = lines_attributes['Cost'].to_numpy()[None].transpose()
    if "Type" in attributes_provided and "Voltage" in attributes_provided and show_aggregated_results:
        category_aggregation         = True
        if cost_result:
            cost_per_category        = get_aggregation_per_category(pd.DataFrame(data=lines_attributes["Cost"].to_numpy(), index=lines_attributes.index, columns=["Cost"]),lines_attributes)
        if fraction_result:
            flow_per_category        = get_aggregation_per_category(pd.DataFrame(data=lines_attributes["Capacity"].to_numpy(), index=lines_attributes.index, columns=["Flow"]),lines_attributes)
            if usage_result:
                flow_km_per_category = get_aggregation_per_category(pd.DataFrame(data=(lines_attributes["Capacity"].to_numpy()*lines_attributes['Length'].to_numpy()), index=lines_attributes.index, columns=["Flow"]),lines_attributes)
    if "Exist/Planned" in attributes_provided:
        asset_type_cost              = True
        existing_assets              = (lines_attributes["Exist/Planned"]== 'Exist').astype(int).to_numpy()
    if "SO 1" in nodes_sn.columns:
        SO_aggregation               = True
        if "SO Owner 1" in attributes_provided and "SO 1 Ownership" in attributes_provided and "SO Owner 2" in attributes_provided and "SO 2 Ownership" in attributes_provided:
            ownership_processing     = False
    
    show_SO_results = show_SO_results*SO_aggregation     # don't show SO results if it is not possible to aggregate results SO-wise

    # initializing outputs from the snapshot loop
    gen_agent_flow_contribution_per_asset_overall   = np.zeros((int(nodes_sn.shape[0]),lines_sn.shape[0]))
    dem_agent_flow_contribution_per_asset_overall   = np.zeros((int(nodes_sn.shape[0]),lines_sn.shape[0]))
    line_flow_overall                               = np.zeros((int(lines_sn.shape[0]),1))
    generation_overall                              = np.zeros((nodes_sn.shape[0],1))
    modified_generation_overall                     = np.zeros((nodes_sn.shape[0],1))
    positive_demand_overall                         = np.zeros((nodes_sn.shape[0],1))
    negative_demand_overall                         = np.zeros((nodes_sn.shape[0],1))

    #%% processing input data and basic results per snapshot
    for snapshot in range(1,n_snapshots+1):
        output_file         = "Scenario " + str(snapshot) +" results\\"
        output_file         = os.path.join(config_path, output_file)
        current_snapshot    = str(snapshot)

        if "Losses"+current_snapshot in lines_sn.columns:   # checking if losses are provided
            lines           = lines_sn[["Line","Flow sn"+current_snapshot,"Losses sn"+current_snapshot]].copy()
            lines           = lines.rename(columns={"Flow sn"+current_snapshot:"Flow","Losses sn"+current_snapshot: "Losses"})
        else:
            lines   = lines_sn[["Line","Flow sn"+current_snapshot]].copy()
            lines   = lines.rename(columns={"Flow sn"+current_snapshot:"Flow"})
        
        other_attributes    = [i for i in nodes_sn.columns if "Generation" not in i]
        other_attributes    = [i for i in other_attributes if "Demand" not in i]
        nodes               = nodes_sn[["Generation sn"+current_snapshot,"Demand sn"+current_snapshot] + other_attributes].copy()
        nodes               = nodes.rename(columns={"Generation sn"+current_snapshot:"Generation","Demand sn"+current_snapshot: "Demand"})

        # aggregating generation and demand of the same node, case 2
        if nodal_aggregation:
            indices_of_nodes_with_generation_and_demand = nodes.index[(nodes["Demand"] != 0) & (nodes["Generation"] != 0)].tolist()
            for i in range(len(indices_of_nodes_with_generation_and_demand)):
                aggregation = (
                    nodes.loc[indices_of_nodes_with_generation_and_demand[i], "Generation"]
                    - nodes.loc[indices_of_nodes_with_generation_and_demand[i], "Demand"]
                )
                if aggregation > 0:
                    nodes.loc[indices_of_nodes_with_generation_and_demand[i], "Generation"] = aggregation
                    nodes.loc[indices_of_nodes_with_generation_and_demand[i], "Demand"] = 0.0
                else:
                    nodes.loc[indices_of_nodes_with_generation_and_demand[i], "Generation"] = 0.0
                    nodes.loc[indices_of_nodes_with_generation_and_demand[i], "Demand"] = abs(aggregation)

        generation, demand, reactance, flows, phi, phiPositive, countries_interconnections, SOs_interconnections, Ownership_matrix = get_input_matrices(lines, nodes,lines_attributes,asset_type_dic,SO_aggregation, ownership_processing)
        negative_demand, positive_demand    = extract_negative_demand(demand)
        modified_generation                 = generation - negative_demand
        is_all_ND_zeros                     = np.all(negative_demand == 0)

        # fill in the ownership matrix if given in the attribute file
        Ownership_matrix                       = Ownership_matrix.set_index(["Line"]) 
        if not ownership_processing:    
            Ownership_matrix["SO Owner 1"]     = lines_attributes["SO Owner 1"] 
            Ownership_matrix["SO Owner 2"]     = lines_attributes["SO Owner 2"] 
            Ownership_matrix["SO 1 Ownership"] = lines_attributes["SO 1 Ownership"]
            Ownership_matrix["SO 2 Ownership"] = lines_attributes["SO 2 Ownership"]

        Pout, PG    = get_pout_pg_matrices(lines, nodes, get_total_nodal_flows(flows, modified_generation, np.zeros(modified_generation.shape)),modified_generation)
        Pin, PD     = get_pin_pd_matrices(lines, nodes, get_total_nodal_flows(flows, np.zeros(positive_demand.shape), positive_demand), positive_demand)

        AG = np.matmul(np.linalg.inv(np.identity(len(Pout)) - Pout), PG)
        AD = np.matmul(np.linalg.inv(np.identity(len(Pin)) - Pin), PD)
        
        # calculating the contribution of each agent to the flow of the lines
        # the assumption here is that each node has only one agent, there cannot be two demand agents and two generator agents in one node
        gen_agent_flow_contribution_per_asset           = (AG * modified_generation[:, 0]).transpose()
        dem_agent_flow_contribution_per_asset           = (AD * positive_demand[:, 0]).transpose()
        gen_agent_flow_contribution_per_asset_overall   += gen_agent_flow_contribution_per_asset*snapshots_weights_dic[snapshot]
        dem_agent_flow_contribution_per_asset_overall   += dem_agent_flow_contribution_per_asset*snapshots_weights_dic[snapshot]
        generation_overall                              += generation*snapshots_weights_dic[snapshot]
        modified_generation_overall                     += modified_generation*snapshots_weights_dic[snapshot]
        positive_demand_overall                         += positive_demand*snapshots_weights_dic[snapshot]
        negative_demand_overall                         += negative_demand*snapshots_weights_dic[snapshot]
        line_flow                                       = lines["Flow"].to_numpy()[None].transpose()
        line_flow                                       = np.absolute(line_flow)
        line_flow_overall                               += line_flow*snapshots_weights_dic[snapshot]

        # defining some matrices in advance
        x, country_nodes_matrix_G   = get_contribution_per_asset(gen_agent_flow_contribution_per_asset, nodes, lines, "Country")
        x, country_nodes_matrix_D   = get_contribution_per_asset(dem_agent_flow_contribution_per_asset, nodes, lines, "Country")
        x, countries_lines          = get_contribution_per_group(x, reactance, length_per_reactance, Ownership_matrix, countries_interconnections, "Country")
        if SO_aggregation:
            y, SO_nodes_matrix_G   = get_contribution_per_asset(gen_agent_flow_contribution_per_asset, nodes, lines, "SO 1")
            y, SO_nodes_matrix_D   = get_contribution_per_asset(dem_agent_flow_contribution_per_asset, nodes, lines, "SO 1")
            y,   SOs_lines         = get_contribution_per_group(y, reactance, length_per_reactance, Ownership_matrix, SOs_interconnections, "SO Owner")
    

        #%% calculating intermediary results per snapshot
        if show_snapshot_results:
            if not os.path.exists(output_file):
                os.makedirs(output_file)

            if not is_all_ND_zeros:
                negative_dem_agent_contribution_per_asset = get_negative_demand_contribution(negative_demand, generation, gen_agent_flow_contribution_per_asset, nodes, lines)
            
            if show_country_results:
                # calculating the contribution of each country to the flow of each line
                gen_country_flow_contribution_per_asset, country_nodes_matrix_G = get_contribution_per_asset(gen_agent_flow_contribution_per_asset, nodes, lines, "Country")
                dem_country_flow_contribution_per_asset, country_nodes_matrix_D = get_contribution_per_asset(dem_agent_flow_contribution_per_asset, nodes, lines, "Country")
                # another way to calculate contribution_by_countries_G is through matrix multiplication = np.matmul(gen_agent_contribution_per_asset.transpose(),country_nodes_matrix_G.drop(columns=['Node']).to_numpy())
                # but I decided to keep the function since I need the loop to calculate the nodal matrix anyway, so there is no efficiency gain from removing it. 
                if show_aggregated_results:
                    # calculating the contribution of each country to the flow in other countries
                    gen_country_flow_contribution_per_country, countries_lines  = get_contribution_per_group(gen_country_flow_contribution_per_asset, reactance, length_per_reactance, Ownership_matrix, countries_interconnections, "Country")
                    dem_country_flow_contribution_per_country, countries_lines  = get_contribution_per_group(dem_country_flow_contribution_per_asset, reactance, length_per_reactance, Ownership_matrix, countries_interconnections, "Country")    
                    if category_aggregation:
                        gen_country_flow_contribution_per_asset_category        = get_aggregation_per_category(gen_country_flow_contribution_per_asset, lines_attributes)
                        dem_country_flow_contribution_per_asset_category        = get_aggregation_per_category(dem_country_flow_contribution_per_asset, lines_attributes)
                      
            if show_SO_results:
                # calculating the contribution of each SO to the flow of each line
                gen_SO_flow_contribution_per_asset, SO_nodes_matrix_G = get_contribution_per_asset(gen_agent_flow_contribution_per_asset, nodes, lines, "SO 1")
                dem_SO_flow_contribution_per_asset, SO_nodes_matrix_D = get_contribution_per_asset(dem_agent_flow_contribution_per_asset, nodes, lines, "SO 1")
                if show_aggregated_results:
                    # calculating the contribution of each SO to the flow in other SOs
                    gen_SO_flow_contribution_per_SO,   SOs_lines     = get_contribution_per_group(gen_SO_flow_contribution_per_asset, reactance, length_per_reactance, Ownership_matrix, SOs_interconnections, "SO Owner")
                    dem_SO_flow_contribution_per_SO,   SOs_lines     = get_contribution_per_group(dem_SO_flow_contribution_per_asset, reactance, length_per_reactance, Ownership_matrix, SOs_interconnections, "SO Owner")
                    if category_aggregation:
                        gen_SO_flow_contribution_per_asset_category    = get_aggregation_per_category(gen_SO_flow_contribution_per_asset, lines_attributes)
                        dem_SO_flow_contribution_per_asset_category    = get_aggregation_per_category(dem_SO_flow_contribution_per_asset, lines_attributes)

            # here the order matters! because country_lines and SO_lines need to be calculated first
            if show_aggregated_results and show_agent_results:
                # calculating the contribution of each agent to the flow in each country
                gen_agent_flow_contribution_per_country   = np.matmul(gen_agent_flow_contribution_per_asset,countries_lines.to_numpy())
                dem_agent_flow_contribution_per_country   = np.matmul(dem_agent_flow_contribution_per_asset,countries_lines.to_numpy())
                if SO_aggregation:    
                    # calculating the contribution of each agent to the flow in each SO
                    gen_agent_flow_contribution_per_SO   = np.matmul(gen_agent_flow_contribution_per_asset,SOs_lines.to_numpy())
                    dem_agent_flow_contribution_per_SO   = np.matmul(dem_agent_flow_contribution_per_asset,SOs_lines.to_numpy())
                if category_aggregation:
                    gen_agent_flow_contribution_per_asset_category  = get_aggregation_per_category(pd.DataFrame(gen_agent_flow_contribution_per_asset.transpose(), index=lines["Line"], columns=nodes["Node"]), lines_attributes)
                    dem_agent_flow_contribution_per_asset_category  = get_aggregation_per_category(pd.DataFrame(dem_agent_flow_contribution_per_asset.transpose(), index=lines["Line"], columns=nodes["Node"]), lines_attributes)

            #%% usage results in terms of flow-km (MW*km)            
            if usage_result:
                gen_agent_flow_km_contribution_per_asset                    = gen_agent_flow_contribution_per_asset*line_length_matrix[:,0]
                dem_agent_flow_km_contribution_per_asset                    = dem_agent_flow_contribution_per_asset*line_length_matrix[:,0]
                if show_agent_results and show_aggregated_results:
                    gen_agent_flow_km_contribution_per_country              = np.matmul(gen_agent_flow_km_contribution_per_asset,countries_lines.to_numpy())
                    dem_agent_flow_km_contribution_per_country              = np.matmul(dem_agent_flow_km_contribution_per_asset,countries_lines.to_numpy())
                    if SO_aggregation:  
                        gen_agent_flow_km_contribution_per_SO               = np.matmul(gen_agent_flow_km_contribution_per_asset,SOs_lines.to_numpy())
                        dem_agent_flow_km_contribution_per_SO               = np.matmul(dem_agent_flow_km_contribution_per_asset,SOs_lines.to_numpy())
                    if category_aggregation:
                        gen_agent_flow_km_contribution_per_asset_category   = get_aggregation_per_category(pd.DataFrame(gen_agent_flow_km_contribution_per_asset.transpose(), index=lines["Line"], columns=nodes["Node"]), lines_attributes)
                        dem_agent_flow_km_contribution_per_asset_category   = get_aggregation_per_category(pd.DataFrame(dem_agent_flow_km_contribution_per_asset.transpose(), index=lines["Line"], columns=nodes["Node"]), lines_attributes)
                    
                if show_country_results:
                    gen_country_flow_km_contribution_per_asset, country_nodes_matrix_G  = get_contribution_per_asset(gen_agent_flow_km_contribution_per_asset, nodes, lines, "Country")
                    dem_country_flow_km_contribution_per_asset, country_nodes_matrix_D  = get_contribution_per_asset(dem_agent_flow_km_contribution_per_asset, nodes, lines, "Country")
                    if show_aggregated_results:
                        gen_country_flow_km_contribution_per_country, countries_lines   = get_contribution_per_group(gen_country_flow_km_contribution_per_asset, reactance, length_per_reactance, Ownership_matrix, countries_interconnections, "Country")
                        dem_country_flow_km_contribution_per_country, countries_lines   = get_contribution_per_group(dem_country_flow_km_contribution_per_asset, reactance, length_per_reactance, Ownership_matrix, countries_interconnections, "Country")
                        if category_aggregation:
                            gen_country_flow_km_contribution_per_asset_category         = get_aggregation_per_category(gen_country_flow_km_contribution_per_asset, lines_attributes)
                            dem_country_flow_km_contribution_per_asset_category         = get_aggregation_per_category(dem_country_flow_km_contribution_per_asset, lines_attributes)

                if show_SO_results:
                    gen_SO_flow_km_contribution_per_asset, SO_nodes_matrix_G  = get_contribution_per_asset(gen_agent_flow_km_contribution_per_asset, nodes, lines, "SO 1")
                    dem_SO_flow_km_contribution_per_asset, SO_nodes_matrix_D  = get_contribution_per_asset(dem_agent_flow_km_contribution_per_asset, nodes, lines, "SO 1") 
                    if show_aggregated_results:
                        gen_SO_flow_km_contribution_per_SO,   SOs_lines       = get_contribution_per_group(gen_SO_flow_km_contribution_per_asset, reactance, length_per_reactance, Ownership_matrix, SOs_interconnections, "SO Owner")
                        dem_SO_flow_km_contribution_per_SO,   SOs_lines       = get_contribution_per_group(dem_SO_flow_km_contribution_per_asset, reactance, length_per_reactance, Ownership_matrix, SOs_interconnections, "SO Owner")
                        if category_aggregation:
                            gen_SO_flow_km_contribution_per_asset_category    = get_aggregation_per_category(gen_SO_flow_km_contribution_per_asset, lines_attributes)
                            dem_SO_flow_km_contribution_per_asset_category    = get_aggregation_per_category(dem_SO_flow_km_contribution_per_asset, lines_attributes)
                        
            #%% utilization results
            if fraction_result:
                if cost_assignment_op == 1:     # utilization with respect to the used capacity
                    gen_agent_utilization_fraction_per_asset        = 100*gen_agent_flow_contribution_per_asset/line_flow[:,0]
                    dem_agent_utilization_fraction_per_asset        = 100*dem_agent_flow_contribution_per_asset/line_flow[:,0]
                else:   # utilization with respect to the rated capacity
                    gen_agent_utilization_fraction_per_asset        = 100*gen_agent_flow_contribution_per_asset/line_capacity_matrix[:,0]
                    dem_agent_utilization_fraction_per_asset        = 100*dem_agent_flow_contribution_per_asset/line_capacity_matrix[:,0]
                    if cost_assignment_op == 3 or cost_assignment_op == 4:  # utilization based on asset type and threshold 
                        gen_agent_utilization_fraction_per_asset2   = 100*gen_agent_flow_contribution_per_asset/line_flow[:,0]
                        dem_agent_utilization_fraction_per_asset2   = 100*dem_agent_flow_contribution_per_asset/line_flow[:,0]
                        # treatment
                        gen_agent_utilization_fraction_per_asset2[np.isnan(gen_agent_utilization_fraction_per_asset2)]  = 0
                        dem_agent_utilization_fraction_per_asset2[np.isnan(dem_agent_utilization_fraction_per_asset2)]  = 0
                        gen_agent_utilization_fraction_per_asset2[np.isinf(gen_agent_utilization_fraction_per_asset2)]  = 0
                        dem_agent_utilization_fraction_per_asset2[np.isinf(dem_agent_utilization_fraction_per_asset2)]  = 0
                        gen_agent_utilization_fraction_per_asset2                                                       = np.where(gen_agent_utilization_fraction_per_asset2 > 100, 100, gen_agent_utilization_fraction_per_asset2)
                        dem_agent_utilization_fraction_per_asset2                                                       = np.where(dem_agent_utilization_fraction_per_asset2 > 100, 100, dem_agent_utilization_fraction_per_asset2)     
                
                gen_agent_utilization_fraction_per_asset[np.isnan(gen_agent_utilization_fraction_per_asset)]    = 0
                dem_agent_utilization_fraction_per_asset[np.isnan(dem_agent_utilization_fraction_per_asset)]    = 0
                gen_agent_utilization_fraction_per_asset[np.isinf(gen_agent_utilization_fraction_per_asset)]    = 0
                dem_agent_utilization_fraction_per_asset[np.isinf(dem_agent_utilization_fraction_per_asset)]    = 0                

                # forcing elements that have more than 100% utilization back to 100%
                gen_agent_utilization_fraction_per_asset = np.where(gen_agent_utilization_fraction_per_asset > 100, 100, gen_agent_utilization_fraction_per_asset)
                dem_agent_utilization_fraction_per_asset = np.where(dem_agent_utilization_fraction_per_asset > 100, 100, dem_agent_utilization_fraction_per_asset)

                if show_intermediary_results:
                    if show_agent_results and show_aggregated_results and category_aggregation and usage_result:    # this is needed to for the lines since lines utilization is based on MW-km not just MW
                        gen_agent_utilization_fraction_per_asset_category   = get_utilization_per_category(gen_agent_flow_km_contribution_per_asset_category, gen_agent_flow_contribution_per_asset_category, flow_km_per_category, flow_per_category, asset_type_dic)                    
                        dem_agent_utilization_fraction_per_asset_category   = get_utilization_per_category(dem_agent_flow_km_contribution_per_asset_category, dem_agent_flow_contribution_per_asset_category, flow_km_per_category, flow_per_category, asset_type_dic)
   
                    if show_country_results:
                        gen_country_utilization_fraction_per_asset, country_nodes_matrix_G  = get_contribution_per_asset(gen_agent_utilization_fraction_per_asset, nodes, lines, "Country")
                        dem_country_utilization_fraction_per_asset, country_nodes_matrix_D  = get_contribution_per_asset(dem_agent_utilization_fraction_per_asset, nodes, lines, "Country")
                        if category_aggregation and usage_result and show_aggregated_results:
                            gen_country_utilization_fraction_per_asset_category             = get_utilization_per_category(gen_country_flow_km_contribution_per_asset_category, gen_country_flow_contribution_per_asset_category, flow_km_per_category, flow_per_category, asset_type_dic)
                            dem_country_utilization_fraction_per_asset_category             = get_utilization_per_category(dem_country_flow_km_contribution_per_asset_category, dem_country_flow_contribution_per_asset_category, flow_km_per_category, flow_per_category, asset_type_dic)
                    
                    if show_SO_results:
                        gen_SO_utilization_fraction_per_asset, SO_nodes_matrix_G  = get_contribution_per_asset(gen_agent_utilization_fraction_per_asset, nodes, lines, "SO 1")
                        dem_SO_utilization_fraction_per_asset, SO_nodes_matrix_D  = get_contribution_per_asset(dem_agent_utilization_fraction_per_asset, nodes, lines, "SO 1")
                        if category_aggregation and usage_result and show_aggregated_results:
                            gen_SO_utilization_fraction_per_asset_category        = get_utilization_per_category(gen_SO_flow_km_contribution_per_asset_category, gen_SO_flow_contribution_per_asset_category, flow_km_per_category, flow_per_category, asset_type_dic)
                            dem_SO_utilization_fraction_per_asset_category        = get_utilization_per_category(dem_SO_flow_km_contribution_per_asset_category, dem_SO_flow_contribution_per_asset_category, flow_km_per_category, flow_per_category, asset_type_dic)
                                
            #%% cost results kUS$
            if cost_result:
                if cost_assignment_op == 1 or cost_assignment_op == 2:    
                    gen_agent_cost_per_asset    = gen_agent_utilization_fraction_per_asset*line_cost_matrix[:,0]/100
                    dem_agent_cost_per_asset    = dem_agent_utilization_fraction_per_asset*line_cost_matrix[:,0]/100
                else:
                    if cost_assignment_op == 3: # full cost if the asset exist, used capacity cost if asset is planned
                        if asset_type_cost:
                            gen_agent_utilization_fraction_per_asset_partial    = np.matmul(gen_agent_utilization_fraction_per_asset,np.diag(1-existing_assets))    # cost of used capacity for planned assets
                            dem_agent_utilization_fraction_per_asset_partial    = np.matmul(dem_agent_utilization_fraction_per_asset,np.diag(1-existing_assets))
                            gen_agent_utilization_fraction_per_asset2           = np.matmul(gen_agent_utilization_fraction_per_asset2,np.diag(existing_assets))     # full cost for existing assets
                            dem_agent_utilization_fraction_per_asset2           = np.matmul(dem_agent_utilization_fraction_per_asset2,np.diag(existing_assets))
                        else:   # if the 'Exist/Planned' are not classified, use the cost of used capacity
                            gen_agent_utilization_fraction_per_asset_partial    = gen_agent_utilization_fraction_per_asset
                            dem_agent_utilization_fraction_per_asset_partial    = dem_agent_utilization_fraction_per_asset
                            gen_agent_utilization_fraction_per_asset2           = np.matmul(gen_agent_utilization_fraction_per_asset2,np.zeros((gen_agent_utilization_fraction_per_asset2.shape[1],gen_agent_utilization_fraction_per_asset2.shape[1])))    # making this matrix zero
                            dem_agent_utilization_fraction_per_asset2           = np.matmul(dem_agent_utilization_fraction_per_asset2,np.zeros((dem_agent_utilization_fraction_per_asset2.shape[1],dem_agent_utilization_fraction_per_asset2.shape[1])))

                    if cost_assignment_op == 4: # full cost if the asset is utilized above the threshold, otherwise, used capacity cost
                        # identifying assets above and below the utilization threshold (UT) separately
                        line_utilization    = np.squeeze(100*line_flow/line_capacity_matrix)
                        line_above_UT       = np.where(line_utilization>utilization_threshold,1,0)

                        gen_agent_utilization_fraction_per_asset_partial    = np.matmul(gen_agent_utilization_fraction_per_asset,np.diag(1-line_above_UT))    # cost of used capacity for assets below the UT
                        dem_agent_utilization_fraction_per_asset_partial    = np.matmul(dem_agent_utilization_fraction_per_asset,np.diag(1-line_above_UT))
                        gen_agent_utilization_fraction_per_asset2           = np.matmul(gen_agent_utilization_fraction_per_asset2,np.diag(line_above_UT))     # full cost for assets above the UT
                        dem_agent_utilization_fraction_per_asset2           = np.matmul(dem_agent_utilization_fraction_per_asset2,np.diag(line_above_UT))

                    gen_agent_cost_per_asset    = (gen_agent_utilization_fraction_per_asset_partial + gen_agent_utilization_fraction_per_asset2)*line_cost_matrix[:,0]/100
                    dem_agent_cost_per_asset    = (dem_agent_utilization_fraction_per_asset_partial + dem_agent_utilization_fraction_per_asset2)*line_cost_matrix[:,0]/100

                gen_agent_cost_per_asset = gen_agent_cost_per_asset*generation_weight
                dem_agent_cost_per_asset = dem_agent_cost_per_asset*demand_weight 
                
                if not is_all_ND_zeros:
                    negative_dem_agent_cost_per_asset       = get_negative_demand_contribution(negative_demand, generation, gen_agent_cost_per_asset, nodes, lines)

                if show_agent_results and show_aggregated_results:
                    gen_agent_cost_per_country              = np.matmul(gen_agent_cost_per_asset,countries_lines.to_numpy())
                    dem_agent_cost_per_country              = np.matmul(dem_agent_cost_per_asset,countries_lines.to_numpy())
                    gen_agent_total_cost                    = np.sum(gen_agent_cost_per_country, axis=1) 
                    dem_agent_total_cost                    = np.sum(dem_agent_cost_per_country, axis=1)
                    if SO_aggregation:
                        gen_agent_cost_per_SO               = np.matmul(gen_agent_cost_per_asset,SOs_lines.to_numpy())
                        dem_agent_cost_per_SO               = np.matmul(dem_agent_cost_per_asset,SOs_lines.to_numpy())
                    if category_aggregation:
                        gen_agent_cost_per_asset_category   = get_aggregation_per_category(pd.DataFrame(gen_agent_cost_per_asset.transpose(), index=lines["Line"], columns=nodes["Node"]), lines_attributes)
                        dem_agent_cost_per_asset_category   = get_aggregation_per_category(pd.DataFrame(dem_agent_cost_per_asset.transpose(), index=lines["Line"], columns=nodes["Node"]), lines_attributes)
                        # final cost-weighted utilization of the whole network
                        if usage_result:
                            gen_agent_network_utilization_fraction  = ((gen_agent_utilization_fraction_per_asset_category*cost_per_category.to_numpy().transpose()[:,0]).sum(axis=1)/cost_per_category.sum(axis=1)[0]).to_frame(name='Network Utilization %')              
                            dem_agent_network_utilization_fraction  = ((dem_agent_utilization_fraction_per_asset_category*cost_per_category.to_numpy().transpose()[:,0]).sum(axis=1)/cost_per_category.sum(axis=1)[0]).to_frame(name='Network Utilization %')
                            
                if show_country_results:
                    gen_country_cost_per_asset, country_nodes_matrix_G      = get_contribution_per_asset(gen_agent_cost_per_asset, nodes, lines, "Country")
                    dem_country_cost_per_asset, country_nodes_matrix_D      = get_contribution_per_asset(dem_agent_cost_per_asset, nodes, lines, "Country")
                    if show_aggregated_results:
                        gen_country_cost_per_country, countries_lines       = get_contribution_per_group(gen_country_cost_per_asset, reactance, length_per_reactance, Ownership_matrix, countries_interconnections, "Country")
                        dem_country_cost_per_country, countries_lines       = get_contribution_per_group(dem_country_cost_per_asset, reactance, length_per_reactance, Ownership_matrix, countries_interconnections, "Country")
                        if category_aggregation:
                            gen_country_cost_per_asset_category             = get_aggregation_per_category(gen_country_cost_per_asset, lines_attributes)
                            dem_country_cost_per_asset_category             = get_aggregation_per_category(dem_country_cost_per_asset, lines_attributes)
                            if usage_result:
                                gen_country_network_utilization_fraction    = ((gen_country_utilization_fraction_per_asset_category*cost_per_category.to_numpy().transpose()[:,0]).sum(axis=1)/cost_per_category.sum(axis=1)[0]).to_frame(name='Network Utilization %')
                                dem_country_network_utilization_fraction    = ((dem_country_utilization_fraction_per_asset_category*cost_per_category.to_numpy().transpose()[:,0]).sum(axis=1)/cost_per_category.sum(axis=1)[0]).to_frame(name='Network Utilization %')
                        
                if show_SO_results:
                    gen_SO_cost_per_asset, SO_nodes_matrix_G        = get_contribution_per_asset(gen_agent_cost_per_asset, nodes, lines, "SO 1")
                    dem_SO_cost_per_asset, SO_nodes_matrix_D        = get_contribution_per_asset(dem_agent_cost_per_asset, nodes, lines, "SO 1")
                    if show_aggregated_results:
                        gen_SO_cost_per_SO,   SOs_lines             = get_contribution_per_group(gen_SO_cost_per_asset, reactance, length_per_reactance, Ownership_matrix, SOs_interconnections, "SO Owner")
                        dem_SO_cost_per_SO,   SOs_lines             = get_contribution_per_group(dem_SO_cost_per_asset, reactance, length_per_reactance, Ownership_matrix, SOs_interconnections, "SO Owner")
                        if category_aggregation:
                            gen_SO_cost_per_asset_category          = get_aggregation_per_category(gen_SO_cost_per_asset, lines_attributes)
                            dem_SO_cost_per_asset_category          = get_aggregation_per_category(dem_SO_cost_per_asset, lines_attributes)
                            if usage_result:
                                gen_SO_network_utilization_fraction = ((gen_SO_utilization_fraction_per_asset_category*cost_per_category.to_numpy().transpose()[:,0]).sum(axis=1)/cost_per_category.sum(axis=1)[0]).to_frame(name='Network Utilization %')
                                dem_SO_network_utilization_fraction = ((dem_SO_utilization_fraction_per_asset_category*cost_per_category.to_numpy().transpose()[:,0]).sum(axis=1)/cost_per_category.sum(axis=1)[0]).to_frame(name='Network Utilization %')

                # calculating the socialized cost of the grid
                if cost_of_unused_capacity_op:        
                    gen_total_allocated_cost_per_asset          = gen_agent_cost_per_asset.sum(axis=0)[None].transpose()
                    dem_total_allocated_cost_per_asset          = dem_agent_cost_per_asset.sum(axis=0)[None].transpose()
                    total_cost_to_be_socialized                 = line_cost_matrix - gen_total_allocated_cost_per_asset - dem_total_allocated_cost_per_asset
                    gen_cost_to_socialize_per_asset             = total_cost_to_be_socialized*generation_socialized_weight
                    dem_cost_to_socialize_per_asset             = total_cost_to_be_socialized*demand_socialized_weight
                    gen_cost_to_socialize_per_asset             = np.where(gen_cost_to_socialize_per_asset < 0, 0, gen_cost_to_socialize_per_asset)
                    dem_cost_to_socialize_per_asset             = np.where(dem_cost_to_socialize_per_asset < 0, 0, dem_cost_to_socialize_per_asset)

                    if cost_of_unused_capacity_op == 1:     # socialize the cost equally among agents who use the asset
                        gen_agent_users_per_asset               = np.where(gen_agent_flow_contribution_per_asset > 0, 1, 0)    # identifying the agents using each line (no matter how small the flow, >0) by 1
                        dem_agent_users_per_asset               = np.where(dem_agent_flow_contribution_per_asset > 0, 1, 0)
                        gen_agent_users_average_per_asset       = gen_agent_users_per_asset.sum(axis=0)[None].transpose()
                        dem_agent_users_average_per_asset       = dem_agent_users_per_asset.sum(axis=0)[None].transpose()
                        gen_agent_socialized_weight_per_asset   = gen_agent_users_per_asset/gen_agent_users_average_per_asset[:,0]
                        dem_agent_socialized_weight_per_asset   = dem_agent_users_per_asset/dem_agent_users_average_per_asset[:,0]
                        
                        gen_agent_socialized_weight_per_asset[np.isnan(gen_agent_socialized_weight_per_asset)]  = 0
                        dem_agent_socialized_weight_per_asset[np.isnan(dem_agent_socialized_weight_per_asset)]  = 0
                        gen_agent_socialized_weight_per_asset[np.isinf(gen_agent_socialized_weight_per_asset)]  = 0
                        dem_agent_socialized_weight_per_asset[np.isinf(dem_agent_socialized_weight_per_asset)]  = 0  
                        
                        gen_agent_socialized_cost_per_asset = gen_agent_socialized_weight_per_asset*gen_cost_to_socialize_per_asset[:,0]
                        dem_agent_socialized_cost_per_asset = dem_agent_socialized_weight_per_asset*dem_cost_to_socialize_per_asset[:,0]

                    elif cost_of_unused_capacity_op == 2:  # socialize the cost equally among the agents belonging to the country(ise) that owns the asset
                        gen_agent_per_country       = country_nodes_matrix_G.set_index(["Node"]).to_numpy()
                        dem_agent_per_country       = country_nodes_matrix_D.set_index(["Node"]).to_numpy()
                        gen_agent_per_asset_country = np.matmul(gen_agent_per_country,countries_lines.to_numpy().transpose())
                        dem_agent_per_asset_country = np.matmul(dem_agent_per_country,countries_lines.to_numpy().transpose())
                        gen_agent_per_asset_country = np.where(gen_agent_per_asset_country> 0, 1, 0)
                        dem_agent_per_asset_country = np.where(dem_agent_per_asset_country> 0, 1, 0)
                        
                        gen_agent_socialized_weight_per_asset   = gen_agent_per_asset_country/gen_agent_per_asset_country.sum(axis=0)[None].transpose()[:,0]
                        dem_agent_socialized_weight_per_asset   = dem_agent_per_asset_country/dem_agent_per_asset_country.sum(axis=0)[None].transpose()[:,0]
                        
                        gen_agent_socialized_weight_per_asset[np.isnan(gen_agent_socialized_weight_per_asset)]  = 0
                        dem_agent_socialized_weight_per_asset[np.isnan(dem_agent_socialized_weight_per_asset)]  = 0
                        gen_agent_socialized_weight_per_asset[np.isinf(gen_agent_socialized_weight_per_asset)]  = 0
                        dem_agent_socialized_weight_per_asset[np.isinf(dem_agent_socialized_weight_per_asset)]  = 0  
                        
                        gen_agent_socialized_cost_per_asset = gen_agent_socialized_weight_per_asset*gen_cost_to_socialize_per_asset[:,0]
                        dem_agent_socialized_cost_per_asset = dem_agent_socialized_weight_per_asset*dem_cost_to_socialize_per_asset[:,0]

                    elif cost_of_unused_capacity_op == 3:  # socialize the cost equally among all agents
                        generation_agents                       = np.where(modified_generation > 0, 1, 0)
                        demand_agents                           = np.where(positive_demand > 0, 1, 0)
                        gen_agent_socialized_weight_per_asset   = generation_agents/generation_agents.sum(axis=0)[0]
                        dem_agent_socialized_weight_per_asset   = demand_agents/demand_agents.sum(axis=0)[0]
                        gen_agent_socialized_cost_per_asset     = gen_agent_socialized_weight_per_asset*gen_cost_to_socialize_per_asset[:,0]
                        dem_agent_socialized_cost_per_asset     = dem_agent_socialized_weight_per_asset*dem_cost_to_socialize_per_asset[:,0]

            #%% export results per snapshot
            # agent flow results
            if show_agent_results:
                print_to_csv(output_file+"Generation agents flow contribution per asset sn_"+current_snapshot, gen_agent_flow_contribution_per_asset, index=nodes["Node"], columns=lines["Line"], total=True, remove_zeros=remove_zero_values)
                print_to_csv(output_file+"Demand agents flow contribution per asset sn_"+current_snapshot, dem_agent_flow_contribution_per_asset, index=nodes["Node"], columns=lines["Line"],total=True, remove_zeros=remove_zero_values)
                if not is_all_ND_zeros:
                    remove_zero_rows_and_columns(negative_dem_agent_contribution_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"Negative demand agents flow contribution per asset sn_"+current_snapshot+".csv")
                if show_aggregated_results:
                    print_to_csv(output_file+"Generation agents flow contribution per country sn_"+current_snapshot, gen_agent_flow_contribution_per_country, index=nodes["Node"], columns=countries_lines.columns, total=False, remove_zeros=remove_zero_values)
                    print_to_csv(output_file+"Demand agents flow contribution per country sn_"+current_snapshot, dem_agent_flow_contribution_per_country, index=nodes["Node"], columns=countries_lines.columns, total=False, remove_zeros=remove_zero_values)
                    if SO_aggregation:  
                        print_to_csv(output_file+"Generation agents flow contribution per SO sn_"+current_snapshot, gen_agent_flow_contribution_per_SO, index=nodes["Node"], columns=SOs_lines.columns, total=False, remove_zeros=remove_zero_values)
                        print_to_csv(output_file+"Demand agents flow contribution per SO sn_"+current_snapshot, dem_agent_flow_contribution_per_SO, index=nodes["Node"], columns=SOs_lines.columns, total=False, remove_zeros=remove_zero_values)
                    if category_aggregation:
                        remove_zero_rows_and_columns(gen_agent_flow_contribution_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Generation agents flow contribution per asset category sn_"+current_snapshot+".csv")
                        remove_zero_rows_and_columns(dem_agent_flow_contribution_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Demand agents flow contribution per asset category sn_"+current_snapshot+".csv")
        
            # countries flow results
            if show_country_results:
                remove_zero_rows_and_columns(gen_country_flow_contribution_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation flow contribution per asset sn_"+current_snapshot+".csv")
                remove_zero_rows_and_columns(dem_country_flow_contribution_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand flow contribution per asset sn_"+current_snapshot+".csv")
                if show_aggregated_results:
                    remove_zero_rows_and_columns(gen_country_flow_contribution_per_country.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation flow contribution per country sn_"+current_snapshot+".csv")
                    remove_zero_rows_and_columns(dem_country_flow_contribution_per_country.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand flow contribution per country sn_"+current_snapshot+".csv")
                    if category_aggregation:
                        remove_zero_rows_and_columns(gen_country_flow_contribution_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation flow contribution per asset category sn_"+current_snapshot+".csv")
                        remove_zero_rows_and_columns(dem_country_flow_contribution_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand flow contribution per asset category sn_"+current_snapshot+".csv")

            # SOs flow results
            if show_SO_results:
                remove_zero_rows_and_columns(gen_SO_flow_contribution_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation flow contribution per asset sn_"+current_snapshot+".csv")
                remove_zero_rows_and_columns(dem_SO_flow_contribution_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand flow contribution per asset sn_"+current_snapshot+".csv")
                if show_aggregated_results:
                    remove_zero_rows_and_columns(gen_SO_flow_contribution_per_SO.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation flow contribution per SO sn_"+current_snapshot+".csv")
                    remove_zero_rows_and_columns(dem_SO_flow_contribution_per_SO.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand flow contribution per SO sn_"+current_snapshot+".csv")
                    if category_aggregation:
                        remove_zero_rows_and_columns(gen_SO_flow_contribution_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation flow contribution per asset category sn_"+current_snapshot+".csv")
                        remove_zero_rows_and_columns(dem_SO_flow_contribution_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand flow contribution per asset category sn_"+current_snapshot+".csv")
            
            # usage results
            if usage_result:
                if show_agent_results:
                    print_to_csv(output_file+"Generation agents flow-km contribution per asset sn_"+current_snapshot, gen_agent_flow_km_contribution_per_asset, index=nodes["Node"], columns=lines["Line"], total=True, remove_zeros=remove_zero_values)
                    print_to_csv(output_file+"Demand agents flow-km contribution per asset sn_"+current_snapshot, dem_agent_flow_km_contribution_per_asset, index=nodes["Node"], columns=lines["Line"], total=True, remove_zeros=remove_zero_values)
                    if show_aggregated_results:
                        print_to_csv(output_file+"Generation agents flow-km contribution per country sn_"+current_snapshot, gen_agent_flow_km_contribution_per_country, index=nodes["Node"], columns=countries_lines.columns, total=False, remove_zeros=remove_zero_values)
                        print_to_csv(output_file+"Demand agents flow-km contribution per country sn_"+current_snapshot, dem_agent_flow_km_contribution_per_country, index=nodes["Node"], columns=countries_lines.columns, total=False, remove_zeros=remove_zero_values)
                        if SO_aggregation: 
                            print_to_csv(output_file+"Generation agents flow-km contribution per SO sn_"+current_snapshot, gen_agent_flow_km_contribution_per_SO, index=nodes["Node"], columns=SOs_lines.columns, total=False, remove_zeros=remove_zero_values)
                            print_to_csv(output_file+"Demand agents flow-km contribution per SO sn_"+current_snapshot, dem_agent_flow_km_contribution_per_SO, index=nodes["Node"], columns=SOs_lines.columns, total=False, remove_zeros=remove_zero_values)
                        if category_aggregation:
                            remove_zero_rows_and_columns(gen_agent_flow_km_contribution_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Generation agents flow-km contribution per asset category sn_"+current_snapshot+".csv")
                            remove_zero_rows_and_columns(dem_agent_flow_km_contribution_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Demand agents flow-km contribution per asset category sn_"+current_snapshot+".csv")
                
                if show_country_results:
                    remove_zero_rows_and_columns(gen_country_flow_km_contribution_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation flow-km contribution per asset sn_"+current_snapshot+".csv")
                    remove_zero_rows_and_columns(dem_country_flow_km_contribution_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand flow-km contribution per asset sn_"+current_snapshot+".csv")
                    if show_aggregated_results:
                        remove_zero_rows_and_columns(gen_country_flow_km_contribution_per_country.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation flow-km contribution per country sn_"+current_snapshot+".csv")
                        remove_zero_rows_and_columns(dem_country_flow_km_contribution_per_country.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand flow-km contribution per country sn_"+current_snapshot+".csv")
                        if category_aggregation:
                            remove_zero_rows_and_columns(gen_country_flow_km_contribution_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation flow-km contribution per asset category sn_"+current_snapshot+".csv")
                            remove_zero_rows_and_columns(dem_country_flow_km_contribution_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand flow-km contribution per asset category sn_"+current_snapshot+".csv")

                if show_SO_results:
                    remove_zero_rows_and_columns(gen_SO_flow_km_contribution_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation flow-km contribution per asset sn_"+current_snapshot+".csv")
                    remove_zero_rows_and_columns(dem_SO_flow_km_contribution_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand flow-km contribution per asset sn_"+current_snapshot+".csv")
                    if show_aggregated_results:
                        remove_zero_rows_and_columns(gen_SO_flow_km_contribution_per_SO.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation flow-km contribution per SO sn_"+current_snapshot+".csv")
                        remove_zero_rows_and_columns(dem_SO_flow_km_contribution_per_SO.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand flow-km contribution per SO sn_"+current_snapshot+".csv")
                        if category_aggregation:
                            remove_zero_rows_and_columns(gen_SO_flow_km_contribution_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation flow-km contribution per asset category sn_"+current_snapshot+".csv")
                            remove_zero_rows_and_columns(dem_SO_flow_km_contribution_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand flow-km contribution per asset category sn_"+current_snapshot+".csv")
                    
            # utilization fraction results
            if fraction_result and show_intermediary_results:
                if show_agent_results:
                    print_to_csv(output_file+"Generation agents utilization fraction per asset sn_"+current_snapshot, gen_agent_utilization_fraction_per_asset, index=nodes["Node"], columns=lines["Line"], total=True, remove_zeros=remove_zero_values)
                    print_to_csv(output_file+"Demand agents utilization fraction per asset sn_"+current_snapshot, dem_agent_utilization_fraction_per_asset, index=nodes["Node"], columns=lines["Line"],total=True, remove_zeros=remove_zero_values)
                    if show_aggregated_results and category_aggregation and usage_result:
                        remove_zero_rows_and_columns(gen_agent_utilization_fraction_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Generation agents utilization fraction per asset category sn_"+current_snapshot+".csv")
                        remove_zero_rows_and_columns(dem_agent_utilization_fraction_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Demand agents utilization fraction per asset category sn_"+current_snapshot+".csv")

                if show_country_results:
                    remove_zero_rows_and_columns(gen_country_utilization_fraction_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation utilization fraction per asset sn_"+current_snapshot+".csv")
                    remove_zero_rows_and_columns(dem_country_utilization_fraction_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand utilization fraction per asset sn_"+current_snapshot+".csv")
                    if show_aggregated_results and category_aggregation and usage_result:
                        remove_zero_rows_and_columns(gen_country_utilization_fraction_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation utilization fraction per asset category sn_"+current_snapshot+".csv")
                        remove_zero_rows_and_columns(dem_country_utilization_fraction_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand utilization fraction per asset category sn_"+current_snapshot+".csv")              

                if show_SO_results:
                    remove_zero_rows_and_columns(gen_SO_utilization_fraction_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation utilization fraction per asset sn_"+current_snapshot+".csv")
                    remove_zero_rows_and_columns(dem_SO_utilization_fraction_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand utilization fraction per asset sn_"+current_snapshot+".csv")
                    if show_aggregated_results and category_aggregation and usage_result:
                        remove_zero_rows_and_columns(gen_SO_utilization_fraction_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation utilization fraction per asset category sn_"+current_snapshot+".csv")
                        remove_zero_rows_and_columns(dem_SO_utilization_fraction_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand utilization fraction per asset category sn_"+current_snapshot+".csv")

            # cost results
            if cost_result:
                if show_agent_results:
                    print_to_csv(output_file+"Generation agents cost per asset sn_"+current_snapshot, gen_agent_cost_per_asset, index=nodes["Node"], columns=lines["Line"], total=True, remove_zeros=remove_zero_values)
                    print_to_csv(output_file+"Demand agents cost per asset sn_"+current_snapshot, dem_agent_cost_per_asset, index=nodes["Node"], columns=lines["Line"],total=True, remove_zeros=remove_zero_values)
                    if not is_all_ND_zeros:
                        remove_zero_rows_and_columns(negative_dem_agent_cost_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"Negative demand agents cost per asset sn_"+current_snapshot+".csv")
                    if cost_of_unused_capacity_op:
                        print_to_csv(output_file+"Generation agents socialized cost per asset sn_"+current_snapshot, gen_agent_socialized_cost_per_asset, index=nodes["Node"], columns=lines["Line"], total=True, remove_zeros=remove_zero_values)
                        print_to_csv(output_file+"Demand agents socialized cost per asset sn_"+current_snapshot, dem_agent_socialized_cost_per_asset, index=nodes["Node"], columns=lines["Line"], total=True, remove_zeros=remove_zero_values)
                    if show_aggregated_results:
                        print_to_csv(output_file+"Generation agents cost per country sn_"+current_snapshot, gen_agent_cost_per_country, index=nodes["Node"], columns=countries_lines.columns, total=False, remove_zeros=remove_zero_values)
                        print_to_csv(output_file+"Demand agents cost per country sn_"+current_snapshot, dem_agent_cost_per_country, index=nodes["Node"], columns=countries_lines.columns, total=False, remove_zeros=remove_zero_values)
                        print_to_csv(output_file+"Generation agents total cost sn_"+current_snapshot, gen_agent_total_cost, index=nodes["Node"], columns=['Total cost KUS$'], total=True, remove_zeros=remove_zero_values)
                        print_to_csv(output_file+"Demand agents total cost sn_"+current_snapshot, dem_agent_total_cost, index=nodes["Node"], columns=['Total cost KUS$'], total=True, remove_zeros=remove_zero_values)
                        if SO_aggregation:  
                            print_to_csv(output_file+"Generation agents cost per SO sn_"+current_snapshot, gen_agent_cost_per_SO, index=nodes["Node"], columns=SOs_lines.columns, total=False, remove_zeros=remove_zero_values)
                            print_to_csv(output_file+"Demand agents cost per SO sn_"+current_snapshot, dem_agent_cost_per_SO, index=nodes["Node"], columns=SOs_lines.columns, total=False, remove_zeros=remove_zero_values)
                        if category_aggregation:
                            remove_zero_rows_and_columns(gen_agent_cost_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Generation agents cost per asset category sn_"+current_snapshot+".csv")
                            remove_zero_rows_and_columns(dem_agent_cost_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Demand agents cost per asset category sn_"+current_snapshot+".csv")
                            if usage_result:
                                remove_zero_rows_and_columns(gen_agent_network_utilization_fraction, remove_zero_values, remove_zero_values).to_csv(output_file+"Generation agents network utilization sn_"+current_snapshot+".csv")
                                remove_zero_rows_and_columns(dem_agent_network_utilization_fraction, remove_zero_values, remove_zero_values).to_csv(output_file+"Demand agents network utilization sn_"+current_snapshot+".csv")
                    
                if show_country_results:
                    remove_zero_rows_and_columns(gen_country_cost_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation cost per asset sn_"+current_snapshot+".csv")
                    remove_zero_rows_and_columns(dem_country_cost_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand cost per asset sn_"+current_snapshot+".csv")
                    if show_aggregated_results:
                        remove_zero_rows_and_columns(gen_country_cost_per_country.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation cost per country sn_"+current_snapshot+".csv")
                        remove_zero_rows_and_columns(dem_country_cost_per_country.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand cost per country sn_"+current_snapshot+".csv")
                        if category_aggregation:
                            remove_zero_rows_and_columns(gen_country_cost_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation cost per asset category sn_"+current_snapshot+".csv")
                            remove_zero_rows_and_columns(dem_country_cost_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand cost per asset category sn_"+current_snapshot+".csv")
                            if usage_result:
                                remove_zero_rows_and_columns(gen_country_network_utilization_fraction, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation network utilization sn_"+current_snapshot+".csv")
                                remove_zero_rows_and_columns(dem_country_network_utilization_fraction, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand network utilization sn_"+current_snapshot+".csv")

                if show_SO_results:
                    remove_zero_rows_and_columns(gen_SO_cost_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation cost per asset sn_"+current_snapshot+".csv")
                    remove_zero_rows_and_columns(dem_SO_cost_per_asset, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand cost per asset sn_"+current_snapshot+".csv")
                    if show_aggregated_results:
                        remove_zero_rows_and_columns(gen_SO_cost_per_SO.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation cost per SO sn_"+current_snapshot+".csv")
                        remove_zero_rows_and_columns(dem_SO_cost_per_SO.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand cost per SO sn_"+current_snapshot+".csv")
                        if category_aggregation:
                            remove_zero_rows_and_columns(gen_SO_cost_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation cost per asset category sn_"+current_snapshot+".csv")
                            remove_zero_rows_and_columns(dem_SO_cost_per_asset_category, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand cost per asset category sn_"+current_snapshot+".csv")
                            if usage_result:
                                remove_zero_rows_and_columns(gen_SO_network_utilization_fraction, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation network utilization sn_"+current_snapshot+".csv")
                                remove_zero_rows_and_columns(dem_SO_network_utilization_fraction, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand network utilization sn_"+current_snapshot+".csv")

    #%% overall results
    output_file         = "Overall results\\"
    output_file         = os.path.join(config_path, output_file)
    if not os.path.exists(output_file):
        os.makedirs(output_file)

    line_flow_overall                               = line_flow_overall/sum(snapshots_weights_dic.values())
    modified_generation_overall                     = modified_generation_overall/sum(snapshots_weights_dic.values())
    generation_overall                              = generation_overall/sum(snapshots_weights_dic.values())
    positive_demand_overall                         = positive_demand_overall/sum(snapshots_weights_dic.values())
    negative_demand_overall                         = negative_demand_overall/sum(snapshots_weights_dic.values())
    is_all_ND_zeros                                 = np.all(negative_demand_overall == 0)
    gen_agent_flow_contribution_per_asset_overall   = gen_agent_flow_contribution_per_asset_overall/sum(snapshots_weights_dic.values())
    dem_agent_flow_contribution_per_asset_overall   = dem_agent_flow_contribution_per_asset_overall/sum(snapshots_weights_dic.values())
    
    if not is_all_ND_zeros:
        negative_dem_agent_contribution_per_asset_overall   = get_negative_demand_contribution(negative_demand_overall, generation_overall, gen_agent_flow_contribution_per_asset_overall, nodes_sn, lines_sn)

    if show_country_results:
        gen_country_flow_contribution_per_asset_overall, country_nodes_matrix_G = get_contribution_per_asset(gen_agent_flow_contribution_per_asset_overall, nodes, lines, "Country")
        dem_country_flow_contribution_per_asset_overall, country_nodes_matrix_D = get_contribution_per_asset(dem_agent_flow_contribution_per_asset_overall, nodes, lines, "Country")
        if show_aggregated_results:
            gen_country_flow_contribution_per_country_overall, countries_lines  = get_contribution_per_group(gen_country_flow_contribution_per_asset_overall, reactance, length_per_reactance, Ownership_matrix, countries_interconnections, "Country")
            dem_country_flow_contribution_per_country_overall, countries_lines  = get_contribution_per_group(dem_country_flow_contribution_per_asset_overall, reactance, length_per_reactance, Ownership_matrix, countries_interconnections, "Country")
            if category_aggregation:
                gen_country_flow_contribution_per_asset_category_overall        = get_aggregation_per_category(gen_country_flow_contribution_per_asset_overall, lines_attributes)
                dem_country_flow_contribution_per_asset_category_overall        = get_aggregation_per_category(dem_country_flow_contribution_per_asset_overall, lines_attributes)
                
    if show_SO_results:
        gen_SO_flow_contribution_per_asset_overall, SO_nodes_matrix_G = get_contribution_per_asset(gen_agent_flow_contribution_per_asset_overall, nodes, lines, "SO 1")
        dem_SO_flow_contribution_per_asset_overall, SO_nodes_matrix_D = get_contribution_per_asset(dem_agent_flow_contribution_per_asset_overall, nodes, lines, "SO 1")
        if show_aggregated_results:
            gen_SO_flow_contribution_per_SO_overall,   SOs_lines      = get_contribution_per_group(gen_SO_flow_contribution_per_asset_overall, reactance, length_per_reactance, Ownership_matrix, SOs_interconnections, "SO Owner")
            dem_SO_flow_contribution_per_SO_overall,   SOs_lines      = get_contribution_per_group(dem_SO_flow_contribution_per_asset_overall, reactance, length_per_reactance, Ownership_matrix, SOs_interconnections, "SO Owner")
            if category_aggregation:
                gen_SO_flow_contribution_per_asset_category_overall   = get_aggregation_per_category(gen_SO_flow_contribution_per_asset_overall, lines_attributes)
                dem_SO_flow_contribution_per_asset_category_overall   = get_aggregation_per_category(dem_SO_flow_contribution_per_asset_overall, lines_attributes)
                
    if show_agent_results and show_aggregated_results:
        gen_agent_flow_contribution_per_country_overall             = np.matmul(gen_agent_flow_contribution_per_asset_overall,countries_lines.to_numpy())
        dem_agent_flow_contribution_per_country_overall             = np.matmul(dem_agent_flow_contribution_per_asset_overall,countries_lines.to_numpy())
        if SO_aggregation:  
            gen_agent_flow_contribution_per_SO_overall              = np.matmul(gen_agent_flow_contribution_per_asset_overall,SOs_lines.to_numpy())
            dem_agent_flow_contribution_per_SO_overall              = np.matmul(dem_agent_flow_contribution_per_asset_overall,SOs_lines.to_numpy())
        if category_aggregation:
            gen_agent_flow_contribution_per_asset_category_overall  = get_aggregation_per_category(pd.DataFrame(gen_agent_flow_contribution_per_asset_overall.transpose(), index=lines["Line"], columns=nodes["Node"]), lines_attributes)
            dem_agent_flow_contribution_per_asset_category_overall  = get_aggregation_per_category(pd.DataFrame(dem_agent_flow_contribution_per_asset_overall.transpose(), index=lines["Line"], columns=nodes["Node"]), lines_attributes)

    if fraction_result:
        if cost_assignment_op == 1:     # utilization with respect to the used capacity
            gen_agent_utilization_fraction_per_asset_overall        = 100*gen_agent_flow_contribution_per_asset_overall/line_flow_overall[:,0]
            dem_agent_utilization_fraction_per_asset_overall        = 100*dem_agent_flow_contribution_per_asset_overall/line_flow_overall[:,0]    
        else:   # utilization with respect to the rated capacity
            gen_agent_utilization_fraction_per_asset_overall        = 100*gen_agent_flow_contribution_per_asset_overall/line_capacity_matrix[:,0]
            dem_agent_utilization_fraction_per_asset_overall        = 100*dem_agent_flow_contribution_per_asset_overall/line_capacity_matrix[:,0]
            if cost_assignment_op == 3 or cost_assignment_op == 4:  # utilization based on asset type and threshold 
                gen_agent_utilization_fraction_per_asset2_overall   = 100*gen_agent_flow_contribution_per_asset_overall/line_flow_overall[:,0]
                dem_agent_utilization_fraction_per_asset2_overall   = 100*dem_agent_flow_contribution_per_asset_overall/line_flow_overall[:,0]
                # treatment
                gen_agent_utilization_fraction_per_asset2_overall[np.isnan(gen_agent_utilization_fraction_per_asset2_overall)]  = 0
                dem_agent_utilization_fraction_per_asset2_overall[np.isnan(dem_agent_utilization_fraction_per_asset2_overall)]  = 0
                gen_agent_utilization_fraction_per_asset2_overall[np.isinf(gen_agent_utilization_fraction_per_asset2_overall)]  = 0
                dem_agent_utilization_fraction_per_asset2_overall[np.isinf(dem_agent_utilization_fraction_per_asset2_overall)]  = 0
                gen_agent_utilization_fraction_per_asset2_overall                                                               = np.where(gen_agent_utilization_fraction_per_asset2_overall > 100, 100, gen_agent_utilization_fraction_per_asset2_overall)
                dem_agent_utilization_fraction_per_asset2_overall                                                               = np.where(dem_agent_utilization_fraction_per_asset2_overall > 100, 100, dem_agent_utilization_fraction_per_asset2_overall)     

        gen_agent_utilization_fraction_per_asset_overall[np.isnan(gen_agent_utilization_fraction_per_asset_overall)]    = 0
        dem_agent_utilization_fraction_per_asset_overall[np.isnan(dem_agent_utilization_fraction_per_asset_overall)]    = 0
        gen_agent_utilization_fraction_per_asset_overall[np.isinf(gen_agent_utilization_fraction_per_asset_overall)]    = 0
        dem_agent_utilization_fraction_per_asset_overall[np.isinf(dem_agent_utilization_fraction_per_asset_overall)]    = 0
        gen_agent_utilization_fraction_per_asset_overall                                                                = np.where(gen_agent_utilization_fraction_per_asset_overall > 100, 100, gen_agent_utilization_fraction_per_asset_overall)
        dem_agent_utilization_fraction_per_asset_overall                                                                = np.where(dem_agent_utilization_fraction_per_asset_overall > 100, 100, dem_agent_utilization_fraction_per_asset_overall)                
    
    if cost_result:
        if cost_assignment_op == 1 or cost_assignment_op == 2:    
            gen_agent_cost_per_asset_overall    = gen_agent_utilization_fraction_per_asset_overall*line_cost_matrix[:,0]/100
            dem_agent_cost_per_asset_overall    = dem_agent_utilization_fraction_per_asset_overall*line_cost_matrix[:,0]/100
        else:
            if cost_assignment_op == 3: # full cost if the asset exist, used capacity cost if asset is planned
                if asset_type_cost:
                    gen_agent_utilization_fraction_per_asset_overall_partial    = np.matmul(gen_agent_utilization_fraction_per_asset_overall,np.diag(1-existing_assets))    # cost of used capacity for planned assets
                    dem_agent_utilization_fraction_per_asset_overall_partial    = np.matmul(dem_agent_utilization_fraction_per_asset_overall,np.diag(1-existing_assets))
                    gen_agent_utilization_fraction_per_asset2_overall           = np.matmul(gen_agent_utilization_fraction_per_asset2_overall,np.diag(existing_assets))     # full cost for existing assets
                    dem_agent_utilization_fraction_per_asset2_overall           = np.matmul(dem_agent_utilization_fraction_per_asset2_overall,np.diag(existing_assets))
                else:   # if the 'Exist/Planned' are not classified, use the cost of used capacity
                    gen_agent_utilization_fraction_per_asset_overall_partial    = gen_agent_utilization_fraction_per_asset_overall
                    dem_agent_utilization_fraction_per_asset_overall_partial    = dem_agent_utilization_fraction_per_asset_overall
                    gen_agent_utilization_fraction_per_asset2_overall           = np.matmul(gen_agent_utilization_fraction_per_asset2_overall,np.zeros((gen_agent_utilization_fraction_per_asset2_overall.shape[1],gen_agent_utilization_fraction_per_asset2_overall.shape[1])))     # full cost for existing assets
                    dem_agent_utilization_fraction_per_asset2_overall           = np.matmul(dem_agent_utilization_fraction_per_asset2_overall,np.zeros((dem_agent_utilization_fraction_per_asset2_overall.shape[1],dem_agent_utilization_fraction_per_asset2_overall.shape[1])))

            if cost_assignment_op == 4: # full cost if the asset is utilized above the threshold, otherwise, used capacity cost
                # identifying assets above and below the utilization threshold (UT) separately
                line_utilization_overall    = np.squeeze(100*line_flow_overall/line_capacity_matrix)
                line_above_UT_overall       = np.where(line_utilization_overall>utilization_threshold,1,0)

                gen_agent_utilization_fraction_per_asset_overall_partial    = np.matmul(gen_agent_utilization_fraction_per_asset_overall,np.diag(1-line_above_UT_overall))    # cost of used capacity for assets below the UT
                dem_agent_utilization_fraction_per_asset_overall_partial    = np.matmul(dem_agent_utilization_fraction_per_asset_overall,np.diag(1-line_above_UT_overall))
                gen_agent_utilization_fraction_per_asset2_overall           = np.matmul(gen_agent_utilization_fraction_per_asset2_overall,np.diag(line_above_UT_overall))     # full cost for assets above the UT
                dem_agent_utilization_fraction_per_asset2_overall           = np.matmul(dem_agent_utilization_fraction_per_asset2_overall,np.diag(line_above_UT_overall))

            gen_agent_cost_per_asset_overall    = (gen_agent_utilization_fraction_per_asset_overall_partial + gen_agent_utilization_fraction_per_asset2_overall)*line_cost_matrix[:,0]/100
            dem_agent_cost_per_asset_overall    = (dem_agent_utilization_fraction_per_asset_overall_partial + dem_agent_utilization_fraction_per_asset2_overall)*line_cost_matrix[:,0]/100
        
        gen_agent_cost_per_asset_overall = gen_agent_cost_per_asset_overall*generation_weight
        dem_agent_cost_per_asset_overall = dem_agent_cost_per_asset_overall*demand_weight 
        
        if not is_all_ND_zeros:
            negative_dem_agent_cost_per_asset_overall = get_negative_demand_contribution(negative_demand_overall, generation_overall, gen_agent_cost_per_asset_overall, nodes_sn, lines_sn)

        # calculating the socialized cost of the grid
        if cost_of_unused_capacity_op:
     
            gen_total_allocated_cost_per_asset_overall  = gen_agent_cost_per_asset_overall.sum(axis=0)[None].transpose()
            dem_total_allocated_cost_per_asset_overall  = dem_agent_cost_per_asset_overall.sum(axis=0)[None].transpose()
            total_cost_to_be_socialized_overall         = line_cost_matrix - gen_total_allocated_cost_per_asset_overall - dem_total_allocated_cost_per_asset_overall
            gen_cost_to_socialize_per_asset_overall     = total_cost_to_be_socialized_overall*generation_socialized_weight
            dem_cost_to_socialize_per_asset_overall     = total_cost_to_be_socialized_overall*demand_socialized_weight
            gen_cost_to_socialize_per_asset_overall     = np.where(gen_cost_to_socialize_per_asset_overall < 0, 0, gen_cost_to_socialize_per_asset_overall)
            dem_cost_to_socialize_per_asset_overall     = np.where(dem_cost_to_socialize_per_asset_overall < 0, 0, dem_cost_to_socialize_per_asset_overall)

            if cost_of_unused_capacity_op == 1:     # socialize the cost equally among agents who use the asset
                gen_agent_users_per_asset_overall               = np.where(gen_agent_flow_contribution_per_asset_overall > 0, 1, 0)    # identifying the agents using each line (no matter how small the flow, >0) by 1
                dem_agent_users_per_asset_overall               = np.where(dem_agent_flow_contribution_per_asset_overall > 0, 1, 0)
                gen_agent_users_average_per_asset_overall       = gen_agent_users_per_asset_overall.sum(axis=0)[None].transpose()
                dem_agent_users_average_per_asset_overall       = dem_agent_users_per_asset_overall.sum(axis=0)[None].transpose()
                gen_agent_socialized_weight_per_asset_overall   = gen_agent_users_per_asset_overall/gen_agent_users_average_per_asset_overall[:,0]
                dem_agent_socialized_weight_per_asset_overall   = dem_agent_users_per_asset_overall/dem_agent_users_average_per_asset_overall[:,0]
                
                gen_agent_socialized_weight_per_asset_overall[np.isnan(gen_agent_socialized_weight_per_asset_overall)]  = 0
                dem_agent_socialized_weight_per_asset_overall[np.isnan(dem_agent_socialized_weight_per_asset_overall)]  = 0
                gen_agent_socialized_weight_per_asset_overall[np.isinf(gen_agent_socialized_weight_per_asset_overall)]  = 0
                dem_agent_socialized_weight_per_asset_overall[np.isinf(dem_agent_socialized_weight_per_asset_overall)]  = 0  
                
                gen_agent_socialized_cost_per_asset_overall = gen_agent_socialized_weight_per_asset_overall*gen_cost_to_socialize_per_asset_overall[:,0]
                dem_agent_socialized_cost_per_asset_overall = dem_agent_socialized_weight_per_asset_overall*dem_cost_to_socialize_per_asset_overall[:,0]

            elif cost_of_unused_capacity_op == 2:  # socialize the cost equally among the agents belonging to the country(ise) that owns the asset
                gen_agent_per_country       = country_nodes_matrix_G.set_index(["Node"]).to_numpy()
                dem_agent_per_country       = country_nodes_matrix_D.set_index(["Node"]).to_numpy()
                gen_agent_per_asset_country = np.matmul(gen_agent_per_country,countries_lines.to_numpy().transpose())
                dem_agent_per_asset_country = np.matmul(dem_agent_per_country,countries_lines.to_numpy().transpose())
                gen_agent_per_asset_country = np.where(gen_agent_per_asset_country > 0, 1, 0)
                dem_agent_per_asset_country = np.where(dem_agent_per_asset_country > 0, 1, 0)
                
                gen_agent_socialized_weight_per_asset_overall   = gen_agent_per_asset_country/gen_agent_per_asset_country.sum(axis=0)[None].transpose()[:,0]
                dem_agent_socialized_weight_per_asset_overall   = dem_agent_per_asset_country/dem_agent_per_asset_country.sum(axis=0)[None].transpose()[:,0]
                
                gen_agent_socialized_weight_per_asset_overall[np.isnan(gen_agent_socialized_weight_per_asset_overall)]  = 0
                dem_agent_socialized_weight_per_asset_overall[np.isnan(dem_agent_socialized_weight_per_asset_overall)]  = 0
                gen_agent_socialized_weight_per_asset_overall[np.isinf(gen_agent_socialized_weight_per_asset_overall)]  = 0
                dem_agent_socialized_weight_per_asset_overall[np.isinf(dem_agent_socialized_weight_per_asset_overall)]  = 0  
                
                gen_agent_socialized_cost_per_asset_overall = gen_agent_socialized_weight_per_asset_overall*gen_cost_to_socialize_per_asset_overall[:,0]
                dem_agent_socialized_cost_per_asset_overall = dem_agent_socialized_weight_per_asset_overall*dem_cost_to_socialize_per_asset_overall[:,0]

            elif cost_of_unused_capacity_op == 3:  # socialize the cost equally among all agents
                generation_agents_overall                       = np.where(modified_generation_overall > 0, 1, 0)
                demand_agents_overall                           = np.where(positive_demand_overall > 0, 1, 0)
                gen_agent_socialized_weight_per_asset_overall   = generation_agents_overall/generation_agents_overall.sum(axis=0)[0]
                dem_agent_socialized_weight_per_asset_overall   = demand_agents_overall/demand_agents_overall.sum(axis=0)[0]
                gen_agent_socialized_cost_per_asset_overall     = gen_agent_socialized_weight_per_asset_overall*gen_cost_to_socialize_per_asset_overall[:,0]
                dem_agent_socialized_cost_per_asset_overall     = dem_agent_socialized_weight_per_asset_overall*dem_cost_to_socialize_per_asset_overall[:,0]
    
        # the remaining cost results
        if show_country_results:
            gen_country_cost_per_asset_overall, country_nodes_matrix_G  = get_contribution_per_asset(gen_agent_cost_per_asset_overall, nodes, lines, "Country")
            dem_country_cost_per_asset_overall, country_nodes_matrix_D  = get_contribution_per_asset(dem_agent_cost_per_asset_overall, nodes, lines, "Country")
            if show_aggregated_results:
                gen_country_cost_per_country_overall, countries_lines   = get_contribution_per_group(gen_country_cost_per_asset_overall, reactance, length_per_reactance, Ownership_matrix, countries_interconnections, "Country")
                dem_country_cost_per_country_overall, countries_lines   = get_contribution_per_group(dem_country_cost_per_asset_overall, reactance, length_per_reactance, Ownership_matrix, countries_interconnections, "Country") 
                if category_aggregation:
                    gen_country_cost_per_asset_category_overall         = get_aggregation_per_category(gen_country_cost_per_asset_overall, lines_attributes)
                    dem_country_cost_per_asset_category_overall         = get_aggregation_per_category(dem_country_cost_per_asset_overall, lines_attributes)

        if show_SO_results:
            gen_SO_cost_per_asset_overall, SO_nodes_matrix_G           = get_contribution_per_asset(gen_agent_cost_per_asset_overall, nodes, lines, "SO 1")
            dem_SO_cost_per_asset_overall, SO_nodes_matrix_D           = get_contribution_per_asset(dem_agent_cost_per_asset_overall, nodes, lines, "SO 1")
            if show_aggregated_results:
                gen_SO_cost_per_SO_overall,   SOs_lines                = get_contribution_per_group(gen_SO_cost_per_asset_overall, reactance, length_per_reactance, Ownership_matrix, SOs_interconnections, "SO Owner")
                dem_SO_cost_per_SO_overall,   SOs_lines                = get_contribution_per_group(dem_SO_cost_per_asset_overall, reactance, length_per_reactance, Ownership_matrix, SOs_interconnections, "SO Owner")
                if category_aggregation:
                    gen_SO_cost_per_asset_category_overall             = get_aggregation_per_category(gen_SO_cost_per_asset_overall, lines_attributes)
                    dem_SO_cost_per_asset_category_overall             = get_aggregation_per_category(dem_SO_cost_per_asset_overall, lines_attributes)

        if show_agent_results and show_aggregated_results:
            gen_agent_cost_per_country_overall                          = np.matmul(gen_agent_cost_per_asset_overall,countries_lines.to_numpy())
            dem_agent_cost_per_country_overall                          = np.matmul(dem_agent_cost_per_asset_overall,countries_lines.to_numpy())
            gen_agent_total_cost_overall                                = np.sum(gen_agent_cost_per_country_overall, axis=1) 
            dem_agent_total_cost_overall                                = np.sum(dem_agent_cost_per_country_overall, axis=1)
            if SO_aggregation:  
                gen_agent_cost_per_SO_overall                           = np.matmul(gen_agent_cost_per_asset_overall,SOs_lines.to_numpy())
                dem_agent_cost_per_SO_overall                           = np.matmul(dem_agent_cost_per_asset_overall,SOs_lines.to_numpy())
            if category_aggregation:
                gen_agent_cost_per_asset_category_overall               = get_aggregation_per_category(pd.DataFrame(gen_agent_cost_per_asset_overall.transpose(), index=lines["Line"], columns=nodes["Node"]), lines_attributes)
                dem_agent_cost_per_asset_category_overall               = get_aggregation_per_category(pd.DataFrame(dem_agent_cost_per_asset_overall.transpose(), index=lines["Line"], columns=nodes["Node"]), lines_attributes)
         
    #%% overall intermediary results
    if show_intermediary_results:    
        if usage_result:
            gen_agent_flow_km_contribution_per_asset_overall                    = gen_agent_flow_contribution_per_asset_overall*line_length_matrix[:,0]
            dem_agent_flow_km_contribution_per_asset_overall                    = dem_agent_flow_contribution_per_asset_overall*line_length_matrix[:,0]
            if show_agent_results and show_aggregated_results:
                gen_agent_flow_km_contribution_per_country_overall              = np.matmul(gen_agent_flow_km_contribution_per_asset_overall,countries_lines.to_numpy())
                dem_agent_flow_km_contribution_per_country_overall              = np.matmul(dem_agent_flow_km_contribution_per_asset_overall,countries_lines.to_numpy())
                if SO_aggregation:  
                    gen_agent_flow_km_contribution_per_SO_overall               = np.matmul(gen_agent_flow_km_contribution_per_asset_overall,SOs_lines.to_numpy())
                    dem_agent_flow_km_contribution_per_SO_overall               = np.matmul(dem_agent_flow_km_contribution_per_asset_overall,SOs_lines.to_numpy())
                if category_aggregation:
                    gen_agent_flow_km_contribution_per_asset_category_overall   = get_aggregation_per_category(pd.DataFrame(gen_agent_flow_km_contribution_per_asset_overall.transpose(), index=lines["Line"], columns=nodes["Node"]), lines_attributes)
                    dem_agent_flow_km_contribution_per_asset_category_overall   = get_aggregation_per_category(pd.DataFrame(dem_agent_flow_km_contribution_per_asset_overall.transpose(), index=lines["Line"], columns=nodes["Node"]), lines_attributes)
            
            if show_country_results:
                gen_country_flow_km_contribution_per_asset_overall, country_nodes_matrix_G  = get_contribution_per_asset(gen_agent_flow_km_contribution_per_asset_overall, nodes, lines, "Country")
                dem_country_flow_km_contribution_per_asset_overall, country_nodes_matrix_D  = get_contribution_per_asset(dem_agent_flow_km_contribution_per_asset_overall, nodes, lines, "Country")
                if show_aggregated_results:
                    gen_country_flow_km_contribution_per_country_overall, countries_lines   = get_contribution_per_group(gen_country_flow_km_contribution_per_asset_overall, reactance, length_per_reactance, Ownership_matrix, countries_interconnections, "Country")
                    dem_country_flow_km_contribution_per_country_overall, countries_lines   = get_contribution_per_group(dem_country_flow_km_contribution_per_asset_overall, reactance, length_per_reactance, Ownership_matrix, countries_interconnections, "Country")
                    if category_aggregation:
                        gen_country_flow_km_contribution_per_asset_category_overall         = get_aggregation_per_category(gen_country_flow_km_contribution_per_asset_overall, lines_attributes)
                        dem_country_flow_km_contribution_per_asset_category_overall         = get_aggregation_per_category(dem_country_flow_km_contribution_per_asset_overall, lines_attributes)
            
            if show_SO_results:
                gen_SO_flow_km_contribution_per_asset_overall, SO_nodes_matrix_G = get_contribution_per_asset(gen_agent_flow_km_contribution_per_asset_overall, nodes, lines, "SO 1")
                dem_SO_flow_km_contribution_per_asset_overall, SO_nodes_matrix_D = get_contribution_per_asset(dem_agent_flow_km_contribution_per_asset_overall, nodes, lines, "SO 1")
                if show_aggregated_results:
                    gen_SO_flow_km_contribution_per_SO_overall,   SOs_lines      = get_contribution_per_group(gen_SO_flow_km_contribution_per_asset_overall, reactance, length_per_reactance, Ownership_matrix, SOs_interconnections, "SO Owner")
                    dem_SO_flow_km_contribution_per_SO_overall,   SOs_lines      = get_contribution_per_group(dem_SO_flow_km_contribution_per_asset_overall, reactance, length_per_reactance, Ownership_matrix, SOs_interconnections, "SO Owner")
                    if category_aggregation:
                        gen_SO_flow_km_contribution_per_asset_category_overall   = get_aggregation_per_category(gen_SO_flow_km_contribution_per_asset_overall, lines_attributes)
                        dem_SO_flow_km_contribution_per_asset_category_overall   = get_aggregation_per_category(dem_SO_flow_km_contribution_per_asset_overall, lines_attributes)

        if fraction_result:
            if show_agent_results and show_aggregated_results and category_aggregation and usage_result:
                gen_agent_utilization_fraction_per_asset_category_overall   = get_utilization_per_category(gen_agent_flow_km_contribution_per_asset_category_overall, gen_agent_flow_contribution_per_asset_category_overall, flow_km_per_category, flow_per_category, asset_type_dic)                    
                dem_agent_utilization_fraction_per_asset_category_overall   = get_utilization_per_category(dem_agent_flow_km_contribution_per_asset_category_overall, dem_agent_flow_contribution_per_asset_category_overall, flow_km_per_category, flow_per_category, asset_type_dic)
                if cost_result:
                    gen_agent_network_utilization_fraction_overall          = ((gen_agent_utilization_fraction_per_asset_category_overall*cost_per_category.to_numpy().transpose()[:,0]).sum(axis=1)/cost_per_category.sum(axis=1)[0]).to_frame(name='Network Utilization %')              
                    dem_agent_network_utilization_fraction_overall          = ((dem_agent_utilization_fraction_per_asset_category_overall*cost_per_category.to_numpy().transpose()[:,0]).sum(axis=1)/cost_per_category.sum(axis=1)[0]).to_frame(name='Network Utilization %')
            
            if show_country_results:
                gen_country_utilization_fraction_per_asset_overall, country_nodes_matrix_G  = get_contribution_per_asset(gen_agent_utilization_fraction_per_asset_overall, nodes, lines, "Country")
                dem_country_utilization_fraction_per_asset_overall, country_nodes_matrix_D  = get_contribution_per_asset(dem_agent_utilization_fraction_per_asset_overall, nodes, lines, "Country")
                if show_aggregated_results and category_aggregation and usage_result:
                    gen_country_utilization_fraction_per_asset_category_overall             = get_utilization_per_category(gen_country_flow_km_contribution_per_asset_category_overall, gen_country_flow_contribution_per_asset_category_overall, flow_km_per_category, flow_per_category, asset_type_dic)
                    dem_country_utilization_fraction_per_asset_category_overall             = get_utilization_per_category(dem_country_flow_km_contribution_per_asset_category_overall, dem_country_flow_contribution_per_asset_category_overall, flow_km_per_category, flow_per_category, asset_type_dic)        
                    if cost_result:
                        gen_country_network_utilization_fraction_overall                    = ((gen_country_utilization_fraction_per_asset_category_overall*cost_per_category.to_numpy().transpose()[:,0]).sum(axis=1)/cost_per_category.sum(axis=1)[0]).to_frame(name='Network Utilization %')
                        dem_country_network_utilization_fraction_overall                    = ((dem_country_utilization_fraction_per_asset_category_overall*cost_per_category.to_numpy().transpose()[:,0]).sum(axis=1)/cost_per_category.sum(axis=1)[0]).to_frame(name='Network Utilization %')

            if show_SO_results:
                gen_SO_utilization_fraction_per_asset_overall, SO_nodes_matrix_G   = get_contribution_per_asset(gen_agent_utilization_fraction_per_asset_overall, nodes, lines, "SO 1")
                dem_SO_utilization_fraction_per_asset_overall, SO_nodes_matrix_D   = get_contribution_per_asset(dem_agent_utilization_fraction_per_asset_overall, nodes, lines, "SO 1")
                if show_aggregated_results and category_aggregation and usage_result:
                    gen_SO_utilization_fraction_per_asset_category_overall         = get_utilization_per_category(gen_SO_flow_km_contribution_per_asset_category_overall, gen_SO_flow_contribution_per_asset_category_overall, flow_km_per_category, flow_per_category, asset_type_dic)
                    dem_SO_utilization_fraction_per_asset_category_overall         = get_utilization_per_category(dem_SO_flow_km_contribution_per_asset_category_overall, dem_SO_flow_contribution_per_asset_category_overall, flow_km_per_category, flow_per_category, asset_type_dic)
                    if cost_result:
                        gen_SO_network_utilization_fraction_overall                = ((gen_SO_utilization_fraction_per_asset_category_overall*cost_per_category.to_numpy().transpose()[:,0]).sum(axis=1)/cost_per_category.sum(axis=1)[0]).to_frame(name='Network Utilization %')
                        dem_SO_network_utilization_fraction_overall                = ((dem_SO_utilization_fraction_per_asset_category_overall*cost_per_category.to_numpy().transpose()[:,0]).sum(axis=1)/cost_per_category.sum(axis=1)[0]).to_frame(name='Network Utilization %')

    #%% exporting overall results
    if show_agent_results:
        print_to_csv(output_file+"Generation agents overall flow contribution per asset", gen_agent_flow_contribution_per_asset_overall, index=nodes["Node"], columns=lines["Line"], total=True, remove_zeros=remove_zero_values)
        print_to_csv(output_file+"Demand agents overall flow contribution per asset", dem_agent_flow_contribution_per_asset_overall, index=nodes["Node"], columns=lines["Line"],total=True, remove_zeros=remove_zero_values)
        if not np.all(negative_demand_overall == 0):
            remove_zero_rows_and_columns(negative_dem_agent_contribution_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Negative demand agents overall flow contribution per asset.csv")
        if show_aggregated_results:
            print_to_csv(output_file+"Generation agents overall flow contribution per country", gen_agent_flow_contribution_per_country_overall, index=nodes["Node"], columns=countries_lines.columns, total=False, remove_zeros=remove_zero_values)
            print_to_csv(output_file+"Demand agents overall flow contribution per country", dem_agent_flow_contribution_per_country_overall, index=nodes["Node"], columns=countries_lines.columns, total=False, remove_zeros=remove_zero_values)
            if SO_aggregation:
                print_to_csv(output_file+"Generation agents overall flow contribution per SO", gen_agent_flow_contribution_per_SO_overall, index=nodes["Node"], columns=SOs_lines.columns, total=False, remove_zeros=remove_zero_values)
                print_to_csv(output_file+"Demand agents overall flow contribution per SO", dem_agent_flow_contribution_per_SO_overall, index=nodes["Node"], columns=SOs_lines.columns, total=False, remove_zeros=remove_zero_values)
            if category_aggregation:
                remove_zero_rows_and_columns(gen_agent_flow_contribution_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Generation agents overall flow contribution per asset category.csv")
                remove_zero_rows_and_columns(dem_agent_flow_contribution_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Demand agents overall flow contribution per asset category.csv")
                
    if show_country_results:
        remove_zero_rows_and_columns(gen_country_flow_contribution_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation overall flow contribution per asset.csv")
        remove_zero_rows_and_columns(dem_country_flow_contribution_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand overall flow contribution per asset.csv")
        if show_aggregated_results:
            remove_zero_rows_and_columns(gen_country_flow_contribution_per_country_overall.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation overall flow contribution per country.csv")
            remove_zero_rows_and_columns(dem_country_flow_contribution_per_country_overall.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand overall flow contribution per country.csv")
            if category_aggregation:
                remove_zero_rows_and_columns(gen_country_flow_contribution_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation overall flow contribution per asset category.csv")
                remove_zero_rows_and_columns(dem_country_flow_contribution_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand overall flow contribution per asset category.csv")
                
    if show_SO_results:
        remove_zero_rows_and_columns(gen_SO_flow_contribution_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation overall flow contribution per asset.csv")
        remove_zero_rows_and_columns(dem_SO_flow_contribution_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand overall flow contribution per asset.csv")
        if show_aggregated_results:
            remove_zero_rows_and_columns(gen_SO_flow_contribution_per_SO_overall.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation overall flow contribution per SO.csv")
            remove_zero_rows_and_columns(dem_SO_flow_contribution_per_SO_overall.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand overall flow contribution per SO.csv")
            if category_aggregation:
                remove_zero_rows_and_columns(gen_SO_flow_contribution_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation overall flow contribution per asset category.csv")
                remove_zero_rows_and_columns(dem_SO_flow_contribution_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand overall flow contribution per asset category.csv")
                
    if cost_result:  
        if show_agent_results:
            print_to_csv(output_file+"Generation agents overall cost per asset", gen_agent_cost_per_asset_overall, index=nodes["Node"], columns=lines["Line"], total=True, remove_zeros=remove_zero_values)
            print_to_csv(output_file+"Demand agents overall cost per asset", dem_agent_cost_per_asset_overall, index=nodes["Node"], columns=lines["Line"],total=True, remove_zeros=remove_zero_values)
            if not is_all_ND_zeros:
                remove_zero_rows_and_columns(negative_dem_agent_cost_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Negative demand agents overall cost per asset.csv")
            if cost_of_unused_capacity_op:
                print_to_csv(output_file+"Generation agents socialized cost per asset", gen_agent_socialized_cost_per_asset_overall, index=nodes["Node"], columns=lines["Line"], total=True, remove_zeros=remove_zero_values)
                print_to_csv(output_file+"Demand agents socialized cost per asset", dem_agent_socialized_cost_per_asset_overall, index=nodes["Node"], columns=lines["Line"], total=True, remove_zeros=remove_zero_values)
            if show_aggregated_results:
                print_to_csv(output_file+"Generation agents overall cost per country", gen_agent_cost_per_country_overall, index=nodes["Node"], columns=countries_lines.columns, total=False, remove_zeros=remove_zero_values)
                print_to_csv(output_file+"Demand agents overall cost per country", dem_agent_cost_per_country_overall, index=nodes["Node"], columns=countries_lines.columns, total=False, remove_zeros=remove_zero_values)
                print_to_csv(output_file+"Generation agents overall total cost", gen_agent_total_cost_overall, index=nodes["Node"], columns=['Total cost KUS$'], total=True, remove_zeros=remove_zero_values)
                print_to_csv(output_file+"Demand agents overall total cost", dem_agent_total_cost_overall, index=nodes["Node"], columns=['Total cost KUS$'], total=True, remove_zeros=remove_zero_values)
                if SO_aggregation:
                    print_to_csv(output_file+"Generation agents overall cost per SO", gen_agent_cost_per_SO_overall, index=nodes["Node"], columns=SOs_lines.columns, total=False, remove_zeros=remove_zero_values)
                    print_to_csv(output_file+"Demand agents overall cost per SO", dem_agent_cost_per_SO_overall, index=nodes["Node"], columns=SOs_lines.columns, total=False, remove_zeros=remove_zero_values)
                if category_aggregation:
                    remove_zero_rows_and_columns(gen_agent_cost_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Generation agents overall cost per asset category.csv")
                    remove_zero_rows_and_columns(dem_agent_cost_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Demand agents overall cost per asset category.csv")

        if show_country_results:
            remove_zero_rows_and_columns(gen_country_cost_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation overall cost per asset"+".csv")
            remove_zero_rows_and_columns(dem_country_cost_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand overall cost per asset"+".csv")
            if show_aggregated_results:
                remove_zero_rows_and_columns(gen_country_cost_per_country_overall.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation overall cost per country.csv")
                remove_zero_rows_and_columns(dem_country_cost_per_country_overall.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand overall cost per country.csv")
                if category_aggregation:
                    remove_zero_rows_and_columns(gen_country_cost_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation overall cost per asset category.csv")
                    remove_zero_rows_and_columns(dem_country_cost_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand overall cost per asset category.csv")

        if show_SO_results:
            remove_zero_rows_and_columns(gen_SO_cost_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation overall cost per asset.csv")
            remove_zero_rows_and_columns(dem_SO_cost_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand overall cost per asset.csv")    
            if show_aggregated_results:
                remove_zero_rows_and_columns(gen_SO_cost_per_SO_overall.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation overall cost per SO.csv")
                remove_zero_rows_and_columns(dem_SO_cost_per_SO_overall.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand overall cost per SO.csv")
                if category_aggregation:
                    remove_zero_rows_and_columns(gen_SO_cost_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation overall cost per asset category.csv")
                    remove_zero_rows_and_columns(dem_SO_cost_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand overall cost per asset category.csv")
    
    # other intermediary results
    if show_intermediary_results:
        if fraction_result:
            if show_agent_results:
                print_to_csv(output_file+"Generation agents overall utilization fraction per asset", gen_agent_utilization_fraction_per_asset_overall, index=nodes["Node"], columns=lines["Line"], total=True, remove_zeros=remove_zero_values)
                print_to_csv(output_file+"Demand agents overall utilization fraction per asset", dem_agent_utilization_fraction_per_asset_overall, index=nodes["Node"], columns=lines["Line"],total=True, remove_zeros=remove_zero_values)
                if show_aggregated_results and category_aggregation and usage_result:
                    remove_zero_rows_and_columns(gen_agent_utilization_fraction_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Generation agents overall utilization fraction per asset category.csv")
                    remove_zero_rows_and_columns(dem_agent_utilization_fraction_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Demand agents overall utilization fraction per asset category.csv")
                    if cost_result:
                        remove_zero_rows_and_columns(gen_agent_network_utilization_fraction_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Generation agents overall network utilization.csv")
                        remove_zero_rows_and_columns(dem_agent_network_utilization_fraction_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Demand agents overall network utilization.csv")

            if show_country_results:
                remove_zero_rows_and_columns(gen_country_utilization_fraction_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation overall utilization fraction per asset.csv")
                remove_zero_rows_and_columns(dem_country_utilization_fraction_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand overall utilization fraction per asset.csv")
                if show_aggregated_results and category_aggregation and usage_result:
                    remove_zero_rows_and_columns(gen_country_utilization_fraction_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation overall utilization fraction per asset category.csv")
                    remove_zero_rows_and_columns(dem_country_utilization_fraction_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand overall utilization fraction per asset category.csv")
                    if cost_result:
                        remove_zero_rows_and_columns(gen_country_network_utilization_fraction_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation overall network utilization.csv")
                        remove_zero_rows_and_columns(dem_country_network_utilization_fraction_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand overall network utilization.csv")
                    
            if show_SO_results:
                remove_zero_rows_and_columns(gen_SO_utilization_fraction_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation overall utilization fraction per asset.csv")
                remove_zero_rows_and_columns(dem_SO_utilization_fraction_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand utilization overall fraction per asset.csv")              
                if show_aggregated_results and category_aggregation and usage_result:
                    remove_zero_rows_and_columns(gen_SO_utilization_fraction_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation overall utilization fraction per asset category.csv")
                    remove_zero_rows_and_columns(dem_SO_utilization_fraction_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand overall utilization fraction per asset category.csv")
                    if cost_result:
                        remove_zero_rows_and_columns(gen_SO_network_utilization_fraction_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation overall network utilization.csv")
                        remove_zero_rows_and_columns(dem_SO_network_utilization_fraction_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand overall network utilization.csv")
                    
        if usage_result:
            if show_agent_results:
                print_to_csv(output_file+"Generation agents overall flow-km contribution per asset", gen_agent_flow_km_contribution_per_asset_overall, index=nodes["Node"], columns=lines["Line"], total=True, remove_zeros=remove_zero_values)
                print_to_csv(output_file+"Demand agents overall flow-km contribution per asset", dem_agent_flow_km_contribution_per_asset_overall, index=nodes["Node"], columns=lines["Line"],total=True, remove_zeros=remove_zero_values)
                if show_aggregated_results:
                    print_to_csv(output_file+"Generation agents overall flow-km contribution per country", gen_agent_flow_km_contribution_per_country_overall, index=nodes["Node"], columns=countries_lines.columns, total=False, remove_zeros=remove_zero_values)
                    print_to_csv(output_file+"Demand agents overall flow-km contribution per country", dem_agent_flow_km_contribution_per_country_overall, index=nodes["Node"], columns=countries_lines.columns, total=False, remove_zeros=remove_zero_values)
                    if SO_aggregation:
                        print_to_csv(output_file+"Generation agents overall flow-km contribution per SO", gen_agent_flow_km_contribution_per_SO_overall, index=nodes["Node"], columns=SOs_lines.columns, total=False, remove_zeros=remove_zero_values)
                        print_to_csv(output_file+"Demand agents overall flow-km contribution per SO", dem_agent_flow_km_contribution_per_SO_overall, index=nodes["Node"], columns=SOs_lines.columns, total=False, remove_zeros=remove_zero_values)    
                    if category_aggregation:
                        remove_zero_rows_and_columns(gen_agent_flow_km_contribution_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Generation agents overall flow-km contribution per asset category.csv")
                        remove_zero_rows_and_columns(dem_agent_flow_km_contribution_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Demand agents overall flow-km contribution per asset category.csv")

            if show_country_results:
                remove_zero_rows_and_columns(gen_country_flow_km_contribution_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation overall flow-km contribution per asset.csv")
                remove_zero_rows_and_columns(dem_country_flow_km_contribution_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand overall flow-km contribution per asset.csv")
                if show_aggregated_results:
                    remove_zero_rows_and_columns(gen_country_flow_km_contribution_per_country_overall.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation overall flow-km contribution per country.csv")
                    remove_zero_rows_and_columns(dem_country_flow_km_contribution_per_country_overall.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand overall flow-km contribution per country.csv")
                    if category_aggregation:
                        remove_zero_rows_and_columns(gen_country_flow_km_contribution_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country generation overall flow-km contribution per asset category.csv")
                        remove_zero_rows_and_columns(dem_country_flow_km_contribution_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"Country demand overall flow-km contribution per asset category.csv")
            
            if show_SO_results:
                remove_zero_rows_and_columns(gen_SO_flow_km_contribution_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation overall flow-km contribution per asset.csv")
                remove_zero_rows_and_columns(dem_SO_flow_km_contribution_per_asset_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand overall flow-km contribution per asset.csv")
                if show_aggregated_results:
                    remove_zero_rows_and_columns(gen_SO_flow_km_contribution_per_SO_overall.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation overall flow-km contribution per SO.csv")
                    remove_zero_rows_and_columns(dem_SO_flow_km_contribution_per_SO_overall.transpose(), remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand overall flow-km contribution per SO.csv")
                    if category_aggregation:
                        remove_zero_rows_and_columns(gen_SO_flow_km_contribution_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO generation overall flow-km contribution per asset category.csv")
                        remove_zero_rows_and_columns(dem_SO_flow_km_contribution_per_asset_category_overall, remove_zero_values, remove_zero_values).to_csv(output_file+"SO demand overall flow-km contribution per asset category.csv")
            
    #%% End!
    return (time.time() - start_time)


#%% default main function

def main():
    "This is the main function for reading inputs from the user and running the model"
    
    args = parser.parse_args()
    if args.dir is None:
        args.dir    = input('Input Dir    Name (Default {}): '.format(DIR))
        if args.dir == '':
            args.dir = DIR
    if args.case is None:
        args.case   = input('Input Case   Name (Default {}): '.format(CASE))
        if args.case == '':
            args.case = CASE
    if args.config is None:
        args.config = input('Input configuration file Name (Default {}): '.format(CONFIGF))
        if args.config == '':
            args.config = CONFIGF

    print('\n*************************************!RUNNING!*************************************')
    print(logo)
    execution_time = InfraFair_run(args.dir, args.case, args.config)
    print("*****************************!EXECUTION TIME %s!*****************************" % time.strftime('%H:%M:%S', time.gmtime(execution_time)))
    print('\n**************************!COST HAS BEEN FAIRLY ALLOCATED!*************************')

if __name__ == '__main__':
    main()