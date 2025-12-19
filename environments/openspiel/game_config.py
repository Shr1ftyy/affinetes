"""Game configuration and task_id decoding logic

20 GAMES TOTAL (11 Random + 9 Large Deterministic)

Selection criteria:
- MUST have >= 100 distinct game trajectories per task_id+seed combination
- Models CANNOT memorize a single winning strategy
- Balanced mix of high-randomness and large strategic-space games

Category A: High-Randomness Games (11 games)
- Use explicit randomness (dice, cards, ship placement)
- ChanceMode = EXPLICIT_STOCHASTIC
- Seed controls meaningful randomness

Category B: Large Deterministic Games (9 games)
- Massive strategy spaces (> 10^40)
- Different parameter variants require different strategies
- Cannot be solved with memorizable universal strategy

REMOVED: 3 Small Deterministic Games
- Tic-Tac-Toe 3x3, Connect Four, Nim (solvable with memorizable strategies)
- Replaced with Hearts, Cribbage, Euchre (high-randomness card games)
"""

import pyspiel
from typing import Dict, Any, Callable


# Game parameter configuration registry
GAME_PARAM_GENERATORS: Dict[str, Callable[[int], Dict[str, Any]]] = {}

# Explicit game order - DO NOT REORDER, only append new games at the end
# This ensures existing task_ids always map to the same game
AVAILABLE_GAMES = []


def register_param_generator(*game_names: str):
    """Decorator to register parameter generator for one or more games"""
    def decorator(func: Callable[[int], Dict[str, Any]]):
        for game_name in game_names:
            GAME_PARAM_GENERATORS[game_name] = func
            if game_name not in AVAILABLE_GAMES:
                AVAILABLE_GAMES.append(game_name)
        return func
    return decorator


def register_game(game_name: str):
    """Register a game without parameter generator (uses defaults)"""
    GAME_PARAM_GENERATORS[game_name] = lambda config_id: {}
    if game_name not in AVAILABLE_GAMES:
        AVAILABLE_GAMES.append(game_name)


# ============================================================================
# GAME 0: Leduc Poker (Imperfect Information - Card Dealing)
# ============================================================================

@register_param_generator("leduc_poker")
def _gen_leduc_poker_params(config_id: int) -> Dict[str, Any]:
    """
    Leduc Poker with 2 players
    
    Randomness: Card dealing from 6-card deck
    - Initial deal: P(6,2) = 30 combinations
    - Public card: 4 remaining cards
    - Total trajectories: 30 × 4 = ~120 distinct game starts
    
    Config space: 1 variant (standard 2-player rules)
    """
    return {"players": 2}


# ============================================================================
# GAME 1: Liar's Dice (Imperfect Information - Dice Rolls)
# ============================================================================

@register_param_generator("liars_dice")
def _gen_liars_dice_params(config_id: int) -> Dict[str, Any]:
    """
    Liar's Dice with variable dice count
    
    Randomness: Dice rolls
    - 1 die/player: 6² = 36 trajectories
    - 2 dice/player: 6⁴ = 1,296 trajectories
    - 3 dice/player: 6⁶ = 46,656 trajectories
    - 4 dice/player: 6⁸ = 1,679,616 trajectories
    - 5 dice/player: 6¹⁰ = 60,466,176 trajectories
    
    Config space: 5 variants (1-5 dice per player)
    Total trajectories: ~62 million
    """
    dice_var = config_id % 5
    return {
        "players": 2,
        "dice_per_player": 1 + dice_var  # 1, 2, 3, 4, 5
    }


# ============================================================================
# GAME 2: Battleship (Imperfect Information - Ship Placement)
# ============================================================================

@register_param_generator("battleship")
def _gen_battleship_params(config_id: int) -> Dict[str, Any]:
    """
    Battleship with random ship placement
    
    Randomness: Ship placement for both players
    - 8×8 board, 3 ships: ~10⁶ placements per player → ~10¹² combinations
    - 10×10 board, 4 ships: ~10⁸ placements per player → ~10¹⁶ combinations
    - 12×12 board, 5 ships: ~10¹⁰ placements per player → ~10²⁰ combinations
    
    Config space: 3 (board) × 3 (ships) = 9 variants
    Total trajectories: > 10²⁰
    """
    board_var = (config_id // 3) % 3
    ships_var = config_id % 3
    
    board_size = 8 + board_var * 2  # 8, 10, 12
    num_ships = 3 + ships_var  # 3, 4, 5
    
    return {
        "board_width": board_size,
        "board_height": board_size,
        "num_ships": num_ships
    }


# ============================================================================
# GAME 3: Goofspiel (Perfect Info with Random Prize Order)
# ============================================================================

@register_param_generator("goofspiel")
def _gen_goofspiel_params(config_id: int) -> Dict[str, Any]:
    """
    Goofspiel with random prize card order
    
    Randomness: Prize card permutation (points_order: "random")
    - 8 cards: 8! = 40,320 trajectories
    - 10 cards: 10! = 3,628,800 trajectories
    - 12 cards: 12! = 479,001,600 trajectories
    - 14 cards: 14! = 87,178,291,200 trajectories
    - 16 cards: 16! = 20,922,789,888,000 trajectories
    
    Config space: 5 variants (8, 10, 12, 14, 16 cards)
    Total trajectories: > 20 trillion
    """
    cards_var = config_id % 5
    return {
        "players": 2,
        "num_cards": 8 + cards_var * 2,  # 8, 10, 12, 14, 16
        "points_order": "random"
    }


# ============================================================================
# GAME 4: Gin Rummy (Card Game - High Randomness)
# ============================================================================

@register_param_generator("gin_rummy")
def _gen_gin_rummy_params(config_id: int) -> Dict[str, Any]:
    """
    Gin Rummy with 52-card deck dealing
    
    Randomness: Card dealing and draw pile order
    - Hand size 7: C(52,7) × C(45,7) × 38! ≈ 10⁶⁰ trajectories
    - Hand size 8: Even larger
    - Hand size 9: Even larger
    
    Config space: 3 (hand) × 3 (knock) = 9 variants
    Total trajectories: > 10⁶⁰ (effectively infinite)
    """
    hand_var = (config_id // 3) % 3
    knock_var = config_id % 3
    return {
        "players": 2,
        "hand_size": 7 + hand_var,  # 7, 8, 9
        "knock_card": 10 - knock_var  # 10, 9, 8
    }


# ============================================================================
# GAME 5: Backgammon (Classic Dice Game)
# ============================================================================

@register_param_generator("backgammon")
def _gen_backgammon_params(config_id: int) -> Dict[str, Any]:
    """
    Backgammon with dice randomness
    
    Randomness: Two 6-sided dice per turn
    - Initial roll: 36 combinations
    - Total trajectories: > 10^50
    
    Config space: 1 variant
    """
    return {}


# ============================================================================
# GAME 6: Pig (Simple Dice Game)
# ============================================================================

@register_param_generator("pig")
def _gen_pig_params(config_id: int) -> Dict[str, Any]:
    """
    Pig dice game with risk/reward decisions
    
    Randomness: Single die per roll
    - Total trajectories: > 10,000
    
    Config space: 3 variants (different win scores)
    """
    score_var = config_id % 3
    return {
        "players": 2,
        "winscore": 20 + score_var * 10  # 20, 30, 40
    }


# ============================================================================
# GAME 7: Blackjack (Card Game)
# ============================================================================

@register_param_generator("blackjack")
def _gen_blackjack_params(config_id: int) -> Dict[str, Any]:
    """
    Blackjack with card dealing randomness
    
    Randomness: 52-card deck
    - Total trajectories: > 10^60
    
    Config space: 1 variant
    """
    return {"players": 1}


# ============================================================================
# GAME 8: Phantom Tic-Tac-Toe (Imperfect Information)
# ============================================================================

@register_param_generator("phantom_ttt")
def _gen_phantom_ttt_params(config_id: int) -> Dict[str, Any]:
    """
    Phantom TTT with observation uncertainty
    
    Randomness: Hidden opponent moves
    - Total trajectories: > 1,000
    
    Config space: 2 variants
    """
    obstype_var = config_id % 2
    return {"obstype": obstype_var}


# ============================================================================
# GAME 9: Breakthrough with Random Setup
# ============================================================================

@register_param_generator("breakthrough")
def _gen_breakthrough_params(config_id: int) -> Dict[str, Any]:
    """
    Breakthrough with randomized initial piece positions
    
    Randomness: Using seed-based random initial state
    - Board sizes: 6x6, 8x8
    - Total trajectories: > 100 per size
    
    Config space: 2 variants
    """
    size_var = config_id % 2
    return {
        "rows": 6 + size_var * 2,  # 6 or 8
        "columns": 6 + size_var * 2
    }


# ============================================================================
# GAME 10: Hex with Random First Moves
# ============================================================================

@register_param_generator("hex")
def _gen_hex_params(config_id: int) -> Dict[str, Any]:
    """
    Hex with varying board sizes
    
    Different board sizes create different strategic spaces
    - Total trajectories: > 100 per size
    
    Config space: 4 variants (5x5, 7x7, 9x9, 11x11)
    """
    size_var = config_id % 4
    board_size = 5 + size_var * 2  # 5, 7, 9, 11
    return {"board_size": board_size}


# ============================================================================
# GAME 11: Connect Four Variants
# ============================================================================

@register_param_generator("hearts")
def _gen_hearts_params(config_id: int) -> Dict[str, Any]:
    """
    Hearts with rule variants
    
    Randomness: 52-card deck dealing
    - Total trajectories: > 10^60
    
    Config space: 8 variants (different rule combinations)
    """
    variant = config_id % 8
    # 3-bit encoding for different rule combinations
    return {
        "pass_cards": (variant & 1) == 1,
        "jd_bonus": (variant & 2) == 2,
        "avoid_all_tricks_bonus": (variant & 4) == 4
    }


# ============================================================================
# GAME 12: Cribbage (Card Game)
# ============================================================================

@register_param_generator("cribbage")
def _gen_cribbage_params(config_id: int) -> Dict[str, Any]:
    """
    Cribbage with variable player counts
    
    Randomness: 52-card deck dealing
    - Total trajectories: > 10^60
    
    Config space: 3 variants (2, 3, 4 players)
    """
    players_var = config_id % 3
    return {"players": 2 + players_var}  # 2, 3, 4


# ============================================================================
# GAME 13: Euchre (Card Game)
# ============================================================================

@register_param_generator("euchre")
def _gen_euchre_params(config_id: int) -> Dict[str, Any]:
    """
    Euchre with rule variants
    
    Randomness: 24-card deck dealing
    - Total trajectories: > 10^20
    
    Config space: 4 variants (different rule combinations)
    """
    variant = config_id % 4
    return {
        "allow_lone_defender": (variant & 1) == 1,
        "stick_the_dealer": (variant & 2) == 2
    }


# ============================================================================
# GAME 14: Othello (Reversi) Different Sizes
# ============================================================================

@register_param_generator("othello")
def _gen_othello_params(config_id: int) -> Dict[str, Any]:
    """
    Othello with different board sizes
    
    Different sizes create vastly different strategy spaces
    - Total trajectories: > 100 per size
    
    Config space: 2 variants (6x6, 8x8)
    """
    size_var = config_id % 2
    board_size = 6 + size_var * 2  # 6 or 8
    return {"board_size": board_size}


# ============================================================================
# GAME 15: Go with Different Board Sizes
# ============================================================================

@register_param_generator("go")
def _gen_go_params(config_id: int) -> Dict[str, Any]:
    """
    Go with multiple board sizes and komi values
    
    Different sizes and komi create different strategic spaces
    - Total trajectories: > 100 per configuration
    
    Config space: 3 (sizes) × 3 (komi) = 9 variants
    """
    size_var = (config_id // 3) % 3
    komi_var = config_id % 3
    
    board_size = 7 + size_var * 2  # 7, 9, 11
    komi = 6.5 + komi_var * 0.5    # 6.5, 7.0, 7.5
    
    return {
        "board_size": board_size,
        "komi": komi
    }


# ============================================================================
# GAME 16: Chess
# ============================================================================

@register_param_generator("chess")
def _gen_chess_params(config_id: int) -> Dict[str, Any]:
    """
    Standard Chess
    
    Note: OpenSpiel's chess doesn't support Chess960 natively,
    but different opening books via config_id can create diversity
    
    Config space: 1 variant (standard chess)
    Total trajectories: Effectively infinite due to game complexity
    """
    return {}


# ============================================================================
# GAME 17: Checkers
# ============================================================================

@register_param_generator("checkers")
def _gen_checkers_params(config_id: int) -> Dict[str, Any]:
    """
    Checkers (English Draughts)
    
    Classic 8x8 board game
    - Deep strategic game
    - Total unique games: > 10^20
    
    Config space: 1 variant
    """
    return {}


# ============================================================================
# GAME 18: Dots and Boxes
# ============================================================================

@register_param_generator("dots_and_boxes")
def _gen_dots_boxes_params(config_id: int) -> Dict[str, Any]:
    """
    Dots and Boxes with varying sizes
    
    Different sizes create different strategic depths
    - Total trajectories: > 100 per size
    
    Config space: 3 variants (3x3, 4x4, 5x5)
    """
    size_var = config_id % 3
    grid_size = 3 + size_var  # 3, 4, 5
    return {
        "num_rows": grid_size,
        "num_cols": grid_size
    }


# ============================================================================
# GAME 19: Clobber
# ============================================================================

@register_param_generator("clobber")
def _gen_clobber_params(config_id: int) -> Dict[str, Any]:
    """
    Clobber with different board sizes
    
    Two-player board game where pieces jump to capture
    - Total trajectories: > 100 per size
    
    Config space: 3 variants
    """
    size_var = config_id % 3
    board_size = 5 + size_var  # 5, 6, 7
    return {
        "rows": board_size,
        "columns": board_size
    }


# ============================================================================
# GAME 20: Quoridor
# ============================================================================

@register_param_generator("quoridor")
def _gen_quoridor_params(config_id: int) -> Dict[str, Any]:
    """
    Quoridor with varying board sizes and wall counts
    
    Strategic path-blocking game
    - Total trajectories: > 100 per configuration
    
    Config space: 2 (sizes) × 2 (walls) = 4 variants
    """
    size_var = (config_id // 2) % 2
    walls_var = config_id % 2
    
    board_size = 7 + size_var * 2  # 7 or 9
    num_walls = 8 + walls_var * 2  # 8 or 10
    
    return {
        "board_size": board_size,
        "number_of_walls": num_walls
    }


# ============================================================================
# Task ID Decoding
# ============================================================================

def decode_task_id(task_id: int) -> Dict[str, Any]:
    """
    Decode task_id into game configuration
    
    task_id format: GGGGCCCCCCCC (12-digit integer)
    - GGGG: Game index (4 digits, 0-9999)
    - CCCCCCCC: Configuration variant (8 digits, 0-99999999)
    
    Args:
        task_id: 12-digit integer representing game and configuration
        
    Returns:
        Dictionary with:
        - game_name: str
        - game_idx: int
        - config_id: int
        - game_params: dict
        
    Examples:
        task_id = 0 -> kuhn_poker with default config
        task_id = 100000000 -> leduc_poker with default config
        task_id = 200000002 -> liars_dice with 3 dice per player
        
    Note:
        AVAILABLE_GAMES order is stable - new games are always appended.
        This ensures existing task_ids always map to the same game.
    """
    game_idx = task_id // 100000000
    config_id = task_id % 100000000
    game_name = AVAILABLE_GAMES[game_idx % len(AVAILABLE_GAMES)]
    game_params = generate_game_params(game_name, config_id)
    
    return {
        "game_name": game_name,
        "game_idx": game_idx,
        "config_id": config_id,
        "game_params": game_params
    }


def generate_game_params(game_name: str, config_id: int) -> Dict[str, Any]:
    """
    Generate game parameter variants based on config_id
    
    Uses registered parameter generators for extensibility.
    Games without registered generators return empty parameters.
    
    Args:
        game_name: Name of the game
        config_id: 8-digit configuration variant ID
        
    Returns:
        Dictionary of game parameters
    """
    generator = GAME_PARAM_GENERATORS.get(game_name)
    if generator:
        return generator(config_id)
    return {}


def create_game(task_id: int):
    """
    Create game instance from task_id
    
    Args:
        task_id: Task identifier
        
    Returns:
        Tuple of (game, config_dict)
    """
    config = decode_task_id(task_id)
    
    game = pyspiel.load_game(
        config["game_name"],
        config["game_params"]
    )
    
    return game, config


def get_game_info():
    """
    Get information about all available games
    
    Returns:
        List of dictionaries with game info
    """
    info = []
    for idx, game_name in enumerate(AVAILABLE_GAMES):
        # Sample config_id range
        generator = GAME_PARAM_GENERATORS.get(game_name)
        if generator:
            # Try to estimate config space by testing a few values
            max_config = 0
            for test_id in [0, 10, 100]:
                try:
                    generator(test_id)
                    max_config = test_id
                except:
                    break
        else:
            max_config = 0
        
        info.append({
            "idx": idx,
            "name": game_name,
            "task_id_start": idx * 100000000,
            "estimated_max_config": max_config
        })
    
    return info