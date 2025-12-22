"""Base Game Agent for OpenSpiel games"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple
import pyspiel


class BaseGameAgent(ABC):
    """
    Base class for game-specific agents.
    
    Each game implements an Agent subclass that encapsulates:
    - State formatting
    - Rule descriptions
    - Prompt generation
    - Parameter configuration
    """
    
    @property
    @abstractmethod
    def game_name(self) -> str:
        """Game name in OpenSpiel"""
        pass
    
    @abstractmethod
    def get_rules(self) -> str:
        """
        Return game rules text
        
        Returns:
            Complete rule description text
        """
        pass
    
    @abstractmethod
    def format_state(self, state: pyspiel.State, player_id: int) -> str:
        """
        Convert OpenSpiel state to LLM-friendly description
        
        Args:
            state: OpenSpiel game state
            player_id: Current player ID
            
        Returns:
            Human-readable state description
        """
        pass
    
    @abstractmethod
    def generate_params(self, config_id: int) -> Dict[str, Any]:
        """
        Generate game parameters based on config_id
        
        Args:
            config_id: Configuration variant ID (0-99999999)
            
        Returns:
            Game parameter dictionary
        """
        pass
    
    def format_action_history(
        self,
        action_history: List[Tuple[int, int]],
        state: pyspiel.State
    ) -> str:
        """
        Format action history (default implementation)
        
        Args:
            action_history: List of (player_id, action) tuples
            state: Current game state
            
        Returns:
            Formatted action history
        """
        if not action_history:
            return "No actions taken yet."
        
        lines = []
        for player_id, action in action_history:
            action_str = state.action_to_string(player_id, action)
            lines.append(f"Player {player_id}: {action_str}")
        
        return "\n".join(lines)
    
    def generate_prompt(
        self,
        state: pyspiel.State,
        player_id: int,
        action_history: List[Tuple[int, int]]
    ) -> str:
        """
        Generate complete LLM prompt (can be overridden)
        
        Args:
            state: Game state
            player_id: Player ID
            action_history: Action history
            
        Returns:
            Complete prompt text
        """
        # 1. Rules
        rules = self.get_rules()
        
        # 2. Format state
        state_desc = self.format_state(state, player_id)
        
        # 3. Action history
        history_desc = self.format_action_history(action_history, state)
        
        # 4. Legal actions
        legal_actions = state.legal_actions(player_id)
        actions_desc = [
            f"{action}: {state.action_to_string(player_id, action)}"
            for action in legal_actions
        ]
        
        # 5. Build prompt
        prompt_parts = [
            f"You are playing {self.game_name}.",
            f"\n{rules}\n",
            f"\nCurrent game state:\n{state_desc}\n",
            f"\nAction history:\n{history_desc}\n",
            f"You are Player {player_id}.\n",
            f"Legal actions:\n" + "\n".join(actions_desc) + "\n",
            "Choose one action by responding with ONLY the action number.",
            "Your choice: "
        ]
        
        return "".join(prompt_parts)