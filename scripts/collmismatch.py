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
    log_mismatches(mesh_tag_location, mesh_tag_header, tags, data_map, palette, orphans)

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
                core_tag = myth_collection.parse_collection_ref(core_data)
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

def log_mismatches(mesh_tag_location, mesh_tag_header, tags, data_map, palette, orphans):
    mismatched_unit_collections = {}
    for palette_type, p_list in palette.items():
        for palette_index, p_val in enumerate(p_list):
            tag_id = p_val['tag']
            tag_type = mesh_tag.Marker2Tag.get(palette_type)
            (location, tag_header) = loadtags.lookup_tag_header(tags, tag_type, tag_id)
            mismatch_tree = check_unit_collection_mismatch(tags, data_map, tag_type, tag_id)
            if mismatch_tree:
                mismatched_unit_collections[tag_id] = mismatch_tree

    print_mismatches(mismatched_unit_collections, mesh_tag_header, mesh_tag_location)

def print_mismatches(mismatched_unit_collections, mesh_tag_header, mesh_tag_location):
    if len(mismatched_unit_collections):
        print(
            f'Mismatched collections: {mesh_tag_header.tag_id} {mesh_tag_header.name} {mesh_tag_location}',
            mismatched_unit_collections.keys()
        )
        for unit_tag, mismatch_tree in mismatched_unit_collections.items():
            traverse_mismatch_tree(*mismatch_tree)

def traverse_mismatch_tree(tag_type, tag_header, location, tag_id, children, depth=0):
    print(f'{' '*depth}- {tag_type}.{tag_id} [{tag_header.name if tag_header else None}] ({location})')
    for child in children:
        traverse_mismatch_tree(*child, depth=depth+1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 collmismatch.py <game_directory> [<level> [<plugin_names> ...]]")
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
