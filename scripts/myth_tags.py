#!/usr/bin/env python3
from collections import namedtuple
import struct

import myth_headers
import utils

CONNECTOR_SIZE = 128
ConnectorFmt = """>
    L
    4s
    h
    h
    h
    h
    16x
"""
Connector = namedtuple('Connector', [
    'flags',
    'collection_reference_tag',
    'normal_sequence_index',
    'origin_object_height_fraction',
    'distance_between_interpolants',
    'damaged_sequence_index',
])

PARTICLE_SYS_SIZE = 132
ParticleSysFmt = """>
    L
    4s
    l
    l
    l
    h
    h
    h
    h
    12s
    12s
    h
    h
    h
    h
    24s
    4s
    4s
    h
    h
    h
    h
    h
    30x
"""
ParticleSys = namedtuple('ParticleSys', [
    'flags',
    'collection_reference_tag',
    'minimum_view_distance',
    'transparency_rolloff_point',
    'transparency_cutoff_point',
    'sequence_index',
    'number_of_particles',
    'maximum_particle_number_delta',
    'scale',
    'velocity_lower_bound',
    'velocity_delta',
    'x0_particle_number',
    'x1_particle_number',
    'y0_particle_number',
    'y1_particle_number',
    'state_variables',
    'ambient_sound_tag',
    'splash_local_projectile_group_tag',
    'box_width',
    'box_top_height',
    'box_bottom_height',
    'max_splashes_per_cell',
    'time_between_building_effects',
])

MEDIA_SIZE = 256
MAX_MEDIA_PRGR = 16
MediaFmt = """>
    L
    4s
    16x
    64s
    h
    8s
    h
    4s
    h
    h
    h
    h
    h
    h
    h
    h
    h
    134x
"""
Media = namedtuple('Media', [
    'flags',
    'collection_reference_tag',
    'projectile_group_tags',
    'reflection_tint_fraction',
    'reflection_tint_color',
    'surface_effect_density',
    'surface_effect_local_projectile_group_tag',
    'wobble_magnitude_i',
    'wobble_magnitude_j',
    'wobble_magnitude_k',
    'wobble_phase_multiplier_i',
    'wobble_phase_multiplier_j',
    'wobble_phase_multiplier_k',
    'effects_per_cell',
    'time_between_building_effects',
    'reflection_transparency',
])

MODEL_SIZE = 8
ModelFmt = """>
    L 4s
"""
Model = namedtuple('Model', [
    'flags',
    'geometry_tag',
])

GEOM_SIZE = 8
GeomFmt = """>
    L 4s
"""
Geom = namedtuple('Geom', [
    'flags',
    'collection_reference_tag',
])

ANIM_SIZE = 1024
ANIM_FRAME_SIZE = 16
MAX_ANIM_FRAMES = 31
AnimFmt = """>
    L
    h
    h
    496s
    444x
    h
    h
    h
    h
    h
    h
    4s
    4s
    h
    h
    40x
    L
    L
    L
"""
Anim = namedtuple('Anim', [
    'flags',
    'number_of_frames',
    'ticks_per_frame',
    'frames',
    'shadow_map_width',
    'shadow_map_height',
    'shadow_bytes_per_row',
    'pad',
    'origin_offset_x',
    'origin_offset_y',
    'forward_sound_tag',
    'backward_sound_tag',
    'forward_sound_type',
    'backward_sound_type',
    'shadow_maps_offset',
    'shadow_maps_size',
    'shadow_maps',
])
AnimFrameFmt = """>
    L 4s
    h h
    4x
"""
AnimFrame = namedtuple('AnimFrame', [
    'flags',
    'model_tag',
    'model_type',
    'permutation_index',
])

SCENERY_SIZE = 128
MAX_SCENERY_PRGR = 4
MAX_SCENERY_SEQ = 6
SceneryFmt = """>
    L
    4s
    4s
    4s
    h
    h
    4x
    16s
    12s
    58x
    h
    8s
    h
    h
    h
    h
"""
Scenery = namedtuple('Scenery', [
    'flags',
    'collection_reference_tag',
    'object_tag',
    'projectile_tag',
    'valid_netgame_scoring_type',
    'netgame_flag_number',
    'projectile_group_tags',
    'sequence_indexes',
    'model_permutation_delta',
    'projectile_group_types',
    'collection_reference_index',
    'impact_projectile_group_type',
    'object_type',
    'projectile_type',
])

    
def parse_tag(data, size, ntuple, fmt):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + size
    return ntuple._make(struct.unpack(fmt, data[start:end]))

def parse_connector(data):
    return parse_tag(data, CONNECTOR_SIZE, Connector, ConnectorFmt)

def parse_particle_sys(data):
    return parse_tag(data, PARTICLE_SYS_SIZE, ParticleSys, ParticleSysFmt)

def parse_media(data):
    media = parse_tag(data, MEDIA_SIZE, Media, MediaFmt)
    return media._replace(
        projectile_group_tags=struct.unpack(f'>{MAX_MEDIA_PRGR * "4s"}', media.projectile_group_tags)
    )

def parse_model(data):
    return parse_tag(data, MODEL_SIZE, Model, ModelFmt)

def parse_geom(data):
    return parse_tag(data, GEOM_SIZE, Geom, GeomFmt)

def parse_anim(data):
    anim = parse_tag(data, ANIM_SIZE, Anim, AnimFmt)

    frames = []
    for values in utils.iter_struct(
        0, MAX_ANIM_FRAMES,
        AnimFrameFmt, anim.frames
    ):
        frame = AnimFrame._make(values)
        frames.append(frame)
    return anim._replace(
        frames=frames
    )

def parse_scenery(data):
    scenery = parse_tag(data, SCENERY_SIZE, Scenery, SceneryFmt)
    return scenery._replace(
        projectile_group_tags=struct.unpack(f'>{MAX_SCENERY_PRGR * "4s"}', scenery.projectile_group_tags),
        sequence_indexes=struct.unpack(f'>{MAX_SCENERY_SEQ}h', scenery.sequence_indexes),
        projectile_group_types=struct.unpack(f'>{MAX_SCENERY_PRGR}h', scenery.projectile_group_types),
    )
