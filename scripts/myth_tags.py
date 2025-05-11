#!/usr/bin/env python3
from collections import namedtuple
import struct

import myth_headers
import utils

CONNECTOR_SIZE = 128
ConnectorFmt = ('Connector', [
    ('L', 'flags'),
    ('4s', 'collection_reference_tag'),
    ('h', 'normal_sequence_index'),
    ('h', 'origin_object_height_fraction'),
    ('h', 'distance_between_interpolants'),
    ('h', 'damaged_sequence_index'),
    ('16x', None),
])

PARTICLE_SYS_SIZE = 132
ParticleSysFmt = ('ParticleSys', [
    ('L', 'flags'),
    ('4s', 'collection_reference_tag'),
    ('l', 'minimum_view_distance'),
    ('l', 'transparency_rolloff_point'),
    ('l', 'transparency_cutoff_point'),
    ('h', 'sequence_index'),
    ('h', 'number_of_particles'),
    ('h', 'maximum_particle_number_delta'),
    ('h', 'scale'),
    ('12s', 'velocity_lower_bound'),
    ('12s', 'velocity_delta'),
    ('h', 'x0_particle_number'),
    ('h', 'x1_particle_number'),
    ('h', 'y0_particle_number'),
    ('h', 'y1_particle_number'),
    ('24s', 'state_variables'),
    ('4s', 'ambient_sound_tag'),
    ('4s', 'splash_local_projectile_group_tag'),
    ('h', 'box_width'),
    ('h', 'box_top_height'),
    ('h', 'box_bottom_height'),
    ('h', 'max_splashes_per_cell'),
    ('h', 'time_between_building_effects'),
    ('30x', None),
])

MEDIA_SIZE = 256
MAX_MEDIA_PRGR = 16
MediaFmt = ('Media', [
    ('L', 'flags'),
    ('4s', 'collection_reference_tag'),
    ('16x', None),
    ('64s', 'projectile_group_tags', utils.list_pack('MediaPgrTags', MAX_MEDIA_PRGR, '>4s')),
    ('h', 'reflection_tint_fraction'),
    ('8s', 'reflection_tint_color'),
    ('h', 'surface_effect_density'),
    ('4s', 'surface_effect_local_projectile_group_tag'),
    ('h', 'wobble_magnitude_i'),
    ('h', 'wobble_magnitude_j'),
    ('h', 'wobble_magnitude_k'),
    ('h', 'wobble_phase_multiplier_i'),
    ('h', 'wobble_phase_multiplier_j'),
    ('h', 'wobble_phase_multiplier_k'),
    ('h', 'effects_per_cell'),
    ('h', 'time_between_building_effects'),
    ('h', 'reflection_transparency'),
    ('134x', None),
])

MODEL_SIZE = 8
ModelFmt = ('Model', [
    ('L', 'flags'),
    ('4s', 'geometry_tag'),
])

GEOM_SIZE = 8
GeomFmt = ('Geom', [
    ('L', 'flags'),
    ('4s', 'collection_reference_tag'),
])

ANIM_SIZE = 1024
ANIM_FRAME_SIZE = 16
MAX_ANIM_FRAMES = 31
AnimFrameFmt = ('AnimFrame', [
    ('L', 'flags'),
    ('4s', 'model_tag'),
    ('h', 'model_type'),
    ('h', 'permutation_index'),
    ('4x', None),
])
AnimFmt = ('Anim', [
    ('L', 'flags'),
    ('h', 'number_of_frames'),
    ('h', 'ticks_per_frame'),
    ('496s', 'frames', utils.list_codec('AnimFrames', MAX_ANIM_FRAMES, AnimFrameFmt)),
    ('444x', None),
    ('h', 'shadow_map_width'),
    ('h', 'shadow_map_height'),
    ('h', 'shadow_bytes_per_row'),
    ('h', 'pad'),
    ('h', 'origin_offset_x'),
    ('h', 'origin_offset_y'),
    ('4s', 'forward_sound_tag'),
    ('4s', 'backward_sound_tag'),
    ('h', 'forward_sound_type'),
    ('h', 'backward_sound_type'),
    ('40x', None),
    ('L', 'shadow_maps_offset'),
    ('L', 'shadow_maps_size'),
    ('L', 'shadow_maps'),
])

SCENERY_SIZE = 128
MAX_SCENERY_PRGR = 4
MAX_SCENERY_SEQ = 6
SceneryFmt = ('Scenery', [
    ('L', 'flags'),
    ('4s', 'collection_reference_tag'),
    ('4s', 'object_tag'),
    ('4s', 'projectile_tag'),
    ('h', 'valid_netgame_scoring_type'),
    ('h', 'netgame_flag_number'),
    ('4x', None),
    ('16s', 'projectile_group_tags', utils.list_pack(
        'SceneryPgrTags', MAX_SCENERY_PRGR, '>4s'
    )),
    ('12s', 'sequence_indexes', utils.list_pack(
        'ScenerySeqIndexes', MAX_SCENERY_SEQ, '>h'
    )),
    ('58x', None),
    ('h', 'model_permutation_delta'),
    ('8s', 'projectile_group_types', utils.list_pack(
        'SceneryPgrTypes', MAX_SCENERY_PRGR, '>h'
    )),
    ('h', 'collection_reference_index'),
    ('h', 'impact_projectile_group_type'),
    ('h', 'object_type'),
    ('h', 'projectile_type'),
])
    
def parse_tag(data, size, fmt):
    start = myth_headers.TAG_HEADER_SIZE
    end = start + size
    return utils.decode_data(fmt, data[start:end])

def parse_connector(data):
    return parse_tag(data, CONNECTOR_SIZE, ConnectorFmt)

def parse_particle_sys(data):
    return parse_tag(data, PARTICLE_SYS_SIZE, ParticleSysFmt)

def parse_media(data):
    return parse_tag(data, MEDIA_SIZE, MediaFmt)

def parse_model(data):
    return parse_tag(data, MODEL_SIZE, ModelFmt)

def parse_geom(data):
    return parse_tag(data, GEOM_SIZE, GeomFmt)

def parse_anim(data):
    return parse_tag(data, ANIM_SIZE, AnimFmt)

def parse_scenery(data):
    return parse_tag(data, SCENERY_SIZE, SceneryFmt)
