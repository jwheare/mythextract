#!/usr/bin/env python3
import json
import os
import struct
import sys

import reco_tag

DEBUG = (os.environ.get('DEBUG') == '1')

def main(game_directory, reco_file):
    """
    Log commands from a recording file
    """

    try:
        (
            reco_header, players, players_idx, monsters, teams, teams_idx,
            plugins, mesh_header, level_name, game_time, game_type_choice, difficulty,
            overhead_map_data, chat_lines, trades, splits, game_stats
        ) = reco_tag.parse_reco_file(game_directory, reco_file)

        print(json.dumps(game_stats, indent=2))

    except (struct.error, UnicodeDecodeError) as e:
        raise ValueError(f"Error processing binary data: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <game_directory> <reco_file>")
        sys.exit(1)
    
    game_directory = sys.argv[1]
    reco_file = sys.argv[2]

    try:
        main(game_directory, reco_file)
    except KeyboardInterrupt:
        sys.exit(130)
    except BrokenPipeError:
        sys.stdout = None
        sys.exit(1)
