"""LLM Bot implementation for OpenSpiel"""

import pyspiel
import numpy as np
import asyncio
import re
import concurrent.futures
import time
from typing import Callable, Awaitable, Tuple, Optional

from game_rules import get_game_rules
from base_agent import BaseGameAgent


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
        agent: Optional[BaseGameAgent] = None,
    ):
        """
        Initialize LLM Bot

        Args:
            game: pyspiel.Game instance
            player_id: Player ID (0 or 1)
            llm_chat_fn: Async function to call LLM API, returns (content, usage)
            rng_seed: Random seed for fallback action selection
            agent: Optional BaseGameAgent for game-specific logic
        """
        pyspiel.Bot.__init__(self)
        self._game = game
        self._player_id = player_id
        self._llm_chat_fn = llm_chat_fn
        self._rng = np.random.RandomState(rng_seed)
        self._agent = agent  # NEW: Store agent for prompt generation

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

        response = None
        usage = None

        for attempt in range(max_retries):
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_async_in_thread)
                    response, usage = future.result()

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
        Generate LLM prompt

        Uses Agent if available, otherwise falls back to default logic.
        """
        # Use agent's generate_prompt if available
        if self._agent:
            return self._agent.generate_prompt(
                state=state,
                player_id=self._player_id,
                action_history=self._action_history
            )
        
        # Fallback to original logic
        game_name = self._game.get_type().short_name

        # Load game rules if available
        game_rules = get_game_rules(game_name)

        # Use OpenSpiel's built-in state description
        state_str = str(state)

        # Get legal actions with descriptions
        legal_actions = state.legal_actions(self._player_id)
        actions_desc = [
            f"{action}: {state.action_to_string(self._player_id, action)}"
            for action in legal_actions
        ]

        # Construct prompt with rules if available
        prompt_parts = [f"You are playing {game_name}."]
        
        if game_rules:
            prompt_parts.append(f"\n{game_rules}\n")
        
        prompt_parts.extend([
            f"\nCurrent game state:\n{state_str}\n",
            f"You are Player {self._player_id}.\n",
            f"Legal actions:\n{chr(10).join(actions_desc)}\n",
            "Choose one action by responding with ONLY the action number.",
            "Your choice: "
        ])
        
        return "".join(prompt_parts)

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
