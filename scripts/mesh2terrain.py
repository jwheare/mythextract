#!/usr/bin/env python3
import sys
import os
import pathlib
import struct

import utils
import mesh2info
import mesh_tag
import mono2tag
import myth_headers
import loadtags
import tag2png

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, level, plugin_names):
    """
    Load Myth game tags and plugins and output terrain map for a mesh
    """
    output_dir = pathlib.Path(sys.path[0], '../output/mesh2terrain/').resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # make_legend(output_dir)

    try:
        if level == 'file' and len(plugin_names) == 1:
            export_mesh_terrain_file(output_dir, plugin_names[0])
        else:
            (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)
            if not level or level == 'list':
                mono2tag.print_entrypoint_map(entrypoint_map, plugin_names=plugin_names)
                mesh_input = input('Choose a mesh id: ')
                main(game_directory, f'mesh={mesh_input}', plugin_names)
            else:
                for mesh_id in mesh2info.mesh_entries(game_version, level, entrypoint_map, tags, plugin_names):
                    export_mesh_terrain_tag(output_dir, tags, data_map, mesh_id)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def make_legend(output_dir):
    swatch_width = 50
    swatch_height = 50
    backing_width = 500
    total_width = swatch_width + backing_width
    total_height = 0
    rows = []
    white = (255,255,255,255)
    for flag, rgb in mesh_tag.MeshCellTerrainColors.items():
        r, g, b = rgb
        rgba = (r,g,b,255)
        print(flag.name, rgba)
        for r in range(swatch_height):
            rows.append([rgba] * swatch_height + [white] * backing_width)
        total_height += swatch_height
    legend_png = tag2png.make_png(total_width, total_height, rows)
    output_path = output_dir / 'legend_template.png'
    with open(output_path, 'wb') as png_file:
        png_file.write(legend_png)

def export_mesh_terrain_file(output_dir, tag_file):
    mesh_tag_data = utils.load_file(tag_file)
    export_mesh_terrain(mesh_tag_data, output_dir)

def export_mesh_terrain_tag(output_dir, tags, data_map, mesh_id):
    mesh_tag_data = loadtags.get_tag_data(tags, data_map, 'mesh', mesh_id)
    mesh_header = mesh_tag.parse_header(mesh_tag_data)
    level_name = mesh_tag.get_level_name(mesh_header, tags, data_map, strip_format=True)
    slug_suffix = f'-{level_name}'

    export_mesh_terrain(mesh_tag_data, output_dir, slug_suffix)

def export_mesh_terrain(mesh_tag_data, output_dir, slug_suffix=''):
    tag_header = myth_headers.parse_header(mesh_tag_data)
    mesh_id = tag_header.tag_id
    mesh_slug = f'{tag_header.name}-{mesh_id}{slug_suffix}'
    mesh_header = mesh_tag.parse_header(mesh_tag_data)
    mesh_cells, mesh_cells_hash = mesh_tag.parse_mesh_cells(mesh_header, mesh_tag_data)
    print('hash', mesh_cells_hash)
    mesh_output_dir = output_dir / mesh_slug
    mesh_output_dir.mkdir(parents=True, exist_ok=True)
    
    for exporter, suffix in [
        (mesh_tag.export_terrain, 'terrain'),
        (mesh_tag.export_media_coverage, 'media'),
        (mesh_tag.export_terrain_height, 'height'),
        (mesh_tag.export_media_height, 'media-height'),
        (mesh_tag.export_terrain_below_media, 'terrain-below-media'),
    ]:
        (width, height, rows) = exporter(mesh_cells)
        output_path = mesh_output_dir / f'{mesh_slug}-{suffix}.png'
        output_png = tag2png.make_png(width, height, rows)
        with open(output_path, 'wb') as png_file:
            print(output_path)
            png_file.write(output_png)
    
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
