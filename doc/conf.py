# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project     = 'InfraFair'
copyright   = '2023, Universidad Pontificia Comillas'
author      = 'Mohamed A.Eltahir Elabbas'
version     = "1.0"
release     = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.mathjax",
    "sphinx.ext.napoleon",
    "sphinx.ext.imgconverter",  # for SVG conversion
]

templates_path      = ['_templates']
exclude_patterns    = ['_build', 'Thumbs.db', '.DS_Store']

autosummary_generate    = True
todo_include_todos      = True

source_suffix   = ".rst"
master_doc      = "index"
language        = "en"


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme          = 'sphinx_book_theme'
html_static_path    = ['_static']
html_css_files      = ['CSS/custom.css']
html_theme_options  = {
    "repository_url": "https://github.com/IIT-EnergySystemModels/InfraFair/tree/main",
    "use_repository_button": True,
    "show_navbar_depth": 1,
}
html_title          = "InfraFair"
html_logo           = "Images/Logo InfraFair.png"
htmlhelp_basename   = "InfraFairdoc"


# -- Options for manual page output ---------------------------------------
man_pages = [(master_doc, "InfraFair", "InfraFair Documentation", [author], 1)]


# -- Options for Texinfo output -------------------------------------------
texinfo_documents = [
    (
        master_doc,
        "InfraFair",
        "InfraFair Documentation",
        author,
        "InfraFair",
    ),
]
intersphinx_mapping = {"https://docs.python.org/": None}
