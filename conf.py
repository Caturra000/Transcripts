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
    "sphinxcontrib.jquery",
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

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

html_theme_options = {
    'navigation_depth': 5
}

# 生产模式开启 Jekyll 风味
# 调试模式保持默认 .html 后缀
# 调试模式通过环境变量开启
if os.getenv('CATURRA_SPHINX_DEBUG') is not None:
    html_link_suffix = '.html'
    print("NOTE: 本地调试模式，链接后缀设置为.html")
else:
    html_link_suffix = '/'

html_title = 'Caturra的中文转录小站'

# 个人习惯起手 H2 标签
suppress_warnings = ["myst.header"]
