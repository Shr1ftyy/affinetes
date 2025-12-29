import itertools
import random
import re
import uuid

from base.data import Data


class GameOf24Generator:
    """Generate Game of 24 challenges with seed-based determinism"""

    def __init__(self):
        # Prompt templates
        self.prompts_en = [
            "Given the numbers {numbers}, apply the arithmetic operations {operators} to get the result of {result}.",
            "Using the numbers {numbers}, figure out how to combine them with the arithmetic operations {operators} to equal {result}.",
            "Try to make {result} by performing arithmetic operations {operators} on the numbers {numbers}.",
            "Can you use the numbers {numbers} and the arithmetic operations {operators} to get {result}?",
        ]

        self.prompts_zh = [
            "给定数字 {numbers}，使用算术运算 {operators} 得到 {result}。",
            "用数字 {numbers}，想办法通过算术运算 {operators} 计算出 {result}。",
            "你能用数字 {numbers} 和算术运算 {operators} 算出 {result} 吗？",
            "试试用算术运算 {operators} 结合数字 {numbers} 计算出 {result}。",
        ]

    def generate(
        self,
        seed: int = None,
        num_of_numbers: int = 4,
        result: int = 24,
        min_candidate: int = 1,
        max_candidate: int = 9,
        operators: list = None,
        max_attempts: int = 1000
    ):
        """
        Generate a single Game of 24 challenge

        Args:
            seed: Random seed for deterministic generation
            num_of_numbers: Number of numbers to use (default: 4)
            result: Target result (default: 24)
            min_candidate: Minimum number value (default: 1)
            max_candidate: Maximum number value (default: 9)
            operators: List of allowed operators (default: ["+", "-", "*", "/"])
            max_attempts: Maximum attempts to find valid challenge

        Returns:
            Data object containing question, answer, and metadata
        """
        if operators is None:
            operators = ["+", "-", "*", "/"]

        rng = random.Random(seed) if seed is not None else random.Random()

        for attempt in range(max_attempts):
            # Generate attempt seed
            attempt_seed = seed + attempt if seed is not None else None
            if attempt_seed is not None:
                rng.seed(attempt_seed)

            # Generate random numbers
            numbers = [
                rng.randint(min_candidate, max_candidate)
                for _ in range(num_of_numbers)
            ]
            numbers = sorted(numbers)

            # Check if solvable
            solutions = self._find_all_solutions(numbers, operators, result)
            if not solutions:
                continue

            # Generate question
            question = self._format_question(numbers, operators, result, rng)

            # Build metadata
            metadata = {
                "seed": seed,
                "trace_id": str(uuid.uuid4()),
                "numbers": numbers,
                "solutions_count": len(solutions),
                "operators": operators,
                "result": result,
                "num_of_numbers": num_of_numbers,
            }

            return Data(
                question=question,
                answer="",  # No reference answer needed, verification is by evaluation
                metadata=metadata
            )

        raise ValueError(
            f"Failed to generate valid Game of 24 challenge after {max_attempts} attempts"
        )

    def _find_all_solutions(self, numbers, operators, target_result):
        """Find all possible solutions for given numbers"""
        solutions = set()

        for nums in itertools.permutations(numbers):
            for ops in itertools.product(operators, repeat=len(nums) - 1):
                cur_nums = list(nums)
                cur_ops = list(ops)

                # Evaluate left to right
                while cur_ops:
                    op = cur_ops.pop(0)
                    cur_num1 = cur_nums.pop(0)
                    cur_num2 = cur_nums.pop(0)

                    try:
                        result = eval(f"{cur_num1} {op} {cur_num2}")
                        cur_nums.insert(0, result)
                    except (ZeroDivisionError, ValueError):
                        break

                # Check if result matches target
                if cur_nums and abs(cur_nums[0] - target_result) < 1e-10:
                    solutions.add(f"nums: {nums}, ops: {ops}")

        return list(solutions)

    def _format_question(self, numbers, operators, result, rng):
        """Format the question prompt"""
        # Randomly choose language
        use_chinese = rng.choice([True, False])

        if use_chinese:
            prompt = rng.choice(self.prompts_zh)
            instruction = "在回答的最后，请输出一个 ```python 代码块。代码块中仅包含一个代表答案的表达式，并且该表达式可以直接被 Python 中的 eval() 函数求值。"
        else:
            prompt = rng.choice(self.prompts_en)
            instruction = " At the end of your response, please output a ```python code block. The code block should contain only a single expression representing the answer, which can be directly evaluated using Python's eval() function."

        prompt = prompt.format(
            numbers=numbers,
            operators=operators,
            result=result
        )

        return prompt + instruction

    def extract_answer(self, test_solution: str) -> str:
        """
        Extract answer from model response

        Looks for ```python code block and extracts the expression
        """
        regex_pattern = "```python.*?```"
        matches = re.findall(regex_pattern, test_solution, re.DOTALL)

        if matches:
            return matches[-1].replace("```python", "").replace("```", "").strip()

        return ""
