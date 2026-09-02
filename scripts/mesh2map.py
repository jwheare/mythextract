#!/usr/bin/env python3
import csv
import json
import pathlib
import sys
import os
import struct

import codec
import mesh_tag
import loadtags
import mesh2trades
import tag2png
import utils
import hashlib
import myth_collection

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, input_csv, output_dir):
    """
    Load Myth game tags and plugins and output header info for a mesh
    """
    if not output_dir:
        output_dir = pathlib.Path(sys.path[0], '../output/mesh2map')

    all_maps_out_path = output_dir / 'maps.json'
    all_maps_unseen = {}
    all_maps_seen = {}
    all_maps = []
    try:
        with open(all_maps_out_path, 'r') as maps_file_read:
            # Load and filter existing maps file
            for existing_map in json.load(maps_file_read):
                if existing_map['mesh_hash'] in all_maps_seen:
                    print('! filter', existing_map['mesh_dir'])
                else:
                    all_maps_unseen[existing_map['mesh_hash']] = True
                    all_maps_seen[existing_map['mesh_hash']] = True
                    all_maps.append(existing_map)
    except FileNotFoundError:
        pass

    with open(input_csv, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        for row in csvreader:
            if len(row) > 0:
                [mesh_id_name, *plugin_names] = row
                (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)
                if len(mesh_id_name) == 4:
                    mesh_id = mesh_id_name
                else:
                    mesh_id = None
                    for entry_id, entrypoint in entrypoint_map.items():
                        (entry_name, entry_long_name, archive_list) = entrypoint
                        if utils.strip_format(entry_long_name) == utils.strip_format(mesh_id_name):
                            mesh_id = entry_id
                    if not mesh_id:
                        print('! skip', row)
                        continue
                try:
                    (mesh_location, mesh_tag_header, mesh_tag_data) = loadtags.get_tag_info(
                        tags, data_map, 'mesh', mesh_id
                    )
                    mesh_hash = make_mesh_hash(mesh_tag_data, plugin_names)
                    if mesh_hash in all_maps_seen:
                        if mesh_hash in all_maps_unseen:
                            del all_maps_unseen[mesh_hash]
                        print('! seen', row)
                    else:
                        all_maps_seen[mesh_hash] = True
                        data = mesh_data(
                            mesh_id, mesh_hash, plugin_names,
                            mesh_tag_header, mesh_tag_data,
                            game_version, tags, data_map,
                            output_dir
                        )
                        all_maps.append({
                            k: v for k, v in data.items() if k in [
                                'name',
                                'mesh_id',
                                'mesh_name',
                                'mesh_slug',
                                'mesh_hash',
                                'mesh_dir',
                                'plugins',
                                'overhead_path',
                            ]
                        })
                except (struct.error, UnicodeDecodeError) as e:
                    raise ValueError(f"Error processing binary data: {e}")

    if len(all_maps_unseen):
        print(len(all_maps), len(all_maps_unseen))
        for all_map in all_maps:
            if all_map['mesh_hash'] in all_maps_unseen:
                print('! unseen', all_map['mesh_dir'])
        if prompt("Remove unseen maps from output?"):
            all_maps = [all_map for all_map in all_maps if all_map['mesh_hash'] not in all_maps_unseen]
            print(len(all_maps))

    with open(all_maps_out_path, 'w') as json_file:
        json.dump(all_maps, json_file, default=json_handler, separators=(',', ':'))
        print('+ export', all_maps_out_path)

def make_mesh_hash(mesh_tag_data, plugin_names):
    hash_content = mesh_tag_data
    if len(plugin_names) > 1:
        plugin_bin = b''.join([b'\0' + bytes(p, 'utf8') for p in plugin_names])
        hash_content += plugin_bin
    return hashlib.md5(hash_content).hexdigest()[:8]


def json_handler(o):
    if isinstance(o, codec.Simple):
        return o.decode()
    elif isinstance(o, codec._Codec):
        return o._asdict()
    elif hasattr(o, 'name'):
        return o.name
    else:
        return str(o)

def mesh_data(
    mesh_id, mesh_hash, plugin_names,
    mesh_tag_header, mesh_tag_data,
    game_version, tags, data_map,
    output_dir
):
    mesh_header = mesh_tag.parse_header(mesh_tag_data)
    level_name = mesh_tag.get_level_name(mesh_header, tags, data_map, strip_format=True)

    mesh_slug = utils.slugify(level_name, strip_bracketed=False)
    mesh_dir = f'maps/{mesh_id}-{mesh_hash}-{mesh_slug}'

    data = {
        'name': level_name,
        'mesh_id': mesh_id,
        'mesh_name': mesh_tag_header.name,
        'mesh_hash': mesh_hash,
        'mesh_slug': mesh_slug,
        'mesh_dir': mesh_dir,
        'plugins': [os.path.basename(p) for p in plugin_names],
    }

    width, height = mesh_tag.mesh_dimensions(mesh_header)
    data['width'] = width
    data['height'] = height

    data['lighting'] = {
        'light_color': codec.color_hex(mesh_header.light_color),
        'light_fraction': mesh_header.light_fraction,
        'dark_color': codec.color_hex(mesh_header.dark_color),
        'dark_fraction': mesh_header.dark_fraction,
        'transition_point': mesh_header.transition_point,
    }

    (palette, _) = mesh_tag.parse_markers(mesh_header, mesh_tag_data)
    all_units = mesh2trades.parse_units(
        game_version,
        tags, data_map, palette, mesh_header,
        data['name']
    )
    game_types = mesh_tag.enabled_netgames(mesh_header)
    game_types.sort()
    game_type_data = []
    data['units'] = mesh2trades.rekey_teams_all(mesh_header, all_units)
    for gt in game_types:
        locations = mesh_tag.netgame_locations(
            mesh_header, gt, palette, tags, data_map
        )
        filtered_locations = [loc for loc in locations if loc['team'] is None or loc['team'] in all_units]
        game_type_data.append({
            'game_type': gt,
            'game_type_long': mesh_tag.NetgameNames[gt],
            'locations': filtered_locations,
        })
    data['game_types'] = game_type_data

    output_path = output_dir / data['mesh_dir']
    output_path.mkdir(parents=True, exist_ok=True)

    (overhead_data, overhead_hash) = mesh_tag.export_overhead(tags, data_map, mesh_header)
    overhead_bitmaps = myth_collection.parse_sequence_bitmaps(overhead_data)
    overhead_path = f'img/overheads/overhead-{overhead_hash}.png'
    (
        overhead_name, overhead_width, overhead_height, overhead_rows
    ) = overhead_bitmaps[0]['bitmaps'][0]
    data['overhead_path'] = overhead_path
    overhead_out_path = output_dir / overhead_path
    overhead_out_path.parent.mkdir(parents=True, exist_ok=True)
    if not overhead_out_path.is_file():
        overhead_png = tag2png.make_png(overhead_width, overhead_height, overhead_rows)
        with open(overhead_out_path, 'wb') as overhead_png_file:
            overhead_png_file.write(overhead_png)
        print('+ export', overhead_out_path)
    else:
        print('! exists', overhead_out_path)

    (cmap_data, cmap_hash) = mesh_tag.export_colormap(tags, data_map, mesh_header)
    (cmap_width, cmap_height, cmap_rows, shadow_rows) = mesh_tag.assemble_colormap(mesh_header, cmap_data)
    cmap_path = f'img/cmaps/cmap-{cmap_hash}.png'
    shadow_path = f'img/shadow/shadow-{cmap_hash}.png'
    data['cmap_path'] = cmap_path
    data['shadow_path'] = shadow_path
    data['cmap_width'] = cmap_width
    data['cmap_height'] = cmap_height

    cmap_out_path = output_dir / cmap_path
    cmap_out_path.parent.mkdir(parents=True, exist_ok=True)
    if not cmap_out_path.is_file():
        cmap_png = tag2png.make_png(cmap_width, cmap_height, cmap_rows)
        with open(cmap_out_path, 'wb') as cmap_png_file:
            cmap_png_file.write(cmap_png)
        print('+ export', cmap_out_path)
    else:
        print('! exists', cmap_out_path)

    shadow_out_path = output_dir / shadow_path
    shadow_out_path.parent.mkdir(parents=True, exist_ok=True)
    if not shadow_out_path.is_file():
        shadow_png = tag2png.make_png(cmap_width, cmap_height, shadow_rows)
        with open(shadow_out_path, 'wb') as shadow_png_file:
            shadow_png_file.write(shadow_png)
        print('+ export', shadow_out_path)
    else:
        print('! exists', shadow_out_path)

    mesh_cells, mesh_cells_hash = mesh_tag.parse_mesh_cells(mesh_header, mesh_tag_data)
    (terrain_width, terrain_height, terrain_rows) = mesh_tag.export_terrain(mesh_cells)
    terrain_path = f'img/terrain/terrain-{mesh_cells_hash}.png'
    data['terrain_path'] = terrain_path

    terrain_out_path = output_dir / terrain_path
    terrain_out_path.parent.mkdir(parents=True, exist_ok=True)
    if not terrain_out_path.is_file():
        terrain_png = tag2png.make_png(terrain_width, terrain_height, terrain_rows)
        with open(terrain_out_path, 'wb') as terrain_png_file:
            terrain_png_file.write(terrain_png)
        print('+ export', terrain_out_path)
    else:
        print('! exists', terrain_out_path)

    (scen, scen_hash) = mesh_tag.impassable_scenery(mesh_header, palette, tags, data_map)
    (scen_width, scen_height, scen_rows) = mesh_tag.export_impassable_scenery(mesh_cells, scen)
    scen_path = f'img/scen/scen-{scen_hash}.png'
    data['impassable_scenery_path'] = scen_path

    scen_out_path = output_dir / scen_path
    scen_out_path.parent.mkdir(parents=True, exist_ok=True)
    if not scen_out_path.is_file():
        scen_png = tag2png.make_png(scen_width, scen_height, scen_rows)
        with open(scen_out_path, 'wb') as scen_png_file:
            scen_png_file.write(scen_png)
        print('+ export', scen_out_path)
    else:
        print('! exists', scen_out_path)

    max_height, min_height, height_range = mesh_tag.cell_height_range(mesh_cells)
    height_path = f'img/height/height-{mesh_cells_hash}.png'
    data['height_path'] = height_path
    data['max_height'] = max_height
    data['min_height'] = min_height
    data['height_range'] = height_range
    (height_width, height_height, height_rows) = mesh_tag.export_terrain_height(mesh_cells)

    height_out_path = output_dir / height_path
    height_out_path.parent.mkdir(parents=True, exist_ok=True)
    if not height_out_path.is_file():
        height_png = tag2png.make_png(height_width, height_height, height_rows)
        with open(height_out_path, 'wb') as height_png_file:
            height_png_file.write(height_png)
        print('+ export', height_out_path)
    else:
        print('! exists', height_out_path)

    data_out_path = output_path / 'data.json'
    with open(data_out_path, 'w') as json_file:
        json.dump(data, json_file, default=json_handler, separators=(',', ':'))
        print('+ export', data_out_path)
    return data

def prompt(message):
    response = input(f"{message} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: python3 {sys.argv[0]} <game_directory> <input_csv> [<output_dir>]")
        sys.exit(1)
    
    game_directory = sys.argv[1]
    input_csv = sys.argv[2]

    output_dir = None
    if len(sys.argv) > 3:
        output_dir = pathlib.Path(sys.argv[3])

    try:
        main(game_directory, input_csv, output_dir)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
