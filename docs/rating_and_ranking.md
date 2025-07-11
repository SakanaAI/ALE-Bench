# `RatingCalculator` and `RankingCalculator`

ALE-Bench provides utilities for calculating ratings and rankings based on contest performance.

## `RatingCalculator`
The `RatingCalculator` class helps estimate a user's rating based on their performance in various contests. It uses a formula similar to the one described in the [official AHC rating document](https://img.atcoder.jp/file/AHC_rating_v2.pdf).

### Initialization
```python
from ale_bench.data import RatingCalculator

rating_calculator = RatingCalculator()
```

### Core Methods
**`calculate_rating`**

Calculates the rating based on a dictionary of performances and the ID of the final contest considered.

*Parameters:*
- `performances (dict[str, int])`: A dictionary where keys are problem IDs (e.g., "ahc001") and values are the performance scores achieved in those problems.
- `final_contest (str)`: The problem ID of the last contest to be included in the rating calculation. Performances from contests ending after this date will be ignored.

*Returns:*
- `int`: The calculated rating, rounded to the nearest integer.

### Example
```python
performances = {
    "ahc001": 2000,
    "ahc002": 2200,
    "ahc003": 1800
}
# Assuming ahc003 is the latest contest to consider for this rating calculation
final_rating = rating_calculator.calculate_rating(performances, "ahc003")
print(f"Calculated Rating: {final_rating}")
```

## `RankingCalculator`
The `RankingCalculator` class allows you to determine a user's rank based on their average performance or overall rating, compared against a pre-compiled dataset of existing user rankings. This dataset is automatically downloaded from the Hugging Face Hub.

### Initialization
```python
from ale_bench.data import RankingCalculator

# Initialize with a minimum number of contest participations to be included in the ranking pool
# (default is 5)
ranking_calculator = RankingCalculator(minimum_participation=5)
```

### Core Methods

**`calculate_avg_perf_rank`**

Calculates the rank based on average performance.

*Parameters:*
- `avg_perf (float)`: The average performance score.

*Returns:*
- `int`: The calculated rank. Lower is better.

---
**`calculate_rating_rank`**

Calculates the rank based on an overall rating.

*Parameters:*
- `rating (int)`: The overall rating.

*Returns:*
- `int`: The calculated rank. Lower is better.

### Example
```python
# Example average performance and rating
my_avg_performance = 2150.75
my_rating = 2345

avg_perf_rank = ranking_calculator.calculate_avg_perf_rank(my_avg_performance)
rating_rank = ranking_calculator.calculate_rating_rank(my_rating)

print(f"Rank based on Average Performance ({my_avg_performance}): {avg_perf_rank}")
print(f"Rank based on Rating ({my_rating}): {rating_rank}")
```
