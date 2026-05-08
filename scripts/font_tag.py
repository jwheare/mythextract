#!/usr/bin/env python3
import os
from collections import OrderedDict

import codec
import myth_headers

DEBUG_FONT = (os.environ.get('DEBUG_FONT') == '1')

FontGlyphFmt = ('FontGlyph', [
    ('H', 'character_code'),
    ('H', 'character_width'),
    ('H', 'bitmap_width'),
    ('H', 'bitmap_height'),
    ('h', 'origin_x'),
    ('h', 'origin_y'),
    ('4x', None),
])

FontHeaderFmt = ('FontHeader', [
    ('l', 'flags'),
    ('H', 'ascending_height'),
    ('H', 'descending_height'),
    ('H', 'leading_height'),
    ('H', 'leading_width'),
    ('L', 'num_glyphs'),
    ('L', 'font_data_offset'),
    ('L', 'font_data_len'),
    ('4s', 'italic_font', codec.String),
    ('4s', 'bold_font', codec.String),
    ('4s', 'condensed_font', codec.String),
    ('4s', 'underlined_font', codec.String),
    ('24x', None), # runtime
])

def make_font_header(**kwargs):
    kwargs['font_data_offset'] = codec.data_size(FontHeaderFmt)
    return codec.input_codec(FontHeaderFmt, **kwargs)

def make_font_glyph(**kwargs):
    return codec.input_codec(FontGlyphFmt, **kwargs)

def parse_font_tag(data, text):
    font_header = myth_headers.parse_tag(FontHeaderFmt, data)
    total_height = font_header.ascending_height + font_header.descending_height
    if DEBUG_FONT:
        print(
            f'glyphs={font_header.num_glyphs} '
            f'asc_h={font_header.ascending_height} desc_h={font_header.descending_height} total_h={total_height} '
            f'lead_h={font_header.leading_height} lead_w={font_header.leading_width} '
            f'flags={font_header.flags} '
            f'italic={font_header.italic_font} '
            f'bold={font_header.bold_font} '
            f'condensed={font_header.condensed_font} '
            f'underline={font_header.underlined_font} '
        )

    glyph_head_start = font_header.font_data_offset + myth_headers.TAG_HEADER_SIZE

    rows = OrderedDict()
    full_width = 0
    empty = (255,255,255,0)
    FontGlyph = codec.codec(FontGlyphFmt)

    if DEBUG_FONT:
        print('  i | c | cw | bit_w x bit_h      | o_x | o_y ')
        print('----+---+----+--------------------+-----+-----')
    while glyph_head_start < font_header.font_data_len:
        font_glyph = FontGlyph(data[glyph_head_start:])
        glyph_head_end = glyph_head_start + font_glyph.data_size()

        g_pix = font_glyph.bitmap_width * font_glyph.bitmap_height
        glyph_size = g_pix + (g_pix & 1)
        delta_w = font_glyph.character_width - font_glyph.bitmap_width

        glyph_char = bytes([font_glyph.character_code]).decode('mac-roman')
        if DEBUG_FONT:
            print(
                f'{font_glyph.character_code:03} | {glyph_char} | '
                f'{font_glyph.character_width:>2} | {font_glyph.bitmap_width:>2}x{font_glyph.bitmap_height:<2} = {(font_glyph.bitmap_width*font_glyph.bitmap_height):>3} -> {glyph_size:>3} | '
                f'{font_glyph.origin_x:>3} | {font_glyph.origin_y:>3} |'
                f'{glyph_head_start} {glyph_head_end} {glyph_head_end - glyph_head_start} {data[glyph_head_start:glyph_head_end].hex()}'
            )

        glyph_data_start = glyph_head_end
        glyph_data_end = glyph_data_start + glyph_size
        glyph_data = data[glyph_data_start:glyph_data_end]

        glyph_rows = []
        glyph_width = max(font_glyph.character_width, font_glyph.bitmap_width)
        if glyph_size:
            # TODO handle font_glyph.origin_x
            empty_row = glyph_width * [empty]

            # Add starting rows
            start_row = font_header.ascending_height - font_glyph.origin_y
            for s in range(start_row):
                glyph_rows.append(empty_row)

            # Add glyph rows
            for y in range(font_glyph.bitmap_height):
                row = []
                for x in range(font_glyph.bitmap_width):
                    ix = y*font_glyph.bitmap_width+x
                    alpha = glyph_data[ix]
                    row.append((0,0,0, 255-alpha))
                if delta_w > 0:
                    # row += delta_w * [(100,200,0,255)]
                    row += delta_w * [empty]
                glyph_rows.append(row)

            # Add remainder rows
            remainder = total_height - font_glyph.bitmap_height
            for r in range(remainder):
                glyph_rows.append(empty_row)
            
            full_width = full_width + glyph_width

        else:
            for r in range(total_height):
                glyph_rows.append(font_glyph.character_width * [empty])

            full_width = full_width + font_glyph.character_width
        rows[glyph_char] = glyph_rows

        # Set value for next loop
        glyph_head_start = glyph_data_end

    render_rows = []
    pre_text = text if text is not None else 'Soulblighter Sunday'
    for char in pre_text:
        full_width = full_width + len(rows[char][0])
    for ri in range(total_height):
        rr = []
        for char in pre_text:
            rr += rows[char][ri]
        for g_r in rows.values():
            rr += g_r[ri]
        render_rows.append(rr)

    return (full_width, total_height, render_rows)
