#!/usr/bin/env python3
import sys
import os
import pathlib
import struct
import signal

import myth_headers
import mesh_tag
import mesh2info
import mono2tag
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')
signal.signal(signal.SIGPIPE, signal.SIG_DFL)

def main(game_directory, level, plugin_name):
    """
    Parse a Myth II mesh tag file removes extra data from actions buffer
    """
    files = loadtags.build_file_list(game_directory, plugin_name)
    (tags, entrypoint_map, data_map) = loadtags.build_tag_map(files)

    try:
        if level:
            (mesh_id, header_name, entry_name, entry_long_name) = mesh2info.parse_level(level, entrypoint_map)
            print(f'mesh={mesh_id} file=[{header_name}] [{entry_name}] [{entry_long_name}]')
            mesh_tag_data = loadtags.get_tag_data(tags, data_map, 'mesh', mesh_id)
            fix_mesh_actions(mesh_tag_data)
        else:
            for header_name, entrypoints in entrypoint_map.items():
                mono2tag.print_entrypoints(entrypoints, header_name)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def fix_mesh_actions(mesh_tag_data):
    mesh_header = mesh_tag.parse_header(mesh_tag_data)
    tag_header = myth_headers.parse_header(mesh_tag_data)

    (actions, action_remainder) = mesh_tag.parse_map_actions(mesh_header, mesh_tag_data)
    remainder_size = len(action_remainder)

    print('remaining action data', remainder_size)

    if remainder_size:
        # Fix sizes and offsets
        map_action_start = mesh_tag.get_offset(mesh_header.map_actions_offset)
        map_action_end = map_action_start + remainder_size

        fixed_data = mesh_tag_data[:map_action_start] + mesh_tag_data[map_action_end:]

        fixed_data_size = mesh_header.data_size - remainder_size
        fixed_map_action_buffer_size = mesh_header.map_action_buffer_size - remainder_size
        fixed_media_coverage_region_offset = mesh_header.media_coverage_region_offset - remainder_size
        fixed_mesh_LOD_data_offset = mesh_header.mesh_LOD_data_offset - remainder_size
        fixed_connectors_offset = mesh_header.connectors_offset - remainder_size

        fixed_mesh_header = mesh_header._replace(
            data_size=fixed_data_size,
            map_action_buffer_size=fixed_map_action_buffer_size,
            media_coverage_region_offset=fixed_media_coverage_region_offset,
            mesh_LOD_data_offset=fixed_mesh_LOD_data_offset,
            connectors_offset=fixed_connectors_offset,
        )

        # Fix tag header size
        fixed_tag_data_size = tag_header.tag_data_size - remainder_size
        fixed_tag_header = tag_header._replace(
            destination=-1,
            identifier=-1,
            type=0,
            tag_data_size=fixed_tag_data_size
        )

        fixed_tag_data = (
            myth_headers.encode_header(fixed_tag_header)
            + mesh_tag.encode_header(fixed_mesh_header)
            + fixed_data[mesh_tag.get_offset(0):]
        )

        print(
            f"""Updated tag values
                tag_header.tag_data_size = {tag_header.tag_data_size} -> {fixed_tag_header.tag_data_size}
                   mesh_header.data_size = {mesh_header.data_size} -> {fixed_mesh_header.data_size}
      mesh_header.map_action_buffer_size = {mesh_header.map_action_buffer_size} -> {fixed_mesh_header.map_action_buffer_size}
mesh_header.media_coverage_region_offset = {mesh_header.media_coverage_region_offset} -> {fixed_mesh_header.media_coverage_region_offset}
        mesh_header.mesh_LOD_data_offset = {mesh_header.mesh_LOD_data_offset} -> {fixed_mesh_header.mesh_LOD_data_offset}
           mesh_header.connectors_offset = {mesh_header.connectors_offset} -> {fixed_mesh_header.connectors_offset}"""
        )

        fixed_path = pathlib.Path(sys.path[0], f'../output/fixed_mesh_actions/meshes/{tag_header.name}').resolve()
        if prompt(fixed_path):
            pathlib.Path(fixed_path.parent).mkdir(parents=True, exist_ok=True)
            with open(fixed_path, 'wb') as fixed_tag_file:
                fixed_tag_file.write(fixed_tag_data)

def prompt(prompt_path):
    # return True
    response = input(f"Write to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fixmeshactions.py <game_directory> [<level> [plugin_name]]")
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
