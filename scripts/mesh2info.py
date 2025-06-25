#!/usr/bin/env python3
import sys
import os
import struct

import mesh_tag
import mono2tag
import loadtags
import utils

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, level, plugin_names):
    """
    Load Myth game tags and plugins and output header info for a mesh
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    try:
        if level:
            for mesh_id in mesh_entries(game_version, level, entrypoint_map, tags, plugin_names):
                parse_mesh_tag(game_version, tags, data_map, mesh_id)
        else:
            mono2tag.print_entrypoint_map(entrypoint_map)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def mesh_entries(game_version, level, entrypoint_map, tags, plugin_names):
    if level == 'all':
        if game_version == 1:
            for level in range(1, 26):
                (mesh_id, header_name, entry_name) = parse_level(f'{level:02}', tags)
                print(f'mesh={mesh_id} file=[{header_name}] [{entry_name}]')
                yield mesh_id
        else:
            for mesh_id, (entry_name, entry_long_name, archive_list) in entrypoint_map.items():
                if not plugin_names or bool(set(plugin_names) & set(archive_list)):
                    print(f'mesh={mesh_id} archives=[{archive_list}] [{entry_name}] [{entry_long_name}]')
                    yield mesh_id
    else:
        (mesh_id, header_name, entry_name) = parse_level(level, tags)
        print(f'mesh={mesh_id} file=[{header_name}] [{entry_name}]')
        yield mesh_id

def parse_level(level, tags):
    ret = None
    level_mesh = level[5:] if level.startswith('mesh=') else None
    if level_mesh:
        if level_mesh in tags['mesh']:
            latest = tags['mesh'][level_mesh][-1]
            ret = (level_mesh, latest[0], latest[1].name)
    else:
        for mesh_id, tag_headers in tags['mesh'].items():
            latest = tag_headers[-1]
            if latest[1].name.startswith(f'{level} '):
                ret = (mesh_id, latest[0], latest[1].name)
    if ret:
        return ret
    else:
        print("Invalid level")
        sys.exit(1)

def parse_mesh_tag(game_version, tags, data_map, mesh_id):
    mesh_tag_data = loadtags.get_tag_data(tags, data_map, 'mesh', mesh_id)

    mesh_header = mesh_tag.parse_header(mesh_tag_data)
    
    locations = [l for (l, th) in tags['mesh'][mesh_id]]

    # print(mesh_id, mesh_header.mesh_size)

    print('data len', len(mesh_tag_data))
    print_header(mesh_header, mesh_id, locations)

def print_header(mesh_header, mesh_id, locations):
    for i, (f, val) in enumerate(mesh_header._asdict().items()):
        print(f'{f:<42} {utils.val_repr(val)}')
        # print(f'[{mesh_id}] {f} {val} {locations}')

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
