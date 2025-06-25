#!/usr/bin/env python3
import sys
import os
import struct
import subprocess
import pathlib

import myth_sound
import loadtags

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, input_soun_id, plugin_names):
    """
    Load Myth game tags and plugins and output sounds as aifc
    """
    (game_version, tags, entrypoint_map, data_map, cutscenes) = loadtags.load_tags(game_directory, plugin_names)

    try:
        extract_sounds(game_version, tags, data_map, input_soun_id, plugin_names)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

def extract_sounds(game_version, tags, data_map, input_soun_id, plugin_names):
    sounds = collect_sounds(tags, data_map, input_soun_id, plugin_names)

    output_dir = '../output/soun2aifc'
    output_path = pathlib.Path(sys.path[0], output_dir).resolve()

    if prompt(output_path):
        for (soun_id, soun_loc, soun_header, permutations) in sounds:
            if len(permutations):
                subdir = soun_header.signature
                if plugin_names and soun_loc[0] in plugin_names:
                    subdir = soun_loc[0]
                sub_path = output_path / f'{subdir}'
                soun_path = f'{soun_id}-{soun_header.name.replace('/', '-')}'
                
                for i, perm in enumerate(permutations):
                    aifc = myth_sound.generate_aifc(perm)
                    perm_filename = f'{soun_id}-{i}-{perm['desc'].replace('/', '-')}'
                    
                    aifc_dir = sub_path / f'aifc/{soun_path}'
                    aifc_path = aifc_dir / f'{perm_filename}.aifc'
                    pathlib.Path(aifc_dir).mkdir(parents=True, exist_ok=True)
                    with open(aifc_path, 'wb') as aifc_file:
                        aifc_file.write(aifc)

                    print(f"AIFC extracted. Output saved to {aifc_path}")

                    wav_dir = sub_path / f'wav/{soun_path}'
                    wav_path = wav_dir / f'{perm_filename}.wav'
                    pathlib.Path(wav_dir).mkdir(parents=True, exist_ok=True)
                    convert_wav(aifc_path, wav_path)
                    print(f"WAV converted. Output saved to {wav_path}")


def convert_wav(aifc_path, wav_path):
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-y",
        "-i", aifc_path,
        wav_path
    ])

def collect_sounds(tags, data_map, input_soun_id, plugin_names):
    if input_soun_id == 'all':
        for soun_id, locations in tags['soun'].items():
            if not plugin_names or set(loc[0] for loc in locations) == set(plugin_names):
                yield get_permutations(tags, data_map, soun_id)
    else:
        yield get_permutations(tags, data_map, input_soun_id)

def get_permutations(tags, data_map, soun_id):
    (soun_loc, soun_header, soun_data) = loadtags.get_tag_info(
        tags, data_map, 'soun', soun_id
    )
    (game_version, soun_tag_id, permutations) = myth_sound.parse_soun_tag(soun_data)
    return (soun_id, soun_loc, soun_header, permutations)

def prompt(prompt_path):
    return True
    response = input(f"Write to: {prompt_path} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: python3 {sys.argv[0]} <game_directory> <soun_id> [<plugin_names> ...]")
        sys.exit(1)
    
    game_directory = sys.argv[1]

    soun_id = sys.argv[2]
    plugin_names = []
    if len(sys.argv) > 3:
        plugin_names = sys.argv[3:]

    try:
        main(game_directory, soun_id, plugin_names)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
