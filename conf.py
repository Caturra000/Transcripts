# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys
sys.path.insert(0, os.path.abspath('_sphinx_spec'))

project = 'Caturra的中文转录小站'
copyright = '2025, Caturra'
author = 'Caturra'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "revitron_sphinx_theme",
    "myst_parser",
]

autodoc_default_options = {
    'autosummary': False 
}

html_theme = 'revitron_sphinx_theme'

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_static_path = ['_static']

html_theme_options = {
    'color_scheme': 'dark'
}

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

html_theme_options = {
    'navigation_depth': 5,
	'color_scheme': 'dark'
}

