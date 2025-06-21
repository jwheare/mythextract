#!/usr/bin/env python3
import sys
import os
import struct

import myth_headers
import myth_tags
import mesh_tag
import myth_collection
import myth_sound
import myth_projectile
import mons_tag
import utils

DEBUG = (os.environ.get('DEBUG') == '1')
DEAD_TAGS = (os.environ.get('DEAD_TAGS') == '1')

def main(input_file):
    """
    Prints header info for an extracted tag file
    """
    tag_data = utils.load_file(input_file)
    try:
        print_tag_info(tag_data)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def print_tag_obj(tag_obj):
    print(f'{"field":<42} {"decoder/scale factor":<32} value')
    print(f'{"-"*42}-{"-"*32}-{"-"*16}')
    for i, (f, val) in enumerate(tag_obj._asdict().items()):
        decoder = tag_obj._decoders[i]
        dec = ''
        if callable(decoder):
            dec = decoder.__name__
        elif decoder:
            dec = str(decoder)
        print(f'{f:<42} {dec:<32} {utils.val_repr(val, tag_obj)}')

def print_tag_info(tag_data):
    tag_header = myth_headers.parse_header(tag_data)
    print(tag_header)
    print(f'data size: {len(tag_data)}')
    match tag_header.tag_type:
        case 'mesh':
            print_tag_obj(mesh_tag.parse_header(tag_data))
        case 'soun':
            print_tag_obj(myth_sound.parse_soun_header(tag_data))
        case 'amso':
            print_tag_obj(myth_sound.parse_amso(tag_data))
        case 'lpgr':
            print_tag_obj(myth_projectile.parse_lpgr(tag_data))
        case 'core':
            print_tag_obj(myth_collection.parse_collection_ref(tag_data))
        case 'unit':
            print_tag_obj(mons_tag.parse_unit(tag_data))
        case 'conn':
            print_tag_obj(myth_tags.parse_connector(tag_data))
        case 'part':
            print_tag_obj(myth_tags.parse_particle_sys(tag_data))
        case 'medi':
            print_tag_obj(myth_tags.parse_media(tag_data))
        case 'prgr':
            (prgr_head, proj_list) = myth_projectile.parse_prgr(tag_data)
            print_tag_obj(prgr_head)
        case 'mode':
            print_tag_obj(myth_tags.parse_model(tag_data))
        case 'geom':
            print_tag_obj(myth_tags.parse_geom(tag_data))
        case 'mons':
            mons_obj = mons_tag.parse_tag(tag_data)
            print_tag_obj(mons_obj)
            print('extended_flags')
            for k, v in mons_tag.extended_flags(mons_obj).items():
                print(f'{k:<32} {v}')
        case 'anim':
            print_tag_obj(myth_tags.parse_anim(tag_data))
        case 'scen':
            print_tag_obj(myth_tags.parse_scenery(tag_data))
        case 'proj':
            print_tag_obj(myth_projectile.parse_proj(tag_data))
        case 'arti':
            print_tag_obj(mons_tag.parse_artifact(tag_data))
        case '.256':
            print_tag_obj(myth_collection.parse_collection_header(tag_data, tag_header))
        case 'ligh':
            print_tag_obj(myth_projectile.parse_lightning(tag_data))
        case 'obje':
            print_tag_obj(mons_tag.parse_obje(tag_data))
        case 'd256':
            print_tag_obj(myth_collection.parse_d256_header(tag_data))
        case _:
            print(f"Unhandled tag type: {tag_header.tag_type}")
            sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tag2info.py <input_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]

    try:
        main(input_file)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
