#!/usr/bin/env python3
import sys
import os
import struct

import codec
import myth_collection
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, coll_id, plugin_names):
    """
    Load Myth game tags and plugins and output sequence data for a collction
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    try:
        if coll_id == 'all':
            for tag_id, d256_headers in tags['.256'].items():
                parse_coll_tag(game_version, tags, data_map, tag_id)
        elif coll_id:
            parse_coll_tag(game_version, tags, data_map, coll_id)
        else:
            print_coll_tags(tags)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def print_coll_tags(tags):
    for coll_id, coll_headers in tags['.256'].items():
        print(coll_id)
        for headers in coll_headers:
            print(f' - {headers[1].name} [{headers[0]}]')

def parse_coll_tag(game_version, tags, data_map, coll_id):
    (tag_location, tag_header, tag_data) = loadtags.get_tag_info(
        tags, data_map, '.256', coll_id
    )
    coll_header = myth_collection.parse_collection_header(tag_data, tag_header)
    sequences = myth_collection.parse_sequences(tag_data, coll_header)
    bitmap_instances = myth_collection.parse_bitmap_instance(tag_data, coll_header)
    shadow_maps = myth_collection.parse_shadow_maps(tag_data, coll_header)
    for sequence in sequences:

        print(coll_id, sequence['name'])
        for f, val in sequence['metadata']._asdict().items():
            if type(val) is bytes and codec.all_on(val):
                val = 'None'
            print(f'{f:<42} {val}')
        for seq_i, (seq_frame, seq_views) in enumerate(sequence['frames']):
            instance_parts = [
                f'Frame {seq_i}',
                f'key_x={seq_frame.key_point_x:<3}',
                f'key_y={seq_frame.key_point_y:<3}',
                f'key_z={seq_frame.key_point_z:<3}',
                f'sm_index={seq_frame.shadow_map_index:<3}',
            ]
            if seq_frame.shadow_map_index > -1 and seq_frame.shadow_map_index < len(shadow_maps):
                shadow_map = shadow_maps[seq_frame.shadow_map_index]
                instance_parts += [
                    f'sm_flags={shadow_map.flags.value}',
                    f'sm_reg_x={round(shadow_map.reg_point_x, 2):<4}',
                    f'sm_reg_y={round(shadow_map.reg_point_y, 2):<4}',
                    f'sm_bm_index={shadow_map.bitmap_index:<4}',
                ]
            print(' '.join(instance_parts))
            for view_i in range(sequence['metadata'].number_of_views):
                view_idx = seq_views[view_i]
                if view_idx > -1 and view_idx < len(bitmap_instances):
                    bitmap_instance = bitmap_instances[view_idx]
                    print(
                        f'Frame {seq_i} View {view_i:<2} '
                        f'bm_flags={bitmap_instance.flags.value} '
                        f'bm_reg_x={bitmap_instance.reg_point_x:<3} '
                        f'bm_reg_y={bitmap_instance.reg_point_y:<3} '
                        f'bm_key_x={bitmap_instance.key_point_x:<3} '
                        f'bm_key_y={bitmap_instance.key_point_y:<3} '
                        f'bm_index={bitmap_instance.bitmap_index}'
                    )
        print('---')

    # Selection Box Size (sequence meta)
    # Key Point Locations (sequence instance)
    # Shadow locations (shadow map)
    # Registration Point (bitmap instance)

    # Ticks per frame (sequence meta)
    # Key frame (sequence meta)
    # Transfer peroid (sequence meta)
    # Mode (sequence meta)
    # Loop frame (sequence meta)
    # First Sound Tag (sequence meta)
    # Key Sound Tag (sequence meta)
    # Last Sound Tag (sequence meta)
    # Use Mirroring (sequence flag)
    # No Rotation (sequence flag)

    # Horizontal Mirror (bitmap instance flag)
    # Bitmap is 3D (bitmap instance flag: texture)
    # Vertical Mirror (bitmap instance flag)

    # Shadow is Light (shadow map flag)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 seqmeta.py <game_directory> [<tag_id> [<plugin_names> ...]]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    tag_id = None
    plugin_names = []
    if len(sys.argv) > 2:
        tag_id = sys.argv[2]
        if len(sys.argv) > 3:
            plugin_names = sys.argv[3:]

    try:
        main(game_directory, tag_id, plugin_names)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
