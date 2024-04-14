.. InfraFair documentation master file, created by Mohamed A.Eltahir Elabbas

##########################################
 Release Notes
##########################################

Below are some of the features we are considering in future releases.

* Add graphical representations for the results.
* Program soft linkages with other software, e.g., the PSS/E software for electricity infrastructure, and integrated assessment platforms, e.g., the IAMC Scenario Explorer. 
* Include consideration and applications for other flow-based infrastructure, potentially gas, hydrogen and heat infrastructure.
* Feature an interactive option for users to create their own network from scratch.	 

InfraFair 1.1.0 (4th of April 2024)
===========================================
This version includes the following improvements:

* Adding losses allocation feature with split key and price input option.
* Improving the execution of function get_total_nodal_flows().
* Allowing the duplicated assets with an optional ID column to be processed.
* Adding joint results for countries and SOs results.
* Adding optional input variables to allocate the cost and losses of assets classified as regional only.
* Fixing the bug with the EU examples raw data for asset duplication processing.
* Fixing bugs in some "if" conditions and renaming variables for better readability.
* Changing the dependency version of Pandas for processing duplicated assets in the setup file.  

InfraFair 1.0.0 (6th of December 2023)
===========================================
This was the first release of InfraFair. It contains the core of the model with the basic feature of 
exporting raw results in the form of .csv files. In this release, special attention was 
given to the electricity infrastructure, as this is the field in which the model was 
scientifically conceived. 