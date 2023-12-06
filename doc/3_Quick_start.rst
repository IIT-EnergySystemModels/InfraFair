.. InfraFair documentation master file, created by Mohamed A.Eltahir Elabbas

###########################
Quick Start
###########################

Developers
==========
By cloning the `InfraFair <https://github.com/IIT-EnergySystemModels/InfraFair/tree/main>`_ repository, 
you can create branches and propose pull-request. We strongly welcome anyone interested in contributing to this project.

Users
=====
If you are not planning on developing, please follow the instructions of the :doc:`2_Installation` first. 

Once installation is complete, `InfraFair <https://github.com/IIT-EnergySystemModels/InfraFair/tree/main>`_ can be 
executed by using a command prompt. In the directory of your choice, open and execute the InfraFair.py script by using 
the following on the command prompt (Windows) or Terminal (Linux) (Depending on what your standard python version is, 
you might need to call `python3` instead of `python`)::

    python InfraFair.py

Then, three parameters (directory folder, and configuration file) will be asked for.

**Remark:** at this step, only press enter for each input and InfraFair will be executed with the default parameters.

After this, in a directory of your choice, make a copy of the `Simple example 
<https://github.com/IIT-EnergySystemModels/InfraFair/tree/main/Examples/Simple_ex>`_ or 
`EU example <https://github.com/IIT-EnergySystemModels/InfraFair/tree/main/Examples/EU_ex>`_ case to create a new 
case of your choice but using the current format of the .csv files.
A proper execution of InfraFair.py can be made by introducing the new case and the directory of your choice. 

Then, the output results should be written in the same folder as the case input. 

.. Note:: 
    that there is an alternative way to run the model by creating a new script **script.py**, and writing the following::
        
        from InfraFair import InfraFair_run
        
        InfraFair_run(<dir>, <case>, <config_file>)
