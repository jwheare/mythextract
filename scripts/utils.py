import re
import struct
import sys

import cProfile
import pstats

import codec

PROFILER = cProfile.Profile()

def all_on(val):
    return all(f == b'' for f in val.split(b'\xff'))

def all_off(val):
    return all(f == b'' for f in val.split(b'\x00'))

def all_printable(val):
    return all(32 <= b <= 126 for b in val)

def print_bytes(byte_sequence, group_size):
    group_i = 0
    for i, b in enumerate(byte_sequence):
        if i % group_size == 0:
            group_i += 1
        print(f'\x1b[3{(group_i % 6 + 1)}m{b}\x1b[0m', end=' ')
    print('---')

def val_repr(val, nt=None):
    if type(val) is bytes and all_off(val):
        return f'[00 x {len(val)}]'
    elif type(val) is bytes and all_on(val):
        return f'[FF x {len(val)}]'
    elif type(val) is bytes and all_printable(val):
        return val
    elif type(val) is bytes:
        return f'0x{val.hex()}'
    elif type(val) is float:
        return f'{val:.03f}'
    elif nt and isinstance(val, codec._Delta):
        upper = val.upper_bound(nt)
        if upper:
            return f'{repr(val)} upper={val.upper_bound_str(nt)}'
        else:
            return repr(val)
    else:
        return repr(val)

def iter_unpack(start, count, fmt, data):
    end = start + (count * struct.calcsize(fmt))
    yield from struct.iter_unpack(fmt, data[start:end])

def cap_title(string):
    return ' '.join([w.title() for w in string.split('_')])

def ansi_format(text):
    italic = re.sub(r'[\|]i', '\x1b[3m', str(text), flags=re.IGNORECASE)
    bold = re.sub(r'[\|]b', '\x1b[1m', italic, flags=re.IGNORECASE)
    plain = re.sub(r'[\|]p', '\x1b[0m', bold, flags=re.IGNORECASE)
    return f'{plain}\x1b[0m'

def strip_format(text):
    return re.sub(r'[\|][ibp]', '', str(text), flags=re.IGNORECASE)

def strip_order(text):
    return re.sub(r'\s{3,}.*', '', str(text))

def decode_string(s):
    return codec.decode_string(s)

def flag(flag_class):
    return lambda index: flag_class(1 << index)

TagTypes = {
    'amso': "Ambient Sounds",
    'arti': "Artifacts",
    'core': "Collection References",
    '.256': "Collections",
    'conn': "Connectors",
    'ditl': "Dialog String Lists",
    'd256': "Detail Collections",
    'dmap': "Detail Maps",
    'dtex': "Detail Textures",
    'bina': "Dialogs",
    'font': "Fonts",
    'form': "Formations",
    'geom': "Geometries",
    'inte': "Interface",
    'ligh': "Lightning",
    'phys': "Local Physics",
    'lpgr': "Local Projectile Groups",
    'medi': "Media Types",
    'meef': "Mesh Effect",
    'meli': "Mesh Lighting",
    'mesh': "Meshes",
    'anim': "Model Animations",
    'mode': "Models",
    'mons': "Monsters",
    'obje': "Objects",
    'obpc': "Observer Constants",
    'part': "Particle Systems",
    'pref': "Preferences",
    'prel': "Preloaded Data",
    'prgr': "Projectile Groups",
    'proj': "Projectiles",
    'reco': "Recordings",
    'save': "Saved Games",
    'scen': "Scenery",
    'scri': "Scripts",
    'soli': "Sound Lists",
    'soun': "Sounds",
    'stli': "String Lists",
    'temp': "Templates",
    'text': "Text",
    'unit': "Units",
    'wind': "Wind",
}

def local_folder(tag_header):
    return tag_type_name(tag_header.tag_type)

def tag_type_name(tag_type):
    return TagTypes[tag_type.lower()].lower()

def load_file(path, length=None):
    try:
        with open(path, 'rb') as infile:
            if length:
                data = infile.read(length)
            else:
                data = infile.read()
    except FileNotFoundError:
        print(f"Error: File not found - {path}")
        sys.exit(1)

    return data

def profileStart():
    PROFILER.enable()

def profileEnd():
    PROFILER.disable()
    pstats.Stats(PROFILER).sort_stats(pstats.SortKey.CUMULATIVE).print_stats(100)
