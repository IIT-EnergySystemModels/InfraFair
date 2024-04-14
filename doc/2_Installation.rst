.. InfraFair documentation master file, created by Mohamed A.Eltahir Elabbas

################
 Installation
################


Getting Python
==============
If it is your first time with Python, we recommend `conda
<https://docs.conda.io/en/latest/miniconda.html>`_ or `pip
<https://pip.pypa.io/en/stable/>`_ as easy-to-use package managers. They are
available for Windows, Mac OS X and GNU/Linux. The minimum Python version tested to use InfraFair is 3.8.

It is always helpful to use dedicated environment, such as the `virtual environments
<https://pypi.python.org/pypi/virtualenv>`_.


Installing InfraFair
===========================
InfraFair can be easily installed with pip:

      > pip install InfraFair 

Alternatively, it can be installed from its GitHub repository following these four steps:

1. Clone the InfraFair repository, which includes the folder structure and all necessary functions to run the model.
2. Launch the command prompt (Windows: Win+R, type "cmd", Enter) or the Anaconda prompt.
3. Set up the path to where the repository was cloned, using the command::
   
        > cd "C:\\Users\\<username>\\...\\InfraFair".
4. Install InfraFair via pip by using the command::
      
        > pip install . 

An already installed model can be upgraded to the latest version with the following command:

      > pip install --upgrade InfraFair 
      

Dependencies
============
InfraFair is programmed and tested to be compatible with Python 3.8 and
above. Like any software project, InfraFair stands on the shoulders of giants. Those giants mainly include:

* `pandas <http://pandas.pydata.org/>`_ for storing data about the network
* `numpy <http://www.numpy.org/>`_ for calculations, such as matrix manipulation 
* `matplotlib <https://matplotlib.org/>`_ for aggregating results
