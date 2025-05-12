#!/usr/bin/env python3
import json
import os
import pathlib
import re
import shutil
from string import Template
import struct
import subprocess
import sys
import time

import myth_headers
import myth_collection
import mesh_tag
import myth_sound
import tag2png
import mono2tag
import mesh2info
import loadtags
import utils

DEBUG = (os.environ.get('DEBUG') == '1')
TIME = (os.environ.get('TIME') == '1')

def load_file(path):
    t = time.perf_counter()
    data = utils.load_file(path)
    TIME and print(path, f'{(time.perf_counter() - t):.3f}')

    return data

def main(game_directory, level, plugin_name, plugin_output):
    """
    Load Myth game tags and plugins and output a web page for the intro to a mesh
    """
    (game_version, tags, entrypoint_map, data_map, cutscene_paths) = loadtags.load_tags(game_directory, [plugin_name])

    try:
        if level:
            if game_version == 2 and level == 'all':
                for mesh_id, (entry_name, entry_long_name, archive_list) in entrypoint_map.items():
                    if not plugin_name or plugin_name in archive_list:
                        if DEBUG:
                            print(f'mesh={mesh_id} file=[{archive_list}] [{entry_name}] [{entry_long_name}]')
                        plugin = plugin_name if plugin_name in archive_list else None
                        extract_level(game_version, tags, data_map, cutscene_paths, mesh_id, plugin, plugin_output)
                if not plugin_name:
                    extract_sb_epilogue(tags, data_map, cutscene_paths)
            elif game_version == 1 and level == 'all':
                for level in range(1, 26):
                    (mesh_id, header_name, entry_name) = mesh2info.parse_level(f'{level:02}', tags)
                    if DEBUG:
                        print(f'level={level} mesh={mesh_id} file=[{header_name}] [{entry_name}]')
                    plugin = None
                    extract_level(game_version, tags, data_map, cutscene_paths, mesh_id, plugin, plugin_output)
            elif game_version == 2 and not plugin_name and level == 'epilogue':
                extract_sb_epilogue(tags, data_map, cutscene_paths)
            else:
                (mesh_id, header_name, entry_name) = mesh2info.parse_level(level, tags)
                if DEBUG:
                    print(f'level={level} mesh={mesh_id} file=[{header_name}] [{entry_name}]')
                plugin = plugin_name if plugin_name == header_name else None
                extract_level(game_version, tags, data_map, cutscene_paths, mesh_id, plugin, plugin_output)
        else:
            mono2tag.print_entrypoint_map(entrypoint_map)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def extract_sb_epilogue(tags, data_map, cutscene_paths):
    prefix = 'myth2'
    game_version = 2
    version_class = 'sb epilogue'
    level = 'epilogue'
    level_name = 'Epilogue'
    caption_data = None
    next_level = None
    plugin = None
    pregame_list = []

    storyline_data = loadtags.get_tag_data(tags, data_map, 'text', 'epil')
    sound_data = loadtags.get_tag_data(tags, data_map, 'soun', 'naep')
    initial_delay = 0
    scroll_rate = 7.6923

    # Extract art
    (background, colors) = extract_epilogue_collection(loadtags.get_tag_data(tags, data_map, '.256', 'inge'))
    art_dicts = [('background', {
        "shared": background
    })]
    bg_initial_path = f'./background/{level}-background-shared.png'
    bg_narration_path = bg_initial_path

    cutscenes = cutscenes2paths(('epilogue', None), cutscene_paths)

    output_html(
        game_version, plugin,
        storyline_data, sound_data, colors, caption_data, pregame_list, art_dicts,
        bg_initial_path, bg_narration_path,
        prefix, version_class, level, level_name, next_level,
        initial_delay, scroll_rate, cutscenes
    )

def cutscenes2paths(cutscenes, cutscene_paths):
    paths = []
    for cutscene in cutscenes:
        if not cutscene:
            cutscene_path = None
        elif cutscene.endswith('.smk'):
            cutscene_path = cutscene_paths.get(f'{cutscene[:-4]}.mov')
        elif cutscene.endswith('.mov'):
            cutscene_paths.get(cutscene)
        else:
            cutscene_path = cutscene_paths.get(f'{cutscene}.mov')
        paths.append(cutscene_path)
    return paths

def extract_level(game_version, tags, data_map, cutscene_paths, mesh_id, plugin, plugin_output):
    mesh_tag_data = loadtags.get_tag_data(tags, data_map, 'mesh', mesh_id)
    tag_header = myth_headers.parse_header(mesh_tag_data)
    level = tag_header.name.split(' ')[0]

    mesh_header = mesh_tag.parse_header(mesh_tag_data)

    if plugin:
        prefix = plugin_output or plugin
    elif game_version == 2:
        prefix = 'myth2'
    elif game_version == 1:
        prefix = 'myth'
    else:
        prefix = 'unknown'

    if game_version == 1 or mesh_tag.is_vtfl(mesh_header):
        version_class = 'tfl'
    else:
        version_class = 'sb'

    if not mesh_tag.has_single_player_story(game_version, mesh_tag_data):
        if DEBUG:
            print('skip, no single player story', game_version, mesh_id, level, plugin)
        return

    if game_version == 1:
        cutscene_tag_pregame = mesh_header.cutscene_tag_pregame
    else:
        cutscene_tag_pregame = mesh_header.cutscene_file_pregame
    cutscenes = cutscenes2paths((None, utils.decode_string(cutscene_tag_pregame)), cutscene_paths)

    next_level = None
    next_entry_data = loadtags.get_tag_data(tags, data_map, 'mesh', utils.decode_string(mesh_header.next_mesh_alternate))
    if not next_entry_data or not mesh_tag.has_single_player_story(game_version, next_entry_data):
        next_entry_data = loadtags.get_tag_data(tags, data_map, 'mesh', utils.decode_string(mesh_header.next_mesh))
    if next_entry_data and mesh_tag.has_single_player_story(game_version, next_entry_data):
        next_header = myth_headers.parse_header(next_entry_data)
        next_level = next_header.name.split(' ')[0]
    elif not plugin and version_class == 'sb':
        next_level = 'epilogue'

    # Extract narration text
    storyline_data = loadtags.get_tag_data(
        tags, data_map, 'text', utils.decode_string(mesh_header.pregame_storyline_tag)
    )

    # Extract sound data
    sound_data = loadtags.get_tag_data(
        tags, data_map, 'soun', utils.decode_string(mesh_header.narration_sound_tag)
    )
    initial_delay = 5000
    scroll_rate = 10

    # Extract level name
    desc_data = loadtags.get_tag_data(
        tags, data_map, 'stli', utils.decode_string(mesh_header.map_description_string_list_tag)
    )
    (_, desc_text) = myth_headers.parse_text_tag(desc_data)
    level_name = utils.decode_string(desc_text.split(b'\r')[0])

    # Extract pregame captions
    caption_data = loadtags.get_tag_data(
        tags, data_map, 'stli', utils.decode_string(mesh_header.picture_caption_string_list_tag)
    )
    
    # Extract pregame art
    pregame_data = loadtags.get_tag_data(
        tags, data_map, '.256', utils.decode_string(mesh_header.pregame_collection_tag)
    )
    pregame_list = []
    map_dict = {}
    colors = None
    if pregame_data:
        (pregame_list, map_dict, colors) = extract_pregame(pregame_data)

    # Extract postgame art
    postgame_data = loadtags.get_tag_data(
        tags, data_map, '.256', utils.decode_string(mesh_header.postgame_collection_tag)
    )
    postgame_dict = {}
    if postgame_data:
        postgame_dict = extract_postgame(postgame_data)

    art_dicts = [('map', map_dict), ('postgame', postgame_dict)]
    bg_initial_path = f'./map/{level}-map-light.png'
    bg_narration_path = f'./map/{level}-map-dark.png'

    output_html(
        game_version, plugin,
        storyline_data, sound_data, colors, caption_data, pregame_list, art_dicts,
        bg_initial_path, bg_narration_path,
        prefix, version_class, level, level_name, next_level,
        initial_delay, scroll_rate, cutscenes
    )

def output_html(
    game_version, plugin,
    storyline_data, sound_data, colors, caption_data, pregame_list, art_dicts,
    bg_initial_path, bg_narration_path,
    prefix, version_class, level, level_name, next_level,
    initial_delay, scroll_rate, cutscenes
):
    # Extract text colors
    heading_color = (255,255,255,255)
    narration_color = (255,255,255,255)
    if colors:
        (_, _, _, [[heading_color, narration_color, color3]]) = colors

    # Extract narration audio
    aifc = None
    if sound_data:
        (_, _, permutations) = myth_sound.parse_soun_tag(sound_data)
        aifc = myth_sound.generate_aifc(permutations[0])

    # Generate intro html
    intro_html = ''
    if storyline_data:
        (_, intro_text) = myth_headers.parse_text_tag(storyline_data)
        intro_html = text2html(intro_text)

    # Extract caption
    caption = ''
    if caption_data:
        (_, caption_text) = myth_headers.parse_text_tag(caption_data)
        caption = utils.decode_string(caption_text.split(b'\r')[0])

    output_dir = '../output/archive/'
    root_path = pathlib.Path(sys.path[0], output_dir).resolve()

    static_prefix = '../../../'

    stylesheets = []
    for style, media in [('font', 'all'), ('screen', 'screen'), ('print', 'print')]:
        style_path = f'{static_prefix}style/{style}.css'
        stylesheets.append(f'<link rel="stylesheet" href="{style_path}" media="{media}">')

    script_path = f'{static_prefix}script.js'
    output_path = root_path / f'{prefix}/level/{level}'

    if prompt(output_path):
        output_path.mkdir(parents=True, exist_ok=True)

        if aifc:
            aifc_path = output_path / f'{level}.aifc'
            with open(aifc_path, 'wb') as aifc_file:
                aifc_file.write(aifc)

            convert_mp3(aifc_path)
            aifc_path.unlink()

        pregame_imgs = []
        durations = []
        max_pregame_height = 0
        (output_path / 'pregame').mkdir(parents=True, exist_ok=True)

        for i, (dur, (_name, width, height, rows)) in enumerate(pregame_list):
            max_pregame_height = max(max_pregame_height, height)
            png_path = f'./pregame/{level}-pregame-{i}.png'
            png_class = f'pregame pregame-{i}'
            if i == 0:
                png_class = f'{png_class} pregame--show'
            pregame_imgs.append(f'<img alt="" class="{png_class}" src="{png_path}" width="{width}" height="{height}">')
            if game_version == 2 and not plugin:
                durations.append(dur)
            write_png(width, height, rows, output_path, png_path)

        for art_type, art_dict in art_dicts:
            (output_path / art_type).mkdir(parents=True, exist_ok=True)
            for art_name, (_name, width, height, rows) in art_dict.items():
                png_path = f'./{art_type}/{level}-{art_type}-{art_name}.png'
                write_png(width, height, rows, output_path, png_path)

        # Copy cutscenes
        cutscene_videos = []
        for i, cutscene_type in enumerate(('pre', 'post')):
            cutscene_path = f'./{cutscene_type}_cutscene.mov'
            cutscene_output_path = (output_path / cutscene_path)
            cutscene = cutscenes[i]
            if cutscene:
                shutil.copy2(cutscene.path, cutscene_output_path)
                convert_mp4(cutscene_output_path)
                cutscene_output_path.unlink()
                cutscene_videos.append((
                    f'<video playsinline width="640px" class="{cutscene_type}_cutscene_video">'
                    f'<source type="video/mp4" src="./{cutscene_type}_cutscene.mp4">'
                    '</video>'
                ))

        helper_path = pathlib.Path(sys.path[0], '../mesh2web').resolve()
        shutil.copy2((helper_path / 'script.js'), root_path)
        shutil.copytree(
            (helper_path / 'style'),
            (root_path / 'style'),
            dirs_exist_ok=True
        )

        with open((helper_path / 'template.html'), 'r') as template_file:
            title_words = ' '.join([
                f'<span class="title_word">{word}</span>' if word[0].isupper() else word
                for word in level_name.split(' ')
            ])
            next_link = ''
            next_prefetch = ''
            speculation_rules = ''
            if next_level:
                next_url = f'../{next_level}/index.html'
                next_link = (
                    f'<a class="button next_link" href="{next_url}">'

                    '<span class="nav_text next_text">'
                    '<span rel="aria-hidden" class="button_text_shadow">Next</span>'
                    '</span>'

                    '<span class="nav_text next_text">'
                    '<span class="button_text_color">Next</span>'
                    '</span>'

                    '</a>'
                )
                next_prefetch = f'<link rel="prefetch" href="{next_url}">'
                speculation_rules = json.dumps({
                    "prerender": [{
                        "urls": [next_url]
                    }]
                })

            final_html = Template(template_file.read()).safe_substitute(
                title=level_name,
                caption=caption,
                stylesheets='\n'.join(stylesheets),
                script_path=script_path,
                bg_initial_path=bg_initial_path,
                bg_narration_path=bg_narration_path,
                heading_color=rgba2css(heading_color),
                narration_color=rgba2css(narration_color),
                title_words=title_words,
                intro_html=intro_html,
                pregame_images='\n'.join(pregame_imgs),
                audio_path=f'./{level}.mp3',
                durations=durations,
                cutscene_videos='\n'.join(cutscene_videos),
                initial_delay=initial_delay,
                scroll_rate=scroll_rate,
                next_link=next_link,
                next_prefetch=next_prefetch,
                speculation_rules=speculation_rules,
                version_class=version_class,
                caption_top=f'{max_pregame_height+42}px',
            )

        with open((output_path / 'index.html'), 'w') as html_file:
            html_file.write(final_html)

        print(f"Web page extracted. Output saved to {output_path}")

def write_png(width, height, rows, output_path, png_path):
    t = time.perf_counter()
    png = tag2png.make_png(width, height, rows)
    TIME and print(png_path, f'{(time.perf_counter() - t):.3f}')
    with open(
        (output_path / png_path), 'wb'
    ) as png_file:
        png_file.write(png)

def convert_mp3(aifc_path):
    t = time.perf_counter()
    output_path = aifc_path.with_suffix('.mp3')
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-y",
        "-i", aifc_path,
        output_path
    ])
    TIME and print('convert_mp3', f'{(time.perf_counter() - t):.3f}')
    return output_path

def convert_mp4(mov_path):
    t = time.perf_counter()
    output_path = mov_path.with_suffix('.mp4')
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-y",
        "-i", mov_path,
        mov_path.with_suffix('.mp4')
    ])
    TIME and print('convert_mp4', f'{(time.perf_counter() - t):.3f}')
    return output_path

def rgba2css(rgba):
    (r, g, b, a) = rgba
    alpha = round(a/255, 2)
    return f'rgba({r}, {g}, {b}, {alpha})'

def text2html(text):
    lbr = text.decode('mac-roman').replace('\r', '<br>\n')
    return re.sub(r'[\\|]i([^|]+)[\\|]p', '<i>\\1</i>', lbr)

def extract_epilogue_collection(data):
    t = time.perf_counter()
    bitmaps = myth_collection.parse_sequence_bitmaps(data)
    TIME and print('extract_epilogue_collection parse', f'{(time.perf_counter() - t):.3f}', len(data))
    background = bitmaps[0]['bitmaps'][0]
    colors = bitmaps[1]['bitmaps'][0]

    return (background, colors)

def extract_pregame(data):
    t = time.perf_counter()
    bitmaps = myth_collection.parse_sequence_bitmaps(data)
    TIME and print('extract_pregame parse', f'{(time.perf_counter() - t):.3f}', len(data))
    maps = {
        'dark': bitmaps[0]['bitmaps'][0],
        'light': bitmaps[4]['bitmaps'][0]
    }
    colors = bitmaps[3]['bitmaps'][0]

    frame_durations = bitmaps[2]['name'].split(',')
    frames = bitmaps[2]['bitmaps']
    z = zip(frame_durations, frames)
    return (z, maps, colors)

def extract_postgame(data):
    t = time.perf_counter()
    bitmaps = myth_collection.parse_sequence_bitmaps(data)
    TIME and print('extract_postgame parse', f'{(time.perf_counter() - t):.3f}', len(data))

    postgame = {}
    if len(bitmaps[0]['bitmaps']):
        postgame['win'] = bitmaps[0]['bitmaps'][0]
    if len(bitmaps[1]['bitmaps']):
        postgame['loss'] = bitmaps[1]['bitmaps'][0]

    return postgame

def prompt(prompt_path):
    # return True
    response = input(f"Write to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 mesh2web.py <game_directory> [<level> [<plugin_name> [<plugin_output>]]]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    level = None
    plugin_name = None
    plugin_output = None
    if len(sys.argv) > 2:
        level = sys.argv[2]
        if len(sys.argv) > 3:
            plugin_name = sys.argv[3]
            if len(sys.argv) == 5:
                plugin_output = sys.argv[4]

    try:
        main(game_directory, level, plugin_name, plugin_output)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
