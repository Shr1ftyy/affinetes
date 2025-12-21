"""LLM Bot implementation for OpenSpiel"""

import pyspiel
import numpy as np
import asyncio
import re
import concurrent.futures
import time
from typing import Callable, Awaitable, Tuple, Optional


class LLMBot(pyspiel.Bot):
    """
    Wraps LLM as an OpenSpiel Bot

    This is the only custom Bot implementation needed - all other bots
    (random, MCTS, etc.) are reused from OpenSpiel's built-in implementations.
    """

    def __init__(
        self,
        game: pyspiel.Game,
        player_id: int,
        llm_chat_fn: Callable[[str], Awaitable[Tuple[str, dict]]],
        rng_seed: int,
    ):
        """
        Initialize LLM Bot

        Args:
            game: pyspiel.Game instance
            player_id: Player ID (0 or 1)
            llm_chat_fn: Async function to call LLM API, returns (content, usage)
            rng_seed: Random seed for fallback action selection
        """
        pyspiel.Bot.__init__(self)
        self._game = game
        self._player_id = player_id
        self._llm_chat_fn = llm_chat_fn
        self._rng = np.random.RandomState(rng_seed)

        # Track action history for prompt construction
        self._action_history = []

        # Track conversation for debugging/analysis
        self._conversation = []

        # Track last error only (not accumulating all errors)
        self._last_error: Optional[dict] = None

        # Track accumulated usage statistics
        self._total_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    def restart_at(self, state):
        """Reset to new game"""
        self._action_history = []
        self._conversation = []
        self._last_error = None
        self._total_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    def inform_action(self, state, player_id, action):
        """Record other players' actions"""
        self._action_history.append((player_id, action))

    def step(self, state):
        """
        Core method: choose action based on current state

        This is called by evaluate_bots during game play.
        """
        # 1. Generate prompt (state description + legal actions)
        prompt = self._generate_prompt(state)

        # 2. Call LLM with retry mechanism (bridge async to sync using thread pool)
        # Run async function in a separate thread with its own event loop
        # This avoids conflicts with existing event loops
        def run_async_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._llm_chat_fn(prompt))
                # Ensure all pending tasks complete before closing
                pending = asyncio.all_tasks(loop)
                if pending:
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                return result
            finally:
                # Properly shutdown async generators before closing loop
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()

        max_retries = 3
        retry_delay = 1.0
        call_timeout = 120  # 2 minutes per LLM call

        response = None
        usage = None

        for attempt in range(max_retries):
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_async_in_thread)
                    response, usage = future.result(timeout=call_timeout)

                self._conversation.append({"role": "user", "content": prompt})
                self._conversation.append({"role": "assistant", "content": response})

                # Accumulate usage statistics
                if usage:
                    self._total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                    self._total_usage["completion_tokens"] += usage.get(
                        "completion_tokens", 0
                    )
                    self._total_usage["total_tokens"] += usage.get("total_tokens", 0)

                break

            except concurrent.futures.TimeoutError:
                error_msg = f"LLM call timeout after {call_timeout}s"
                
                if attempt < max_retries - 1:
                    print(
                        f"LLM call timed out (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                else:
                    print(
                        f"LLM call timed out after {max_retries} attempts, falling back to random action"
                    )
                    self._last_error = {
                        "prompt": prompt,
                        "error": error_msg,
                        "attempts": max_retries,
                    }
                    legal_actions = state.legal_actions(self._player_id)
                    return self._rng.choice(legal_actions)
                    
            except Exception as e:
                import traceback

                error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

                if attempt < max_retries - 1:
                    print(
                        f"LLM call failed (attempt {attempt + 1}/{max_retries}): {e}, retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                else:
                    print(
                        f"LLM call failed after {max_retries} attempts: {e}, falling back to random action"
                    )
                    self._last_error = {
                        "prompt": prompt,
                        "error": error_msg,
                        "attempts": max_retries,
                    }
                    legal_actions = state.legal_actions(self._player_id)
                    return self._rng.choice(legal_actions)

        # 3. Parse action from response
        legal_actions = state.legal_actions(self._player_id)
        action = self._parse_action(response, legal_actions)

        # 4. Record action in history
        self._action_history.append((self._player_id, action))

        return action

    def _generate_prompt(self, state):
        """
        Generate LLM prompt with game-specific formatting
        
        For Liar's Dice: provides comprehensive rules on first turn,
        shows only player's own dice, and formats state clearly.
        """
        game_name = self._game.get_type().short_name
        
        # Check if this is the first turn (empty conversation)
        is_first_turn = len(self._conversation) == 0
        
        # Game-specific prompt generation
        if game_name == "liars_dice":
            return self._generate_liars_dice_prompt(state, is_first_turn)
        else:
            return self._generate_default_prompt(state, game_name)
    
    def _generate_default_prompt(self, state, game_name):
        """Default prompt format for most games"""
        state_str = str(state)
        legal_actions = state.legal_actions(self._player_id)
        actions_desc = [
            f"{action}: {state.action_to_string(self._player_id, action)}"
            for action in legal_actions
        ]

        prompt = f"""You are playing {game_name}.

Current game state:
{state_str}

You are Player {self._player_id}.

Legal actions:
{chr(10).join(actions_desc)}

Choose one action by responding with ONLY the action number.
Your choice: """
        
        return prompt
    
    def _generate_liars_dice_prompt(self, state, is_first_turn):
        """
        Generate comprehensive Liar's Dice prompt
        
        - First turn: includes full game rules
        - Shows only player's own dice
        - Clear bid history and current situation
        """
        # Parse state to extract player's dice and bid history
        state_str = str(state)
        parts = state_str.split()
        
        # Extract player's dice (first sequence of digits)
        my_dice_str = parts[0] if parts else ""
        my_dice = [int(d) for d in my_dice_str] if my_dice_str.isdigit() else []
        
        # Extract bid history (remaining parts)
        bid_history = parts[1:] if len(parts) > 1 else []
        
        # Get legal actions
        legal_actions = state.legal_actions(self._player_id)
        actions_desc = [
            f"{action}: {state.action_to_string(self._player_id, action)}"
            for action in legal_actions
        ]
        
        # Count total dice in game
        num_players = self._game.num_players()
        dice_per_player = len(my_dice)
        total_dice = num_players * dice_per_player
        
        # Build comprehensive prompt
        if is_first_turn:
            # First turn: include full rules explanation
            prompt = f"""You are playing LIAR'S DICE - A bluffing and deduction game.

=== GAME RULES ===
Players: {num_players} players
Dice per player: {dice_per_player} dice (values 1-6)
Total dice in game: {total_dice} dice

HOW TO PLAY:
1. Each player has their own dice (hidden from others)
2. Players take turns making BIDS about the total dice across ALL players
3. A bid is "quantity-face" (e.g., "3-5" means "at least three 5s exist among all {total_dice} dice")
4. SPECIAL RULE: 1s are WILD - they count as any face value
5. Each bid must be HIGHER than the previous:
   - Higher quantity with any face, OR
   - Same quantity with higher face value
6. Instead of bidding higher, you can call "Liar" to challenge the previous bid
7. If you call "Liar": count all dice; if bid was FALSE, bidder loses; if TRUE, caller loses

STRATEGY TIPS:
- You can see your own {dice_per_player} dice
- Estimate what others might have (each die has 1/6 chance of any face)
- Remember: 1s are wild and count toward any face
- Conservative bids are safer; aggressive bids apply pressure

=== YOUR CURRENT SITUATION ===
Your dice: {', '.join(str(d) for d in my_dice)}
Your dice count by face:
"""
            # Add dice count analysis
            for face in range(1, 7):
                count = my_dice.count(face)
                prompt += f"  {face}s: {count} dice"
                if face == 1 and count > 0:
                    prompt += " (WILD - counts as any face)"
                prompt += "\n"
            
            prompt += f"""
Bid history: None (you're making the opening bid)

YOUR TASK:
Make an opening bid. Choose conservatively based on your dice.
Since you have {my_dice.count(1)} wild 1s, you can bid on faces you don't have.

Legal actions:
{chr(10).join(actions_desc)}

Respond with ONLY the action number.
Your choice: """
        
        else:
            # Subsequent turns: concise prompt
            current_bid = bid_history[-1] if bid_history else "None"
            
            prompt = f"""LIAR'S DICE - Player {self._player_id}'s Turn

Your dice ({dice_per_player} dice): {', '.join(str(d) for d in my_dice)}
Total dice in game: {total_dice}
Current bid: {current_bid}

Bid history: {' → '.join(bid_history) if bid_history else 'None'}

Remember: 1s are WILD (count as any face)

Legal actions:
{chr(10).join(actions_desc)}

Respond with ONLY the action number.
Your choice: """
        
        return prompt

    def _parse_action(self, response: str, legal_actions: list) -> int:
        """
        Parse LLM response to extract action ID

        Args:
            response: LLM response text
            legal_actions: List of legal action IDs

        Returns:
            Action ID (falls back to random if parsing fails)
        """
        # Try to extract number from response
        match = re.search(r"\b(\d+)\b", response.strip())
        if match:
            action = int(match.group(1))
            if action in legal_actions:
                return action

        # Parsing failed, choose random action
        return self._rng.choice(legal_actions)

    def get_conversation(self):
        """Get conversation history"""
        return self._conversation

    def get_last_error(self):
        """Get last error (if any)"""
        return self._last_error

    def get_total_usage(self):
        """Get accumulated usage statistics"""
        return self._total_usage
