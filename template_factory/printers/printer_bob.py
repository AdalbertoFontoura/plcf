from __future__ import absolute_import

""" Template Factory: CS-Studio Display Builder printer """


__author__     = "Krisztian Loki"
__copyright__  = "Copyright 2017, European Spallation Source, Lund"
__license__    = "GPLv3"



from . import PRINTER
from tf_ifdef import BASE_TYPE, BIT, ENUM



def printer():
    return (BOB.name(), BOB)




class BOB(PRINTER):
    # between label and PV
    HSPACE_1           = 10

    # between columns
    HSPACE_2           = 38

    # height of labels and PVs + space between rows
    HEIGHT             = 25

    # between groups
    VSPACE_2           = 20

    LABEL_WIDTH        = 200
    TEXTUPDATE_WIDTH   = 150
    TEXTENTRY_WIDTH    = 150
    COMBOBOX_WIDTH     = 150
    ACTIONBUTTON_WIDTH = 150
    GROUP_WIDTH        = 42
    GROUP_HEIGHT       = 42

    LABEL = """    <widget type="label" version="2.0.0">
      <name>Label {name}</name>
      <text>{text}</text>
      <x>{x}</x>
      <y>{y}</y>
      <width>{width}</width>
      <horizontal_alignment>2</horizontal_alignment>
      <vertical_alignment>1</vertical_alignment>
      <tooltip>{text}</tooltip>
    </widget>
"""

    TEXTUPDATE = """    <widget type="textupdate" version="2.0.0">
      <name>{name}</name>
      <pv_name>{pv_name}</pv_name>
      <x>{x}</x>
      <y>{y}</y>
      <width>{width}</width>
    </widget>
"""

    TEXTENTRY = """    <widget type="textentry" version="3.0.0">
      <name>{name}</name>
      <pv_name>{pv_name}</pv_name>
      <x>{x}</x>
      <y>{y}</y>
      <width>{width}</width>
    </widget>
"""

    COMBOBOX = """    <widget type="combo" version="2.0.0">
    <name>Combo Box</name>
    <pv_name>{pv_name}</pv_name>
    <x>{x}</x>
    <y>{y}</y>
    <height>20</height>
    <width>{width}</width>
  </widget>
"""

    ACTIONBUTTON = """    <widget type="action_button" version="3.0.0">
    <name>{name}</name>
    <actions>
      <action type="write_pv">
        <pv_name>$(pv_name)</pv_name>
        <value>1</value>
        <description>Execute</description>
      </action>
    </actions>
    <pv_name>{pv_name}</pv_name>
    <x>{x}</x>
    <y>{y}</y>
    <height>20</height>
    <tooltip>$(actions)</tooltip>
    <width>{width}</width>
  </widget>
"""


    SEPARATOR = """    <widget type="polyline" version="2.0.0">
    <name>Polyline</name>
    <x>{x}</x>
    <y>{y}</y>
    <width>4</width>
    <height>{height}</height>
    <line_width>4</line_width>
    <line_color>
      <color name="Grid" red="169" green="169" blue="169">
      </color>
    </line_color>
    <points>
      <point x="0.0" y="0.0">
      </point>
      <point x="0.0" y="{height}.0">
      </point>
    </points>
  </widget>
"""

    def __init__(self):
        super(BOB, self).__init__(comments = False, preserve_empty_lines = False, show_origin = False)
        self._x      = 0
        self._y      = 0


    @staticmethod
    def name():
        return "BOB"


    #
    # HEADER
    #
    def header(self, header_if_def, output, **keyword_params):
        super(BOB, self).header(header_if_def, output, **keyword_params)
        self.add_filename_header(output, extension = "bob")
        self._append("""<?xml version="1.0" encoding="UTF-8"?>
<display version="2.0.0">
  <name>Display</name>""", output)


    #
    # BODY
    #
    def _ifdef_body(self, if_def, output, **keyword_params):
        x                = 0
        y                = 0
        group_width      = BOB.GROUP_WIDTH;
        group_height     = BOB.GROUP_HEIGHT;

        inst_slot = self.inst_slot(if_def)

        self._append("""  <widget type="group" version="2.0.0">
    <name>{group}</name>
    <x>{x}</x>
    <y>{y}</y>
    <transparent>true</transparent>""".format(group = self.raw_inst_slot(if_def),
                                              x     = self._x,
                                              y     = self._y), output)

        left = True
        max_width = BOB.LABEL_WIDTH + BOB.HSPACE_1 + max(BOB.TEXTUPDATE_WIDTH, BOB.TEXTENTRY_WIDTH, BOB.ACTIONBUTTON_WIDTH, BOB.COMBOBOX_WIDTH)

        for var in if_def.interfaces():
            if not isinstance(var, BASE_TYPE):
                continue

            label_x = x if left else x + width + BOB.HSPACE_2

            self._append(BOB.LABEL.format(name       = var.name(),
                                          text       = "{}:".format(var.get_parameter("PV_DESC", var.name())).replace("<", "&lt;").replace(">", "&gt;"),
                                          x          = label_x,
                                          y          = y,
                                          width      = BOB.LABEL_WIDTH), output)

            if var.is_status():
                self._append(BOB.TEXTUPDATE.format(name    = var.name(),
                                                   pv_name = var.fqpn(),
                                                   x       = label_x + BOB.HSPACE_1 + BOB.LABEL_WIDTH,
                                                   y       = y,
                                                   width   = BOB.TEXTUPDATE_WIDTH), output)
                width = BOB.LABEL_WIDTH + BOB.HSPACE_1 + BOB.TEXTUPDATE_WIDTH
            else:
                if isinstance(var, BIT):
                    self._append(BOB.ACTIONBUTTON.format(name    = var.name(),
                                                         pv_name = var.fqpn(),
                                                         x       = label_x + BOB.HSPACE_1 + BOB.LABEL_WIDTH,
                                                         y       = y,
                                                         width   = BOB.ACTIONBUTTON_WIDTH), output)
                    width = BOB.LABEL_WIDTH + BOB.HSPACE_1 + BOB.ACTIONBUTTON_WIDTH
                elif isinstance(var, ENUM):
                    self._append(BOB.COMBOBOX.format(name    = var.name(),
                                                     pv_name = var.fqpn(),
                                                     x       = label_x + BOB.HSPACE_1 + BOB.LABEL_WIDTH,
                                                     y       = y,
                                                     width   = BOB.COMBOBOX_WIDTH), output)
                    width = BOB.LABEL_WIDTH + BOB.HSPACE_1 + BOB.COMBOBOX_WIDTH
                else:
                    self._append(BOB.TEXTENTRY.format(name    = var.name(),
                                                      pv_name = var.fqpn(),
                                                      x       = label_x + BOB.HSPACE_1 + BOB.LABEL_WIDTH,
                                                      y       = y,
                                                      width   = BOB.TEXTENTRY_WIDTH), output)
                    width = BOB.LABEL_WIDTH + BOB.HSPACE_1 + BOB.TEXTENTRY_WIDTH

            if not left:
                y = y + BOB.HEIGHT
            left = not left

        if not left:
            y = y + BOB.HEIGHT

        group_width  = group_width + 2 * max_width + BOB.HSPACE_2
        group_height = group_height + y
        self._y      = self._y + group_height + BOB.VSPACE_2

        self._append(BOB.SEPARATOR.format(x      = max_width + BOB.HSPACE_2 // 2,
                                          y      = 5,
                                          height = y - 10), output)

        self._append("""    <width>{group_width}</width>
    <height>{group_height}</height>
</widget>""".format(group_width  = group_width,
                    group_height = group_height), output)


    #
    # FOOTER
    #
    def footer(self, footer_if_def, output, **keyword_params):
        super(BOB, self).footer(footer_if_def, output, **keyword_params)
        self._append("""<height>{height}</height>
</display>
""".format(height = self._y), output)
