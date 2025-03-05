#!/usr/bin/env python3
import sys
import os
import pathlib
import struct
from collections import OrderedDict

import myth_headers
import tag2png

DEBUG = (os.environ.get('DEBUG') == '1')

def main(tag_path):
    """
    Parse a Myth II font tag file and output the bitmaps
    """
    data = myth_headers.load_file(tag_path)

    header = myth_headers.parse_header(data)
    (width, height, pixel_rows) = parse_font_tag(data)

    png = tag2png.make_png(width, height, pixel_rows)
    output_path = pathlib.Path(sys.path[0], f'../output/fonts/font-{header.tag_id}.png').resolve()

    if prompt(output_path):
        pathlib.Path(output_path.parent).mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as png_file:
            png_file.write(png)

def prompt(prompt_path):
    # return True
    response = input(f"Write test file to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

def parse_font_tag(data):
    try:
        font_header_start = myth_headers.TAG_HEADER_SIZE
        font_header_end = font_header_start + 64
        # 0000 0000 000C 0003 0000 0000 0000 00DD 0000 0040 0000553C 676F3032
        (
            flags,
            ascending_height, # 5 for heading (size 17) 3 for body (size 12)
            descending_height,
            leading_height, leading_width,
            num_glyphs,
            font_data_offset, font_data_len,
            italic_font, bold_font, condensed_font, underlined_font,
            italic_index, bold_index, condense_index, underlined_index,
            _, _
        ) = struct.unpack(
                """>
                4s
                H H
                H H
                L
                L L
                4s 4s 4s 4s
                H H H H
                8s 8s
                """,
                data[font_header_start:font_header_end]
        )

        total_height = ascending_height + descending_height
        print(
            f'glyphs={num_glyphs} '
            f'asc_h={ascending_height} desc_h={descending_height} total_h={total_height} '
            f'lead_h={leading_height} lead_w={leading_width} '
            f'flags={flags.hex()}'
        )

        glyph_head_start = font_header_end

        glyph_i = 1
        rows = OrderedDict()
        full_width = 0
        empty = (255,255,255,0)
        print('  i | c | cw | bit_w x bit_h      | o_x | o_y')
        print('----+---+----+--------------------+-----+-----')
        while glyph_head_start < font_data_len:
            glyph_head_end = glyph_head_start + 16
            # 0020       0004     0000   0000   002D    0037    0000 0000
            # 0021       0004     0003   000A   FFFF    000A    0000 0000
            # glyph_char char_w   bit_w  bit_h  orig_x  orig_y  runtime

            (
                glyph_char,
                char_w, # positive horizontal pen offset in pixels after drawing this character
                bit_w, bit_h, # bitmap dimensions
                orig_x, orig_y, # origin coordinates, can be outside of bitmap
                _ # runtime data
            ) = struct.unpack(
                """>
                    2s H
                    H H
                    h h
                    4s
                """,
                data[glyph_head_start:glyph_head_end]
            )
            glyph_char = glyph_char.split(b'\x00')[-1].decode('mac-roman')
            g_pix = bit_w*bit_h
            glyph_size = g_pix + (g_pix & 1)
            delta_w = char_w - bit_w
            print(
                f'{glyph_i:03} | {glyph_char} | '
                f'{char_w:>2} | {bit_w:>2}x{bit_h:<2} = {(bit_w*bit_h):>3} -> {glyph_size:>3} | '
                f'{orig_x:>3} | {orig_y:>3}'
            )

            glyph_data_start = glyph_head_end
            glyph_data_end = glyph_data_start + glyph_size
            glyph_data = data[glyph_data_start:glyph_data_end]

            glyph_rows = []
            glyph_width = max(char_w, bit_w)
            if glyph_size:
                # TODO handle orig_x
                empty_row = glyph_width * [empty]

                # Add starting rows
                start_row = ascending_height - orig_y
                for s in range(start_row):
                    glyph_rows.append(empty_row)

                # Add glyph rows
                for y in range(bit_h):
                    row = []
                    for x in range(bit_w):
                        ix = y*bit_w+x
                        alpha = glyph_data[ix]
                        row.append((0,0,0, 255-alpha))
                    if delta_w > 0:
                        # row += delta_w * [(100,200,0,255)]
                        row += delta_w * [empty]
                    glyph_rows.append(row)

                # Add remainder rows
                remainder = total_height - bit_h
                for r in range(remainder):
                    glyph_rows.append(empty_row)
                
                full_width = full_width + glyph_width

            else:
                for r in range(total_height):
                    glyph_rows.append(char_w * [empty])

                full_width = full_width + char_w
            rows[glyph_char] = glyph_rows

            # Set value for next loop
            glyph_head_start = glyph_data_end
            glyph_i = glyph_i + 1

        render_rows = []
        pre_text = 'Soulblighter Sunday'
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

    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tag2font.py <input_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]

    try:
        main(input_file)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.exit(1)
