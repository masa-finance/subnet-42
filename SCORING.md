# Subnet 42 Scoring System

## Overview

The Subnet 42 scoring system evaluates miner performance by analyzing telemetry data collected from their TEE (Trusted Execution Environment) workers. This scoring mechanism is designed to reward miners that successfully process web scraping and Twitter data collection tasks, while penalizing those with errors or failed operations.

## Telemetry Collection Process

1. **Telemetry Data Sources**: Each registered TEE worker periodically reports telemetry data that includes:
   - Web scraping success and failure counts
   - Twitter data collection metrics (tweets, profiles, etc.)
   - Error counts by type (auth errors, rate limit errors, etc.)
   - Operational timestamps

2. **Delta-based Calculations**: Rather than using absolute values, the system calculates *deltas* (changes) between telemetry snapshots to measure recent performance:
   - The system stores multiple telemetry snapshots over time
   - Scores are based on changes between oldest and newest snapshots
   - This approach rewards recent activity and improvements

3. **TEE Restart Handling**: When a TEE worker restarts, telemetry counters may reset to zero, causing negative deltas. The system:
   - Detects negative delta values in any telemetry metric
   - Deletes all telemetry for that node to start fresh
   - Ensures all deltas used for scoring are non-negative (using `max(0, delta)`)

## Scoring Algorithm

The scoring calculation follows these key steps:

1. **Telemetry Data Collection**: For each node:
   - Retrieve telemetry data snapshots
   - Calculate deltas between oldest and newest records
   - Handle any negative deltas (TEE restarts)
   - Store normalized delta values for scoring

2. **Key Performance Metrics**: The score primarily considers:
   - `web_success`: Successful web scraping operations
   - `twitter_returned_tweets`: Successfully retrieved tweets
   - `twitter_returned_profiles`: Successfully retrieved Twitter profiles

3. **Kurtosis Weighting**: The system applies a custom kurtosis-like function to weight top performers more heavily:
   ```python
   def apply_kurtosis_custom(
       x,
       top_percentile=90,
       reward_factor=0.4,
       steepness=2.0,
       center_sensitivity=0.5,
       boost_factor=0.2
   ):
   ```
   This function:
   - Applies higher weights to nodes in the top percentile (default 90%)
   - Uses configurable parameters to adjust the curve's shape
   - Avoids excessively punishing nodes that are performing adequately but not exceptionally

4. **Metric Normalization**: Each metric is normalized to ensure fair comparison:
   - Values are scaled to a 0-1 range using min-max scaling
   - Nodes with zero values receive minimal but non-zero scores
   - Extreme outliers are handled appropriately

5. **Score Combination**: The final score combines weighted metrics:
   - Web success, tweet retrieval, and profile retrieval each contribute to the final score
   - Nodes with balanced performance across all metrics receive higher scores
   - Nodes with exceptional performance in one area but poor in others receive moderate scores

6. **Validation**: Scores undergo validation checks:
   - Nodes with extremely low activity receive minimal scores
   - Scores are normalized to sum to 1.0 across all nodes (for setting weights)
   - Invalid or disconnected nodes receive zero scores

## Weight Setting

The calculated scores are used to set weights on the Bittensor blockchain:

1. **Weight Conversion**:
   - Scores are converted to weights suitable for the blockchain
   - The weights determine how much TAO (the network token) each miner earns

2. **Update Frequency**:
   - Weights are updated at regular intervals
   - A minimum interval between updates prevents excessive blockchain transactions
   - Updates are retried up to 3 times if they fail

3. **Notification**:
   - Miners receive score reports with their performance metrics
   - These reports provide transparency and help miners optimize their operations

## Performance Optimization

To maximize your score as a miner:

1. **Maintain Uptime**: Keep your TEE worker running continuously to avoid restarts
2. **Minimize Errors**: Reduce authentication errors, rate limits, and other failures
3. **Maximize Successful Operations**: Focus on achieving high success rates for X and web scraping
4. **Balance Performance**: Aim for good performance across all metrics rather than excelling in just one
5. **Monitor Telemetry**: Regularly check your telemetry data to identify and address issues

## Technical Implementation

The scoring system is implemented across several components:

1. **WeightsManager**: Handles the overall weight calculation process
2. **NodeManager**: Manages connections to miners and collects telemetry
3. **TelemetryStorage**: Stores and retrieves telemetry data
4. **ScoringFunctions**: Implements various mathematical scoring functions

The core of the scoring logic is in the `calculate_weights` method of the `WeightsManager` class, which:
1. Processes delta telemetry data
2. Extracts and normalizes metrics
3. Applies kurtosis weighting
4. Calculates final scores
5. Converts scores to weights

## Conclusion

The Subnet 42 scoring system is designed to fairly reward miners based on their actual performance in web scraping and Twitter data collection. By using delta-based metrics and kurtosis weighting, the system encourages continuous improvement and rewards both consistency and excellence. 