#!/usr/bin/env python3
import sys
import os
import struct
import pathlib

import myth_sound
import utils

DEBUG = (os.environ.get('DEBUG') == '1')

def main(tag_path, aifc_path):
    """
    Parse a Myth TFL or Myth II soun tag file and output the aifc file
    """
    data = utils.load_file(tag_path)

    try:
        (game_version, tag_id, permutations) = myth_sound.parse_soun_tag(data)
    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

    if not aifc_path:
        aifc_path = f'../output/aifc/{game_version}-{tag_id}.aifc'
        path = pathlib.Path(sys.path[0], aifc_path).resolve()
    else:
        path = pathlib.Path(aifc_path).with_suffix('.aifc')

    perm_count = len(permutations)

    if prompt(path, perm_count):
        for i, perm in enumerate(permutations):
            aifc = myth_sound.generate_aifc(perm)
            
            perm_path = path
            if (perm_count > 1):
                perm_path = path.with_stem(f'{path.stem}-{i}')

            pathlib.Path(perm_path.parent).mkdir(parents=True, exist_ok=True)
            with open(perm_path, 'wb') as aifc_file:
                aifc_file.write(aifc)
                print(f"AIFC extracted. Output saved to {perm_path} ({perm['desc']})")


def prompt(prompt_path, perm_count):
    # return True
    prefix = ''
    suffix = ''
    if (perm_count > 1):
        prompt_path = prompt_path.with_stem(f'{prompt_path.stem}-n')
        prefix = f'{perm_count}x permutations '
        suffix = ' (n=permutation)'
    response = input(f"Write {prefix}to: {prompt_path}{suffix} [Y/n]: ").strip().lower()
    return response in {"", "y", "yes"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tag2aifc.py <input_file> [<output_file>]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    if len(sys.argv) == 3:
        output_file = sys.argv[2]
    else:
        output_file = None
    
    try:
        main(input_file, output_file)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
