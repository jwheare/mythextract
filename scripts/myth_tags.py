#!/usr/bin/env python3
import struct

import codec
import myth_headers

ConnectorFmt = ('Connector', [
    ('L', 'flags'),
    ('4s', 'collection_reference_tag'),
    ('h', 'normal_sequence_index'),
    ('h', 'origin_object_height_fraction'),
    ('h', 'distance_between_interpolants'),
    ('h', 'damaged_sequence_index'),
    ('16x', None),
])

ParticleSysFmt = ('ParticleSys', [
    ('L', 'flags'),
    ('4s', 'collection_reference_tag'),
    ('L', 'minimum_view_distance', codec.World),
    ('L', 'transparency_rolloff_point', codec.World),
    ('L', 'transparency_cutoff_point', codec.World),
    ('h', 'sequence_index'),
    ('H', 'number_of_particles'),
    ('H', 'maximum_particle_number_delta'), # unused
    ('H', 'scale', codec.Fixed),
    ('L', 'velocity_lower_bound_i', codec.Fixed),
    ('L', 'velocity_lower_bound_j', codec.Fixed),
    ('L', 'velocity_lower_bound_k', codec.Fixed),
    ('L', 'velocity_delta_i', codec.fixed_delta('velocity_lower_bound_i')),
    ('L', 'velocity_delta_j', codec.fixed_delta('velocity_lower_bound_j')),
    ('L', 'velocity_delta_k', codec.fixed_delta('velocity_lower_bound_j')),
    ('H', 'x0_particle_number', codec.ShortFixed),
    ('H', 'x1_particle_number', codec.ShortFixed),
    ('H', 'y0_particle_number', codec.ShortFixed),
    ('H', 'y1_particle_number', codec.ShortFixed),
    ('H', 'not_snowing_duration_lower_bound', codec.Time),
    ('H', 'not_snowing_duration_delta', codec.time_delta('not_snowing_duration_lower_bound')),
    ('H', 'not_snowing_value_lower_bound', codec.Percent),
    ('H', 'not_snowing_value_delta', codec.percent_delta('not_snowing_value_lower_bound')),
    ('H', 'not_snowing_transition_lower_bound', codec.Time),
    ('H', 'not_snowing_transition_delta', codec.time_delta('not_snowing_transition_lower_bound')),
    ('H', 'snowing_duration_lower_bound', codec.Time),
    ('H', 'snowing_duration_delta', codec.time_delta('snowing_duration_lower_bound')),
    ('H', 'snowing_value_lower_bound', codec.Percent),
    ('H', 'snowing_value_delta', codec.percent_delta('snowing_value_lower_bound')),
    ('H', 'snowing_transition_lower_bound', codec.Time),
    ('H', 'snowing_transition_transition_delta', codec.time_delta('snowing_transition_lower_bound')),
    ('4s', 'ambient_sound_tag'),
    ('4s', 'splash_local_projectile_group_tag'),
    ('H', 'box_width'),
    ('H', 'box_top_height', codec.World),
    ('H', 'box_bottom_height', codec.World),
    ('H', 'max_splashes_per_cell'),
    ('H', 'time_between_building_effects'),
    ('26x', None),
])

MAX_MEDIA_PRGR = 16
MediaFmt = ('Media', [
    ('L', 'flags'),
    ('4s', 'collection_reference_tag'),
    ('16x', None),
    ('64s', 'projectile_group_tags', codec.list_pack('MediaPgrTags', MAX_MEDIA_PRGR, '>4s')),
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

ModelFmt = ('Model', [
    ('L', 'flags'),
    ('4s', 'geometry_tag'),
])

GeomFmt = ('Geom', [
    ('L', 'flags'),
    ('4s', 'collection_reference_tag'),
])

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
    ('496s', 'frames', codec.list_codec(MAX_ANIM_FRAMES, AnimFrameFmt)),
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
    ('16s', 'projectile_group_tags', codec.list_pack(
        'SceneryPgrTags', MAX_SCENERY_PRGR, '>4s',
        filter_fun=lambda _self, t: not codec.all_on(t),
        empty_value=struct.pack('>l', -1)
    )),
    ('12s', 'sequence_indexes', codec.list_pack(
        'ScenerySeqIndexes', MAX_SCENERY_SEQ, '>h'
    )),
    ('58x', None),
    ('h', 'model_permutation_delta'),
    ('8s', 'projectile_group_types', codec.list_pack(
        'SceneryPgrTypes', MAX_SCENERY_PRGR, '>h'
    )),
    ('h', 'collection_reference_index'),
    ('h', 'impact_projectile_group_type'),
    ('h', 'object_type'),
    ('h', 'projectile_type'),
])

def parse_connector(data):
    return myth_headers.parse_tag(ConnectorFmt, data)

def parse_particle_sys(data):
    return myth_headers.parse_tag(ParticleSysFmt, data)

def parse_media(data):
    return myth_headers.parse_tag(MediaFmt, data)

def parse_model(data):
    return myth_headers.parse_tag(ModelFmt, data)

def parse_geom(data):
    return myth_headers.parse_tag(GeomFmt, data)

def parse_anim(data):
    return myth_headers.parse_tag(AnimFmt, data)

def parse_scenery(data):
    return myth_headers.parse_tag(SceneryFmt, data)
