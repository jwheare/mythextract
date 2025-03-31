#!/usr/bin/env python3
from collections import namedtuple
import os
import struct

import myth_headers

DEBUG_SOUN = (os.environ.get('DEBUG_SOUN') == '1')

SOUN_HEADER_SIZE = 64
SoundHeaderFmt = """>
    L h h H
    H H H H

    h
    L L

    4s H H
    L L L

    I I I I
"""
SoundHeader = namedtuple('SoundHeader', [
    'flags', 'loudness', 'play_fraction', 'external_frequency_modifier',
    'pitch_lower_bound', 'pitch_delta', 'volume_lower_bound', 'volume_delta',

    'first_subtitle_within_string_list_index',
    'sound_offset', 'sound_size',

    'subtitle_string_list_tag', 'subtitle_string_list_index', 'unused',
    'permutation_count', 'permutations_offset', 'permutations_size',

    'd6', 'd7', 'd8', 'd9'
])

AMSO_SIZE = 64
MAX_AMSO_SOUN = 6
AmsoFmt = """>
    L
    h h
    h h
    24s
    h
    10x
    12s
    h h
"""
Amso = namedtuple('Amso', [
    'flags',
    'inner_radius', 'outer_radius',
    'period_lower_bound', 'period_delta',
    'sound_tags',
    'random_sound_radius',
    'sound_indexes',
    'phase', 'period'
])

def parse_soun_header(data):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + SOUN_HEADER_SIZE
    return SoundHeader._make(struct.unpack(SoundHeaderFmt, data[start:end]))

def parse_amso(data):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + AMSO_SIZE
    amso = Amso._make(struct.unpack(AmsoFmt, data[start:end]))
    sound_tags = struct.unpack(f'>{MAX_AMSO_SOUN * "4s"}', amso.sound_tags)
    sound_indexes = struct.unpack(f'>{MAX_AMSO_SOUN}h', amso.sound_indexes)
    return amso._replace(
        sound_tags=sound_tags,
        sound_indexes=sound_indexes,
    )
