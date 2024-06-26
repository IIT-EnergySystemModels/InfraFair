.. InfraFair documentation master file, created by Mohamed A.Eltahir Elabbas

##########################################
 Introduction
##########################################

Description
===========

The **InfraFair** is a modelling tool aimed at computing the allocation of the cost of energy infrastructure according 
to the economic use expected to be made by agents, driving efficient investment decisions. The modelling tool 
employs the **Average Participations Method (APM)** (see :doc:`6_Mathematical_Formulation`) that allocates the 
cost based on the electrical usage that each agent makes of each infrastructure asset as a reasonable proxy 
to the benefits, the former obtained from the latter. The basic intuition behind the APM is that 
energy consumed by demands and produced by generators, as well as the responsibility for causing energy 
flows, can be assigned by employing a **simple heuristic rule** that only uses the actual pattern of flows in 
the infrastructure network.

The rule assumes that energy flows can be traced by supposing that at any network node, the inflows are distributed proportionally among the outflows. This is the so-called **proportionality rule**. Implicit in this rule is the assumption that energy does not flow in the opposite direction to that of the prevalent (net) flow over each asset, which, according to this assumption, is the only existing flow. Based on these assumptions, the method traces the flow of energy from individual sources to individual sinks in all the network assets.


Scope
=====

InfraFair determines the network utilisation of agents, system operators and countries. 
Based on this utilisation and assuming that it reflects the economic benefits received by agents, 
it determines the responsibility of each agent in the construction of each element in the network. 
Additionally, it can also attribute losses on the assets to their responsible agents.
In order to reasonably reflect agent utilisation of infrastructure, multiple representative snapshots 
of annual network usage should be provided. InfraFair presents a decision support tool for tariff 
design for regional power transmission infrastructure, but it can be used for national infrastructure 
as well as other types of infrastructures operating on the same principle of flow (*flow-based infrastructure*), 
such as gas and hydrogen infrastructure. 
All assets that have a flow usage can be represented in the network model. For instance, the electrical network can include
power lines, transformers, breaks, series capacitors and phase shifting transformers.


Functionality
=============
Inputs to the model must consist of the **map of flows** in each of the assets as well as the **injections and withdrawals** of energy at each node. Additionally, the **rating capacity and the capital cost** of each asset must be provided for the model to be able to allocate costs to network users. Other information, such as the voltage and the length of each asset, can be provided to produce optional categorised results. When provided with hourly representative snapshots of these inputs, InfraFair can calculate (per snapshot and overall annual weighted average):

* Individual agent flows, losses and cost contributions to each asset in the network.
* Country flows, losses and cost contributions to each asset in the network.
* Individual agent and country utilisation of each asset in the network.
* Individual Agent flows, losses and cost contributions to similar aggregated assets.
* Country flows, losses and cost contributions to similar aggregated assets. 
* Individual agent and country utilisation of similar aggregated assets.
* Individual Agent total cost contribution to be paid.
* Individual agent and country utilisation of the whole network.
* Country flows, losses and cost contributions made of the use of each other country.
* Country total flow and cost contributions made of the use of the rest of the network.
* Country flows, losses and cost incurred from the use made by the rest of the countries.


Target user group
=================

InfraFair is primarily intended for researchers, planners and regulators who need a 
transparent and fair tool for allocating the cost of investment in flow-based infrastructure. 
InfraFair is **free software** and can be arbitrarily extended.


Licence
=======

Copyright 2023 `Universidad Pontificia Comillas <https://www.comillas.edu/en/>`_

InfraFair is licensed under the open source `AGPL-3.0 license <https://github.com/IIT-EnergySystemModels/InfraFair/tree/main/LICENSE>`_.
