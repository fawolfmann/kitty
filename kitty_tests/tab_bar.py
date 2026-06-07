#!/usr/bin/env python
# License: GPL v3 Copyright: 2026, Kovid Goyal <kovid at kovidgoyal.net>

from kitty.config import defaults, load_config
from kitty.fast_data_types import (
    BOTTOM_EDGE,
    DECAWM,
    LEFT_EDGE,
    RIGHT_EDGE,
    TOP_EDGE,
    Color,
)
from kitty.options.utils import tab_bar_edge as parse_tab_bar_edge
from kitty.tab_bar import (
    DrawData,
    ExtraData,
    TabBarData,
    draw_tab_vertical_fade,
    draw_tab_vertical_powerline,
    draw_tab_vertical_separator,
    draw_tab_vertical_slant,
    truncate_to_visible_width,
    vertical_powerline_caps,
)

from . import BaseTest

VERTICAL_DRAW_FUNCS = (
    draw_tab_vertical_fade, draw_tab_vertical_separator,
    draw_tab_vertical_powerline, draw_tab_vertical_slant,
)


class TestTabBar(BaseTest):

    def draw_data(self, edge='left', powerline_style='angled'):
        return DrawData(
            0, '', 0, '', (),
            Color(255, 255, 255), Color(60, 80, 110),   # active fg/bg
            Color(160, 164, 170), Color(40, 44, 50),     # inactive fg/bg
            Color(34, 40, 46),                            # default_bg (panel)
            '{title}', None, '', powerline_style, edge, 0, 0,
        )

    def test_tab_bar_edge_parsing(self):
        self.ae(parse_tab_bar_edge('left'), LEFT_EDGE)
        self.ae(parse_tab_bar_edge('right'), RIGHT_EDGE)
        self.ae(parse_tab_bar_edge('top'), TOP_EDGE)
        self.ae(parse_tab_bar_edge('bottom'), BOTTOM_EDGE)
        self.ae(parse_tab_bar_edge('Bottom'), BOTTOM_EDGE)
        self.ae(parse_tab_bar_edge('garbage'), BOTTOM_EDGE)  # fallback
        self.ae(defaults.tab_bar_width, 200.0)

    def test_vertical_tab_bar_background_default(self):
        # A vertical bar with no explicit tab_bar_background derives a distinct panel.
        o = load_config(overrides=('tab_bar_edge left', 'background #0f1419', 'foreground #d0d0d0'))
        self.assertIsNotNone(o.tab_bar_background)
        self.assertNotEqual(o.tab_bar_background, Color(0x0f, 0x14, 0x19))
        # An explicit tab_bar_background is respected.
        o = load_config(overrides=('tab_bar_edge right', 'tab_bar_background #112233'))
        self.ae(o.tab_bar_background, Color(0x11, 0x22, 0x33))
        # Horizontal bars are unchanged (stay unset by default).
        o = load_config(overrides=('tab_bar_edge bottom', 'background #0f1419'))
        self.assertIsNone(o.tab_bar_background)

    def test_truncate_to_visible_width(self):
        tr = truncate_to_visible_width
        self.ae(tr('hello', 10), 'hello')          # fits unchanged
        self.ae(tr('hello world', 5), 'hell…')      # cut + ellipsis
        self.ae(tr('', 5), '')
        self.ae(tr('abc', 0), '')
        # SGR escapes are preserved and do not count towards width.
        out = tr('\x1b[31mhello world\x1b[0m', 5)
        self.assertTrue(out.startswith('\x1b[31m'))
        self.assertTrue(out.endswith('…'))
        # Wide (double-width) characters are measured correctly.
        self.ae(tr('日本語', 7), '日本語')
        self.ae(tr('日本語', 3), '日…')

    def test_vertical_styles_render(self):
        titles = ['vim', 'very-long-tab-name', 'logs', 'htop']
        ncols = 14
        for edge in ('left', 'right'):
            dd = self.draw_data(edge)
            for fn in VERTICAL_DRAW_FUNCS:
                s = self.create_screen(cols=ncols, lines=len(titles))
                s.reset_mode(DECAWM)
                for row, title in enumerate(titles):
                    tab = TabBarData(title=title, tab_id=-1, is_active=(row == 1))
                    s.cursor.x = 0
                    s.cursor.y = row
                    fn(dd, s, tab, ncols, row + 1, row == len(titles) - 1, ExtraData())
                # Every tab occupies a full-width row.
                for y in range(len(titles)):
                    self.ae(len(str(s.line(y))), ncols)
                # The over-long title is truncated with an ellipsis.
                self.assertIn('…', str(s.line(1)), f'{fn.__name__} edge={edge}')
                # Short titles render verbatim.
                self.assertIn('vim', str(s.line(0)))

    def test_vertical_powerline_cap(self):
        # The content-facing edge cap is placed on the correct side per edge.
        # Compare against the glyph from tab_bar.py itself (avoids source literal issues).
        for edge, col, cap_idx in (('left', 13, 0), ('right', 0, 1)):
            s = self.create_screen(cols=14, lines=1)
            s.reset_mode(DECAWM)
            tab = TabBarData(title='x', tab_id=-1, is_active=True)
            draw_tab_vertical_powerline(self.draw_data(edge), s, tab, 14, 1, True, ExtraData())
            self.ae(str(s.line(0))[col], vertical_powerline_caps['angled'][cap_idx])

    def test_tab_title_max_length_in_vertical(self):
        dd = self.draw_data('left')._replace(max_tab_title_length=4)
        s = self.create_screen(cols=20, lines=1)
        s.reset_mode(DECAWM)
        tab = TabBarData(title='abcdefghij', tab_id=-1, is_active=False)
        draw_tab_vertical_fade(dd, s, tab, 20, 1, True, ExtraData())
        # Visible (stripped) title is capped to tab_title_max_length cells incl. ellipsis.
        text = str(s.line(0)).strip()
        self.assertLessEqual(len(text), 4)
        self.assertTrue(text.endswith('…'))
