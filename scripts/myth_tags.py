#!/usr/bin/env python3
import struct
import os

import codec
import myth_headers

DEBUG = (os.environ.get('DEBUG') == '1')

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

MAXIMUM_MATERIALS_PER_GEOMETRY = 32
ModelPermutationFmt = ('ModelPermutation', [
    ('H', 'collection_reference_permutation'),
    ('32s', 'frames', codec.list_pack('ModelPermutationFrames', MAXIMUM_MATERIALS_PER_GEOMETRY, '>b')),
    ('26x', None),
    ('2x', None),
    ('2x', None),
])
ModelMeshCellFmt = ('ModelMeshCell', [
    ('h', 'x'),
    ('h', 'y'),
    ('h', 'flags'),
    ('2x', None)
])
ModelFmt = ('Model', [
    ('L', 'flags'),
    ('4s', 'geometry_tag'),
    ('h', 'geometry_index'),
    ('H', 'vertex_flags_count'),
    ('H', 'permutation_count'),
    ('H', 'mesh_cell_count'),

    ('L', 'geometry_vertex_offset'),
    ('L', 'geometry_vertex_size'),
    ('l', 'geometry_vertex_ptr'),
    
    ('L', 'permutations_offset'),
    ('L', 'permutations_size'),
    ('L', 'permutations_ptr'),
    
    ('L', 'mesh_cell_offset'),
    ('L', 'mesh_cell_size'),
    ('L', 'mesh_cell_ptr'),
    
    ('L', 'data_offset'),
    ('L', 'data_size'),
    ('L', 'data_ptr'),
])

GeomMaterialFmt = ('GeomMaterial', [
    ('32s', 'name', codec.String),
    ('h', 'sequence_index'),
    ('h', 'collection_index'),
    ('h', 'color_table_index'),
    ('h', 'bitmap_index'),
    ('24x', None),
])
GeomFmt = ('Geom', [
    ('L', 'flags'),
    ('4s', 'collection_reference_tag'),
    ('h', 'material_count'),
    ('h', 'vertex_count'),
    ('h', 'surface_count'),
    ('h', 'dependency_count'),
    ('h', 'center_x'),
    ('h', 'center_y'),
    ('h', 'center_z'),
    ('6x', None),
    ('L', 'materials_offset'),
    ('L', 'materials_size'),
    ('L', 'materials_ptr'),
    ('L', 'vertex_offset'),
    ('L', 'vertex_size'),
    ('L', 'vertex_ptr'),
    ('L', 'surface_offset'),
    ('L', 'surface_size'),
    ('L', 'surface_ptr'),
    ('L', 'dependency_offset'),
    ('L', 'dependency_size'),
    ('L', 'dependency_ptr'),
    ('L', 'data_offset'),
    ('L', 'data_size'),
    ('L', 'data_ptr'),
    ('h', 'bounds_min_x'),
    ('h', 'bounds_min_y'),
    ('h', 'bounds_min_z'),
    ('h', 'bounds_max_x'),
    ('h', 'bounds_max_y'),
    ('h', 'bounds_max_z'),
    ('26x', None),
    ('2x', None),
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
    model = myth_headers.parse_tag(ModelFmt, data)
    if DEBUG:
        model_data = data[64:]
        value_data = model_data[model.data_offset:]
        print('actual model data size', len(model_data[model.data_offset:]))
        print('combined size', model.geometry_vertex_size + model.permutations_size + model.mesh_cell_size)

        vertex_flags = codec.list_pack('ModelVertexFlags', model.vertex_flags_count, '>L', offset=model.geometry_vertex_offset)(value_data)

        permutations = codec.list_codec(
            model.permutation_count,
            ModelPermutationFmt
        )(value_data, offset=model.permutations_offset)

        mesh_cells = codec.list_codec(
            model.mesh_cell_count,
            ModelMeshCellFmt
        )(value_data, offset=model.mesh_cell_offset)

        print('vertex_flags', len(vertex_flags), list(vertex_flags))
        print('permutations', len(permutations))
        for p in permutations:
            print(p.collection_reference_permutation, list(p.frames))
        print('  mesh_cells', len(mesh_cells), [(c.x, c.y, c.flags) for c in mesh_cells])

    return model

def parse_geom(data):
    geom = myth_headers.parse_tag(GeomFmt, data)
    if DEBUG:
        geom_data = data[64:]
        value_data = geom_data[geom.data_offset:]
        
        print('actual geom data size', len(geom_data[geom.data_offset:]))
        print('combined size', geom.materials_size + geom.vertex_size + geom.surface_size + geom.dependency_size)

        materials = codec.list_codec(
            geom.material_count,
            GeomMaterialFmt
        )(value_data, offset=geom.materials_offset)

        print('materials', len(materials))
        for mat in materials:
            print(mat)

    return geom

def parse_anim(data):
    return myth_headers.parse_tag(AnimFmt, data)

def parse_scenery(data):
    return myth_headers.parse_tag(SceneryFmt, data)
