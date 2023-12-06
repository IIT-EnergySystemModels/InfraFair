from setuptools import setup

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
print(logo)

setup(
    name='InfraFair',
    version='1.0.0',    
    description='A modelling tool for infrastructure cost allocation',
    url='https://github.com/IIT-EnergySystemModels/InfraFair',
    author='Mohamed A.Eltahir Elabbas',
    author_email='mohamed.a.eltahir@hotmail.com',
    license='GNU AFFERO General Public License v3',
    long_description = "README.md",
    packages=['InfraFair'],
    install_requires=['numpy',
                      'pandas',
                      'matplotlib',                  
                      ],
    dependency_links=[
        "http://pandas.pydata.org/",
        "http://www.numpy.org/",
        "https://matplotlib.org/",
    ],     
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'Environment :: Console',
        'License :: OSI Approved :: GNU Affero General Public License v3',  
        'Operating System :: OS Independent',
        'Natural Language :: English',        
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],   
)