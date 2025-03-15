#!/usr/bin/env python3
import sys
import os
import struct

import myth_headers
import myth_collection
import mesh_tag
import mesh2info
import mono2tag
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, level, plugin_names):
    """
    Load Myth game tags and plugins and output markers for a mesh
    """
    (files, cutscenes) = loadtags.build_file_list(game_directory, plugin_names)
    (game_version, tags, entrypoint_map, data_map) = loadtags.build_tag_map(files)

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

def check_unit_collection_mismatch(tags, data_map, tag_type, tag_id):
    if tag_type == 'unit':
        (unit_location, unit_header, unit_tag_data) = loadtags.get_tag_info(tags, data_map, tag_type, tag_id)

        if unit_tag_data:
            mons_tag_id = myth_headers.decode_string(unit_tag_data[64:68])
            (mons_location, mons_header, mons_data) = loadtags.get_tag_info(tags, data_map, 'mons', mons_tag_id)
            mons_coll = None
            if mons_data:
                mons_coll = myth_headers.decode_string(mons_data[68:72])

            core_tag_id = myth_headers.decode_string(unit_tag_data[68:72])
            (core_location, core_header, core_data) = loadtags.get_tag_info(tags, data_map, 'core', core_tag_id)
            core_coll = None
            if core_data:
                core_tag = myth_collection.parse_collection_ref(core_data[64:])
                core_coll = core_tag.collection_tag

            if mons_coll and core_coll and mons_coll != core_coll:
                (mons_coll_location, mons_coll_header) = loadtags.lookup_tag_header(tags, '.256', mons_coll)
                (core_coll_location, core_coll_header) = loadtags.lookup_tag_header(tags, '.256', core_coll)
                return (tag_type, unit_header, unit_location, tag_id, [
                    ('mons', mons_header, mons_location, mons_tag_id, [
                        ('.256', mons_coll_header, mons_coll_location, mons_coll, [])
                    ]),
                    ('core', core_header, core_location, core_tag_id, [
                        ('.256', core_coll_header, core_coll_location, core_coll, [])
                    ])
                ])

def print_markers(mesh_tag_location, mesh_tag_header, tags, data_map, palette, orphans):
    mismatched_unit_collections = {}
    for palette_type, p_list in palette.items():
        for palette_index, p_val in enumerate(p_list):
            tag_id = p_val['tag']
            tag_type = mesh_tag.Marker2Tag.get(palette_type)
            (location, tag_header) = loadtags.lookup_tag_header(tags, tag_type, tag_id)
            mismatch_tree = check_unit_collection_mismatch(tags, data_map, tag_type, tag_id)
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
                f'count={p_val['_unreliable_count']}? '
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

    if len(mismatched_unit_collections):
        print(
            f'Mismatched collections: {mesh_tag_header.tag_id} {mesh_tag_header.name} {mesh_tag_location}',
            mismatched_unit_collections.keys()
        )
        for unit_tag, mismatch_tree in mismatched_unit_collections.items():
            traverse_mismatch_tree(*mismatch_tree)

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

def traverse_mismatch_tree(tag_type, tag_header, location, tag_id, children, depth=0):
    print(f'{' '*depth}- {tag_type}.{tag_id} [{tag_header.name if tag_header else None}] ({location})')
    for child in children:
        traverse_mismatch_tree(*child, depth=depth+1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mesh2markers.py <game_directory> [<level> [<plugin_names> ...]]")
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
