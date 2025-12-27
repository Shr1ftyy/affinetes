"""Oware Game Agent"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseGameAgent
from typing import Dict, Any


class OwareAgent(BaseGameAgent):
    """Oware Game Agent - African mancala-style strategy game"""
    
    @property
    def game_name(self) -> str:
        return "oware"
    
    def get_rules(self) -> str:
        return """OWARE RULES:
Board: 2 rows of 6 pits (houses), each with 4 seeds initially. Each player owns one row.
Goal: Capture more seeds than your opponent (>24 seeds to win).

Turn structure:
1. Pick all seeds from one of your pits
2. Sow seeds counter-clockwise, one per pit (including opponent's pits)
3. Capture: If last seed lands in opponent's pit with 2 or 3 total seeds, capture those seeds
4. Continue capturing backwards if previous pits also have 2-3 seeds

Rules:
- Cannot leave opponent with no seeds (must give them a move)
- Grand Slam: Capturing all opponent's seeds is forbidden (unless unavoidable)
- Game ends when one player cannot move, or by mutual agreement

Scoring: Player with most captured seeds wins.

Strategy: Balance between sowing for position and capturing opportunities.
Requires counting, planning multiple moves ahead, and denying opponent options.

Move Format: Select pit number (0-5) from your row to sow seeds."""
    
    def generate_params(self, config_id: int) -> Dict[str, Any]:
        """
        Oware parameter generation
        
        Config variants:
        - 0: Standard rules (4 seeds per pit)
        - 1: Variant with 3 seeds per pit (faster)
        - 2: Variant with 5 seeds per pit (longer games)
        """
        seed_variant = config_id % 3
        
        if seed_variant == 0:
            seeds_per_house = 4  # Standard
        elif seed_variant == 1:
            seeds_per_house = 3  # Faster
        else:
            seeds_per_house = 5  # Longer
        
        return {"seeds_per_house": seeds_per_house}
    
    def get_mcts_config(self) -> tuple[int, int]:
        """
        2-player counting game. Medium complexity.
        Action space: 6 moves per turn (choose which pit to sow).
        Requires calculation of sowing patterns and captures.
        """
        return (1000, 100)