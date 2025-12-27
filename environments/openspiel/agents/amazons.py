"""Amazons Game Agent"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseGameAgent
from typing import Dict, Any


class AmazonsAgent(BaseGameAgent):
    """Amazons Game Agent - Complex territorial control game"""
    
    @property
    def game_name(self) -> str:
        return "amazons"
    
    def get_rules(self) -> str:
        return """AMAZONS RULES:
Board: 10×10 grid. Each player has 4 amazons (queen-like pieces).
Goal: Be the last player able to move.

Turn structure (each move has 2 parts):
1. Move your amazon (like a chess queen: any distance horizontally, vertically, or diagonally)
2. Shoot an arrow from the new position (also like a queen move, blocking that square)

Rules:
- Amazons cannot move through or onto blocked squares or other amazons
- Arrows permanently block squares (cannot be removed)
- Players must make both moves if possible
- You lose if you cannot make a legal move on your turn

Strategy: Control territory, trap opponent's amazons, maintain mobility.
This is a highly tactical game requiring long-term spatial planning.

Move Format: Each action combines amazon movement + arrow placement.
Example: "a4-d4-d1" means move amazon from a4 to d4, shoot arrow to d1."""
    
    def generate_params(self, config_id: int) -> Dict[str, Any]:
        """
        Amazons parameter generation
        
        Config variants:
        - 0: Standard 10x10 board
        - 1: Smaller 8x8 board (faster games)
        - 2: 6x6 board (for quicker evaluation)
        """
        size_variant = config_id % 3
        
        if size_variant == 0:
            board_size = 10
        elif size_variant == 1:
            board_size = 8
        else:
            board_size = 6
        
        return {"board_size": board_size}
    
    def get_mcts_config(self) -> tuple[int, int]:
        """
        2-player territorial control game. Very high complexity.
        Large action space (hundreds of moves per turn in early game).
        """
        return (300, 30)