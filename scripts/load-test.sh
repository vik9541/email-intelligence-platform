#!/bin/bash

# Load testing script

echo "🚀 Starting load test..."

# Create results directory
mkdir -p results

# 1. Baseline (10 users, 5 min)
echo "📊 Baseline test (10 users, 5 min)..."
locust -f tests/load_test.py:EmailProcessingUser \
  --host=http://localhost:8000 \
  --users=10 \
  --spawn-rate=2 \
  --run-time=5m \
  --headless \
  --csv=results/baseline

# 2. Stress test (100 users)
echo "💥 Stress test (100 users, 10 min)..."
locust -f tests/load_test.py:EmailProcessingUser \
  --host=http://localhost:8000 \
  --users=100 \
  --spawn-rate=10 \
  --run-time=10m \
  --headless \
  --csv=results/stress

# 3. Burst scenario
echo "⚡ Burst scenario (200 users)..."
locust -f tests/load_test.py:EmailBurstUser \
  --host=http://localhost:8000 \
  --users=200 \
  --spawn-rate=20 \
  --run-time=5m \
  --headless \
  --csv=results/burst

# 4. Heavy stress (500 users)
echo "🔥 Heavy stress test (500 users, 5 min)..."
locust -f tests/load_test.py:StressTestUser \
  --host=http://localhost:8000 \
  --users=500 \
  --spawn-rate=50 \
  --run-time=5m \
  --headless \
  --csv=results/heavy-stress

echo "✅ Load tests completed!"
echo "Results saved to: results/"
echo ""
echo "Summary:"
cat results/baseline_stats.csv | tail -1
cat results/stress_stats.csv | tail -1
cat results/burst_stats.csv | tail -1
cat results/heavy-stress_stats.csv | tail -1
