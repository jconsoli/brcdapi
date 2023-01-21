# Copyright 2022, 2023 Jack Consoli.  All rights reserved.
#
# NOT BROADCOM SUPPORTED
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may also obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
:mod:`brcdapi.excel_fonts` - Contains miscellaneous font, fill, and alignment definitions for the openpyxl library

Public Methods & Data::

    +-----------------------+---------------------------------------------------------------------------------------+
    | Method                | Description                                                                           |
    +=======================+=======================================================================================+
    | font_type             | Returns the font definition tuple for the openpyxl libraries                          |
    +-----------------------+---------------------------------------------------------------------------------------+
    | fill_type             | Returns the font definition tuple for the openpyxl libraries                          |
    +-----------------------+---------------------------------------------------------------------------------------+
    | border_type           | Returns the border definition tuple for the openpyxl libraries                        |
    +-----------------------+---------------------------------------------------------------------------------------+
    | align_type            | Returns the alignment definition tuple for the openpyxl libraries                     |
    +-----------------------+---------------------------------------------------------------------------------------+

Version Control::

    +-----------+---------------+-----------------------------------------------------------------------------------+
    | Version   | Last Edit     | Description                                                                       |
    +===========+===============+===================================================================================+
    | 1.0.0     | 28 Apr 2022   | Initial Launch                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 1.0.1     | 22 Jun 2022   | Added default of None when passed parm in font_type(), fill_type(),               |
    |           |               | border_type(), and align_type()                                                   |
    +-----------+---------------+-----------------------------------------------------------------------------------+
    | 1.0.2     | 21 Jan 2023   | Added cli_font                                                                    |
    +-----------+---------------+-----------------------------------------------------------------------------------+
"""
__author__ = 'Jack Consoli'
__copyright__ = 'Copyright 2022, 2023 Jack Consoli'
__date__ = '21 Jan 2023'
__license__ = 'Apache License, Version 2.0'
__email__ = 'jack.consoli@broadcom.com'
__maintainer__ = 'Jack Consoli'
__status__ = 'Released'
__version__ = '1.0.2'

import brcdapi.log as brcdapi_log
import openpyxl.styles as xl_styles

#################################################################
#   Font Types                                                  #
#                                                               #
#   If you add a font type, remember to add it to font_tbl      #
#################################################################
cli_font = xl_styles.Font(
    name='Courier New',
    size=11,
    bold=False,
    italic=False,
    vertAlign=None,
    underline='none',
    strike=False,
    color='FF000000')
std_font = xl_styles.Font(
    name='Calibri',
    size=11,
    bold=False,
    italic=False,
    vertAlign=None,
    underline='none',
    strike=False,
    color='FF000000')
h1_font = xl_styles.Font(
    name='Calibri',
    size=14,
    bold=True,
    italic=False,
    vertAlign=None,
    underline='none',
    strike=False,
    color='FF000000')
h2_font = xl_styles.Font(
    name='Calibri',
    size=12,
    bold=True,
    italic=False,
    vertAlign=None,
    underline='none',
    strike=False,
    color='FF000000')
bold_font = xl_styles.Font(
    name='Calibri',
    size=11,
    bold=True,
    italic=False,
    vertAlign=None,
    underline='none',
    strike=False,
    color='FF000000')
italic_font = xl_styles.Font(
    name='Calibri',
    size=11,
    bold=False,
    italic=True,
    vertAlign=None,
    underline='none',
    strike=False,
    color='FF000000')
warn_font = xl_styles.Font(
    name='Calibri',
    size=11,
    bold=True,
    italic=False,
    vertAlign=None,
    underline='none',
    strike=False,
    color='FF8000')
error_font = xl_styles.Font(
    name='Calibri',
    size=11,
    bold=True,
    italic=False,
    vertAlign=None,
    underline='none',
    strike=False,
    color='FF0000')
link_font = xl_styles.Font(
    name='Calibri',
    size=11,
    bold=False,
    italic=False,
    vertAlign=None,
    underline='single',
    strike=False,
    color='3336FF')
_white_bold_font = xl_styles.Font(
    name='Calibri',
    size=11,
    bold=True,
    italic=False,
    vertAlign=None,
    underline='none',
    strike=False,
    color='FFFFFFFF')
font_tbl = dict(
    cli=cli_font,
    std=std_font,
    hdr_1=h1_font,
    hdr_2=h2_font,
    bold=bold_font,
    italic=italic_font,
    warn=warn_font,
    error=error_font,
    link=link_font,
    white_bold=_white_bold_font,
)

#################################################################
#   Fill Types                                                  #
#                                                               #
#   If you add a fill type, remember to add it to _fill_tbl      #
#################################################################
_lightblue_fill = xl_styles.PatternFill(  # Fill used in reports
    fill_type='solid',
    start_color='FFCCE5FF',
)
_config_asic_0_fill = xl_styles.PatternFill(  # orange color used in switch configuration workbook for ASIC 0
    fill_type='solid',
    start_color='FFFCD5B4',
)
_config_asic_1_fill = xl_styles.PatternFill(  # grey-blue color used in switch configuration workbook for ASIC 1
    fill_type='solid',
    start_color='FFDCE6F1',
)
_config_slot_fill = xl_styles.PatternFill(  # Fill used in reports
    fill_type='solid',
    start_color='FFC00000',
)
_fill_tbl = dict(
    lightblue=_lightblue_fill,
    config_asic_0=_config_asic_0_fill,
    config_asic_1=_config_asic_1_fill,
    config_slot=_config_slot_fill,
)

#################################################################
#   Border Types                                                #
#                                                               #
#   If you add a border type, remember to add it to border_tbl  #
#################################################################
thin_border = xl_styles.Border(
    left=xl_styles.Side(border_style='thin', color='FF000000'),
    right=xl_styles.Side(border_style='thin', color='FF000000'),
    top=xl_styles.Side(border_style='thin', color='FF000000'),
    bottom=xl_styles.Side(border_style='thin', color='FF000000'),
    # diagonal=xl_styles.Side(border_style=None,color='FF000000'),
    # diagonal_direction=0,outline=xl_styles.Side(border_style=None,color='FF000000'),
    # vertical=xl_styles.Side(border_style=None,color='FF000000'),
    # horizontal=xl_styles.Side(border_style=None,color='FF000000')
)
border_tbl = dict(
    thin=thin_border,
)

#################################################################
#   Align Types                                                 #
#                                                               #
#   If you add an align type, remember to add it to align_tbl   #
#################################################################
wrap_center_alignment = xl_styles.Alignment(
    horizontal='center',
    vertical='top',
    text_rotation=0,
    wrap_text=True,
    shrink_to_fit=False,
    indent=0)
wrap_right_alignment = xl_styles.Alignment(
    horizontal='right',
    vertical='top',
    text_rotation=0,
    wrap_text=True,
    shrink_to_fit=False,
    indent=0)
wrap_alignment = xl_styles.Alignment(
    horizontal='general',
    vertical='top',
    text_rotation=0,
    wrap_text=True,
    shrink_to_fit=False,
    indent=0)
wrap_vert_center_alignment = xl_styles.Alignment(
    horizontal='center',
    vertical='top',
    text_rotation=90,
    wrap_text=True,
    shrink_to_fit=False,
    indent=0)
align_tbl = dict(
    wrap_center=wrap_center_alignment,
    wrap=wrap_alignment,
    wrap_vert_center=wrap_vert_center_alignment,
    wrap_right=wrap_right_alignment,
)


def font_type(x):
    """Returns the font definition tuple for the openpyxl libraries

    :param x: Font type listed in font_tbl
    :type x: str
    :return: Font definitions for openpyxl library
    :rtype: tuple
    """
    global font_tbl, std_font

    if x is None:
        return None
    if x in font_tbl:
        return font_tbl[x]
    brcdapi_log.exception('Unknown font type: ' + x, True)
    return std_font


def fill_type(x):
    """Returns the font definition tuple for the openpyxl libraries

    :param x: Fill type listed in font_tbl
    :type x: str
    :return: Fill definitions for openpyxl library
    :rtype: tuple
    """
    global _fill_tbl, _lightblue_fill

    if x is None:
        return None
    if x in _fill_tbl:
        return _fill_tbl[x]
    brcdapi_log.exception('Unknown fill type: ' + x, True)
    return _lightblue_fill


def border_type(x):
    """Returns the border definition tuple for the openpyxl libraries

    :param x: Border type listed in font_tbl
    :type x: str
    :return: Border definitions for openpyxl library
    :rtype: tuple
    """
    global border_tbl, thin_border

    if x is None:
        return None
    if x in border_tbl:
        return border_tbl[x]
    brcdapi_log.exception('Unknown border type: ' + x, True)
    return thin_border


def align_type(x):
    """Returns the alignment definition tuple for the openpyxl libraries

    :param x: Alignment type listed in font_tbl
    :type x: str
    :return: Alignment definitions for openpyxl library
    :rtype: tuple
    """
    global align_tbl, wrap_alignment

    if x is None:
        return None
    if x in align_tbl:
        return align_tbl[x]
    brcdapi_log.exception('Unknown align type: ' + x, True)
    return wrap_alignment
