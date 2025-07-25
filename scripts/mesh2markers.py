#!/usr/bin/env python3
import sys
import os
import struct

import mesh_tag
import mesh2info
import mono2tag
import loadtags
import collmismatch

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, level, plugin_names):
    """
    Load Myth game tags and plugins and output markers for a mesh
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    try:
        if level:
            for mesh_id in mesh2info.mesh_entries(game_version, level, entrypoint_map, tags, plugin_names):
                parse_mesh_markers(game_version, tags, data_map, mesh_id)
        else:
            mono2tag.print_entrypoint_map(entrypoint_map)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def parse_mesh_markers(game_version, tags, data_map, mesh_id):
    (mesh_tag_location, mesh_tag_header, mesh_tag_data) = loadtags.get_tag_info(tags, data_map, 'mesh', mesh_id)
    mesh_header = mesh_tag.parse_header(mesh_tag_data)

    (palette, orphans) = mesh_tag.parse_markers(mesh_header, mesh_tag_data)
    print_markers(mesh_tag_location, mesh_tag_header, tags, data_map, palette, orphans)

def print_markers(mesh_tag_location, mesh_tag_header, tags, data_map, palette, orphans):
    mismatched_unit_collections = {}
    for palette_type, p_list in palette.items():
        for palette_index, p_val in enumerate(p_list):
            tag_id = p_val['tag']
            tag_type = mesh_tag.Marker2Tag.get(palette_type)
            (location, tag_header) = loadtags.lookup_tag_header(tags, tag_type, tag_id)
            mismatch_tree = collmismatch.check_unit_collection_mismatch(tags, data_map, tag_type, tag_id)
            if mismatch_tree:
                mismatched_unit_collections[tag_id] = mismatch_tree
            tag_header_print = f'[{tag_header.name}] ' if tag_header else ''
            flag_info = mesh_tag.palette_flag_info(p_val['flags'])
            flags = f'(flags={'/'.join(flag_info)}) ' if len(flag_info) else ''
            netgame_info = mesh_tag.netgame_flag_info(p_val['netgame_flags'])
            netgame = f'(netgame={'/'.join(netgame_info)}) ' if len(netgame_info) else ''
            print(
                f'{palette_type} {palette_index:<2} '
                f'[{tag_id}] {tag_header_print}'
                f'team={p_val['team_index']} '
                f'{flags}'
                f'{netgame}'
            )

            for marker_id, marker in p_val['markers'].items():

                flag_info = mesh_tag.marker_flag_info(marker['flags'])
                flags = f'(flags={'/'.join(flag_info)}) ' if len(flag_info) else ''

                difficulty = f'(diff={mesh_tag.difficulty(marker['min_difficulty']).lower()}) ' if marker['min_difficulty'] else ''
                print(
                    f'{palette_type} {palette_index:<2} '
                    f'[{tag_id}] {tag_header_print}'
                    f'- {marker_id:<5} '
                    f'{flags}'
                    f'{difficulty}'
                    f'facing={marker['facing']:06.2f} '
                    f'pos={[round(po, 2) for po in marker['pos']]} '
                )
            print('-')

    collmismatch.print_mismatches(mismatched_unit_collections, mesh_tag_header, mesh_tag_location)

    if orphans['count']:
        print('---')
        print('ORPHANS')
        for marker_type, type_orphans in orphans['markers'].items():
            if len(type_orphans):
                for marker_id, orphan_info in type_orphans.items():
                    print(
                        f'O.{marker_type} {orphan_info['palette_index']:<2} - '
                        f'- {marker_id:<5} '
                        # f'flags={orphan_info['flags']} '
                        f'min_diff={orphan_info['min_difficulty']} '
                        # f'facing={orphan_info['facing']:06.2f} '
                        # f'pos={[round(po, 2) for po in orphan_info['pos']]} '
                    )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <game_directory> [<level> [<plugin_names> ...]]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    level = None
    plugin_names = []
    if len(sys.argv) > 2:
        level = sys.argv[2]
        if len(sys.argv) > 3:
            plugin_names = sys.argv[3:]

    try:
        main(game_directory, level, plugin_names)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
