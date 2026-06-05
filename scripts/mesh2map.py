#!/usr/bin/env python3
import json
import pathlib
import shutil
import sys
import os
import struct

import mesh_tag
import mono2tag
import loadtags
import mesh2info
import mesh2trades
import tag2png

DEBUG = (os.environ.get('DEBUG') == '1')
GAME_TYPE = os.environ.get('GAME_TYPE')
DIFFICULTY = int(os.environ.get('DIFFICULTY', 2))

def main(game_directory, level, plugin_names):
    """
    Load Myth game tags and plugins and output header info for a mesh
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    try:
        if not level or level == 'list':
            mono2tag.print_entrypoint_map(entrypoint_map, plugin_names=plugin_names)
            mesh_input = input('Choose a mesh id: ')
            main(game_directory, f'mesh={mesh_input}', plugin_names)
        else:
            for mesh_id in mesh2info.mesh_entries(game_version, level, entrypoint_map, tags, plugin_names):
                parse_mesh_tag(game_version, tags, data_map, mesh_id, plugin_names)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def parse_mesh_tag(game_version, tags, data_map, mesh_id, plugin_names):
    mesh_tag_data = loadtags.get_tag_data(tags, data_map, 'mesh', mesh_id)

    mesh_header = mesh_tag.parse_header(mesh_tag_data)

    level_name = mesh_tag.get_level_name(mesh_header, tags, data_map, strip_format=True)

    (palette, _) = mesh_tag.parse_markers(mesh_header, mesh_tag_data)

    game_types, game_type_units = mesh2trades.parse_game_type_units(
        game_version,
        tags, data_map, palette, mesh_header,
        level_name, DIFFICULTY, GAME_TYPE
    )

    width, height = mesh_tag.mesh_dimensions(mesh_header)
    data = {
        'width': width,
        'height': height,
        'name': level_name,
        'mesh_id': mesh_id,
        'plugins': [os.path.basename(p) for p in plugin_names],
    }
    game_type_data = []
    for gt in game_types:
        if 'all' in game_type_units or gt in game_type_units:
            locations = mesh_tag.netgame_locations(
                mesh_header, gt, DIFFICULTY, palette, tags, data_map
            )
            gtu = game_type_units.get('all', game_type_units.get(gt))
            filtered_locations = [loc for loc in locations if loc['team'] is None or loc['team'] in gtu]
            game_type_data.append({
                'game_type': gt,
                'game_type_long': mesh_tag.NetgameNames[gt],
                'locations': filtered_locations,
            })
    data['game_types'] = game_type_data

    output_dir = f'../output/mesh2map/{mesh_id} {level_name}'
    output_path = pathlib.Path(sys.path[0], output_dir).resolve()

    if prompt(output_path):
        output_path.mkdir(parents=True, exist_ok=True)

        cmap_out_path = output_path / 'cmap.png'
        (cmap_data, cmap_hash) = mesh_tag.export_colormap(tags, data_map, mesh_header)
        (cmap_width, cmap_height, cmap_rows) = mesh_tag.assemble_colormap(mesh_header, cmap_data)
        data['cmap_width'] = cmap_width
        data['cmap_height'] = cmap_height
        if not cmap_out_path.is_file():
            cmap_png = tag2png.make_png(cmap_width, cmap_height, cmap_rows)
            with open(cmap_out_path, 'wb') as png_file:
                png_file.write(cmap_png)
            print('+ export', cmap_out_path)
        else:
            print('! exists', cmap_out_path)

        data_out_path = output_path / 'data.json'
        with open(data_out_path, 'w') as json_file:
            json.dump(data, json_file, indent=2)
            print('+ export', data_out_path)

        html_file = 'mesh2map.html'
        html_path = pathlib.Path(sys.path[0], '../mesh2map').resolve() / html_file
        shutil.copy2(html_path, output_path)
        print('+ export', (output_path / html_file))

def prompt(prompt_path):
    # return True
    response = input(f"Write to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

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
