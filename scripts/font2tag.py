#!/usr/bin/env python3
import math
import sys
import os
import pathlib

import codec
import myth_headers
import font_tag
import utils

# PYTHON-DEPENDENCIES
import freetype
from matplotlib import font_manager

DEBUG = (os.environ.get('DEBUG') == '1')
LIST_FONTS = (os.environ.get('LIST_FONTS') == '1')
FONT_STYLE = os.environ.get('FONT_STYLE', 'normal')
FONT_WEIGHT = int(os.environ.get('FONT_WEIGHT', 400))
FONT_SIZE = int(os.environ.get('FONT_SIZE', 12))
ANTIALIAS = (os.environ.get('ANTIALIAS') == '1')

def main(font_path, output_path):
    """
    Parse a Myth II font tag file and output the bitmaps
    """
    if font_path.is_file():
        font_name = font_path.name
        font_path = str(font_path)
    else:
        font = choose_font(font_path.name, FONT_STYLE, FONT_WEIGHT)
        font_name = font.name
        font_path = font.fname

    make_font(font_name, font_path, output_path, FONT_SIZE, FONT_STYLE, FONT_WEIGHT, ANTIALIAS)

def load_font_face(font_path, font_size):
    face = freetype.Face(font_path)
    face.set_pixel_sizes(0, font_size)  # width=0 means "same as height"
    return face

def make_font(font_name, font_path, output_path, font_size, font_style, font_weight, antialiased):
    face = load_font_face(font_path, font_size)
    # * FreeType values are in 26.6 fixed-point format, hence the >> 6 to get pixels
    # * descender is negative in FreeType, matching the Windows convention where
    #   tmDescent is a positive number representing distance below baseline
    # * tmExternalLeading (the gap between lines added by the OS) has no FreeType
    #   equivalent — it's a Windows GDI concept. You'd typically set it to 0 or derive
    #   it from your own line spacing logic
    # * tmHeight in Windows is tmAscent + tmDescent (which includes internal leading),
    #   matching face.size.height

    tmAscent = face.size.ascender >> 6
    tmDescent = -(face.size.descender >> 6)
    tmHeight = tmAscent + tmDescent
    tmExternalLeading = (face.size.height >> 6) - tmHeight
    tmInternalLeading = math.ceil(font_size / 2) # round up

    ascending_height = tmAscent
    descending_height = tmDescent
    leading_height = tmInternalLeading + tmExternalLeading

    leading_width = 0

    glyph_data = b''
    num_glyphs = 0

    if DEBUG:
        print(
            f'font={font_name} style={font_style} weight={font_weight} '
            f'size={font_size} antialised={antialiased} y_ppem={face.size.y_ppem}\n'
            f'asc_h={ascending_height} desc_h={descending_height} total_h={tmHeight} '
            f'lead_h={leading_height} lead_w={leading_width} '
        )
        print('  i | c | cw | cr | bit_w x bit_h      | o_x | o_y ')
        print('----+---+----+----+--------------------+-----+-----')
    for char_code in range(1, 256):
        if char_code != 0x7f and char_code >= 32:
            glyph_char = bytes([char_code]).decode('mac-roman')
            alpha_rows, glyph = font_face_glyph(face, tmHeight, glyph_char, antialiased)
            (
                bitmap_width, bitmap_height, orig_x, orig_y,
                top, right, bottom, left
            ) = char_props(glyph)
            char_width = glyph.bitmap.width
            # Default char width for space char
            if bitmap_width == 0 and bitmap_height == 0:
                char_width = 4
            if DEBUG:
                print(
                    f'{char_code:03} | {glyph_char} | '
                    f'{char_width:>2} | {glyph.bitmap.rows:>2} | '
                    f'{bitmap_width:>2}x{bitmap_height:<2} = {(bitmap_width*bitmap_height):>3}        | '
                    f'{orig_x:>3} | {orig_y:>3}'
                )
            font_glyph = font_tag.make_font_glyph(
                character_code=char_code,
                character_width=char_width,
                bitmap_width=bitmap_width,
                bitmap_height=bitmap_height,
                origin_x=orig_x,
                origin_y=orig_y
            )
            glyph_data += font_glyph.value

            glyph_pixels = bytes([255-a for a in glyph.bitmap.buffer])
            if len(glyph_pixels) % 2:
                glyph_pixels += b'\x00'

            glyph_data += glyph_pixels
            num_glyphs += 1

    font_header = font_tag.make_font_header(
        flags=0,
        ascending_height=ascending_height,
        descending_height=descending_height,
        leading_height=leading_height,
        leading_width=leading_width,
        num_glyphs=num_glyphs,
        font_data_len=len(glyph_data),
        italic_font=None,
        bold_font=None,
        condensed_font=None,
        underlined_font=None,
    )

    font_data = font_header.value + glyph_data
    tag_name = font_name
    tag_id = myth_headers.generate_tag_id(tag_name)
    tag_header = myth_headers.create_tag_header(
        b'font', tag_id, codec.encode_string(tag_name), len(font_data)
    )
    if not output_path:
        output_path = pathlib.Path(sys.path[0], '../output/tag2font').resolve()
    tag_path = (
        output_path / f'{utils.local_folder(tag_header)}/{tag_name}'
    )
    pathlib.Path(tag_path.parent).mkdir(parents=True, exist_ok=True)
    if not tag_path.is_file() or prompt(tag_path, '🚨 File exists. '):
        with open(tag_path, 'wb') as tag_file:
            tag_file.write(tag_header.value + font_data)

def char_props(glyph):
    bitmap_top = glyph.bitmap_top
    bitmap_left = glyph.bitmap_left
    bitmap_right = bitmap_left + glyph.bitmap.width
    bitmap_bottom = bitmap_top + glyph.bitmap.rows

    if glyph.bitmap.width == 0 and glyph.bitmap.rows == 0:
        bitmap_origin_x = 45
        bitmap_origin_y = 55
    else:
        bitmap_origin_x = -bitmap_left
        bitmap_origin_y = bitmap_top

    return (
        glyph.bitmap.width, glyph.bitmap.rows, bitmap_origin_x, bitmap_origin_y,
        bitmap_top, bitmap_right, bitmap_bottom, bitmap_left
    )

def font_face_glyph(face, tmHeight, char, antialiased):
    face.load_char(char, freetype.FT_LOAD_RENDER)
    glyph = face.glyph

    # Raw 8-bit grayscale bitmap
    alpha_rows = []
    for y in range(glyph.bitmap.rows):
        row = []
        for x in range(glyph.bitmap.width):
            idx = (y * glyph.bitmap.width) + x
            alpha = glyph.bitmap.buffer[idx]
            if antialiased:
                alpha = 255 if alpha == 255 else 0
            row.append(alpha)
        alpha_rows.append(row)

    return alpha_rows, glyph


def choose_font(font_name, font_style, font_weight):
    name_match = False
    fontpaths = []
    found = None
    for font in font_manager.fontManager.ttflist:
        fpath = pathlib.Path(font.fname)
        if fpath.parent not in fontpaths:
            fontpaths.append(fpath.parent)
        if font_name == font.name:
            name_match = True
            if font_style == font.style and font_weight == font.weight:
                if found:
                    print('Duplicate font!')
                    print('prev', found)
                    print('this', font)
                found = font
    print(fontpaths)
    if found:
        return found
    if font_name:
        print(f'Font not found: {font_name}')
    if LIST_FONTS or name_match:
        for font in font_manager.fontManager.ttflist:
            if not name_match or font_name == font.name:
                print(f"{font.name} [{font.style}] [{font.weight}]: {font.fname}")
    input_font = input("Choose a font: ")
    return choose_font(input_font)


def prompt(prompt_path, prefix=''):
    # return False
    response = input(f"{prefix}Write file to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <font_name_or_path> [<output_path>]")
        sys.exit(1)
    
    font_name_or_path = pathlib.Path(sys.argv[1]).resolve()
    output_path = None
    if len(sys.argv) > 2:
        output_path = pathlib.Path(sys.argv[2]).resolve()

    try:
        main(font_name_or_path, output_path)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
