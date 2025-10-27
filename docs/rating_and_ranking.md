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
    "ahc008": 1189,
    "ahc011": 1652,
    "ahc015": 2446,
    "ahc016": 1457,
    "ahc024": 1980,
    "ahc025": 1331,
    "ahc026": 1965,
    "ahc027": 1740,
    "ahc039": 2880,
    "ahc046": 2153,
}

average_performance = sum(performances.values()) / len(performances)
print(f"Average Performance: {average_performance}")
# Average Performance: 1879.3

# "ahc046" is the latest contest in ALE-Bench. You always need to set the final_contest to this value to report the rating.
final_rating = rating_calculator.calculate_rating(performances, "ahc046")
print(f"Calculated Rating: {final_rating}")
# Calculated Rating: 2222
```

## `RankingCalculator`
The `RankingCalculator` class allows you to determine a user's rank based on their average performance or overall rating, compared against a pre-compiled dataset of existing user rankings. This dataset is automatically downloaded from the Hugging Face Hub.

### Initialization
```python
from ale_bench.data import RankingCalculator

# Initialize with a minimum number of contest participations to be included in the ranking pool
ranking_calculator = RankingCalculator()  # Default minimum participation is 5
ranking_calculator = RankingCalculator(minimum_participation=10)  # Example with custom minimum participation
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

---
**`convert_rank_to_percentile`**

Converts a rank to a percentile based on the distribution of ranks.

*Parameters:*
- `rank (int)`: The rank to convert.
- `method (Literal["original", "hazen", "weibull"])`: The method to use for conversion. Defaults to `"weibull"`.
    - `"original"`: $\text{percentile} = 100.0 \times \frac{\text{rank}}{\text{\#active\_users}}$, capped at 100% when $\text{rank} = \text{\#active\_users} + 1$
    - `"hazen"`: $\text{percentile} = 100.0 \times \frac{(\text{rank} - 0.5)}{(\text{\#active\_users} + 1)}$
    - `"weibull"`: $\text{percentile} = 100.0 \times \frac{\text{rank}}{(\text{\#active\_users} + 2)}$

    > *Note:* The `"weibull"` method is recommended because it avoids 0%/100% endpoints (exclusive percentiles) and is widely used in the literature. We selected `"weibull"` as default rather than `"hazen"` because it provides a slightly more aligned to the original percentile calculation when the rank is higher. The original paper uses the `"original"` method, but it does not align well with statistical properties. All methods are acceptable as long as the method is documented.

*Returns:*
- `float`: The corresponding percentile.

### Example
```python
# Example average performance and rating
my_avg_performance = 1879.3
my_rating = 2222

print("The number of active users in the ranking pool:", ranking_calculator.num_active_users)
# The number of active users in the ranking pool: 2220

avg_perf_rank = ranking_calculator.calculate_avg_perf_rank(my_avg_performance)
avg_perf_rank_percentile = ranking_calculator.convert_rank_to_percentile(avg_perf_rank, "original")  # If you want to use the "original" method
avg_perf_rank_percentile = ranking_calculator.convert_rank_to_percentile(avg_perf_rank)  # Using the default "weibull" method
print(f"Rank based on Average Performance ({my_avg_performance}): {avg_perf_rank} ({avg_perf_rank_percentile:.1f}%)")
# Rank based on Average Performance (1879.3): 150 (6.8%)

rating_rank = ranking_calculator.calculate_rating_rank(my_rating)
rating_rank_percentile = ranking_calculator.convert_rank_to_percentile(rating_rank, "original")  # If you want to use the "original" method
rating_rank_percentile = ranking_calculator.convert_rank_to_percentile(rating_rank)  # Using the default "weibull" method
print(f"Rank based on Rating ({my_rating}): {rating_rank} ({rating_rank_percentile:.1f}%)")
# Rank based on Rating (2222): 191 (8.6%)
```
