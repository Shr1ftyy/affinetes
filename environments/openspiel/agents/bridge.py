"""Bridge Game Agent"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_agent import BaseGameAgent
from typing import Dict, Any


class BridgeAgent(BaseGameAgent):
    """Bridge Game Agent - 4-player card game"""
    
    @property
    def game_name(self) -> str:
        return "bridge"
    
    def get_rules(self) -> str:
        return """BRIDGE RULES:
Players: 4 players in 2 partnerships (North-South vs East-West). Uses standard 52-card deck.
Goal: Win tricks to fulfill your contract bid.

Game phases:
1. BIDDING: Players bid to declare contract (level + suit/NT). Bids must be higher than previous.
   - Level: 1-7 (number of tricks over 6 needed)
   - Strain: ♣ (Clubs) < ♦ (Diamonds) < ♥ (Hearts) < ♠ (Spades) < NT (No Trump)
   - Special bids: Pass, Double, Redouble
   - Bidding ends after 3 consecutive passes

2. PLAY: Declarer's partner (dummy) reveals cards. Declarer controls both hands.
   - Must follow suit if possible
   - Highest card in led suit wins (or highest trump if trump played)
   - Winner of trick leads next

Scoring: Points based on contract level, suit, and tricks won.
Win condition: Partnership that fulfills more contracts wins overall.

NOTE: This is a simplified Bridge implementation focusing on bidding strategy and trick-taking."""
    
    def generate_params(self, config_id: int) -> Dict[str, Any]:
        """
        Bridge parameter generation
        
        Config variants:
        - 0: Standard rubber bridge
        - 1: Chicago bridge (4 deals)
        - 2: Duplicate bridge scoring
        """
        variant = config_id % 3
        
        params = {}
        
        if variant == 0:
            # Rubber bridge (default)
            params = {}
        elif variant == 1:
            # Chicago bridge
            params = {"is_chicago": True}
        else:
            # Duplicate scoring
            params = {"is_duplicate": True}
        
        return params
    
    def get_mcts_config(self) -> tuple[int, int]:
        """
        4-player card game. 52-card deck, complex bidding and play.
        High strategic depth, imperfect information.
        """
        return (500, 50)