#!/usr/bin/env python3
import sys
import os
import struct

import myth_headers
import mesh_tag
import mono2tag
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, level, plugin_name):
    """
    Load Myth game tags and plugins and output header info for a mesh
    """
    (files, cutscenes) = loadtags.build_file_list(game_directory, plugin_name)
    (game_version, tags, entrypoint_map, data_map) = loadtags.build_tag_map(files)

    try:
        if level:
            for mesh_id in mesh_entries(level, entrypoint_map, tags):
                parse_mesh_tag(game_version, tags, data_map, mesh_id)
        else:
            for header_name, entrypoints in entrypoint_map.items():
                mono2tag.print_entrypoints(entrypoints, header_name)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def mesh_entries(level, entrypoint_map, tags):
    if level == 'all':
        for header_name, entrypoints in entrypoint_map.items():
            for mesh_id, (entry_name, entry_long_name) in entrypoints.items():
                print(f'mesh={mesh_id} file=[{header_name}] [{entry_name}] [{entry_long_name}]')
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
    print_header(mesh_header, mesh_id, locations)

def print_header(mesh_header, mesh_id, locations):
    mhd = mesh_header._asdict()
    for f in mesh_header._fields:
        val = mhd[f]
        if type(val) is bytes and myth_headers.all_off(val):
            val = f'[00 x {len(val.split(b'\x00'))-1}]'
        elif type(val) is bytes and myth_headers.all_on(val):
            val = f'[FF x {len(val.split(b'\xff'))-1}]'
        elif f.startswith('cutscene_file'):
            val = val.rstrip(b'\x00')
        print(f'{f:<42} {val}')
        # print(f'[{mesh_id}] {f} {val} {locations}')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mesh2info.py <game_directory> [<level> [plugin_name]]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    level = None
    plugin_name = None
    if len(sys.argv) > 2:
        level = sys.argv[2]
        if len(sys.argv) == 4:
            plugin_name = sys.argv[3]

    try:
        main(game_directory, level, plugin_name)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.exit(1)
