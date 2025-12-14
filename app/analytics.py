"""Business analytics and metrics tracking."""

from datetime import datetime

from prometheus_client import Counter, Gauge, Histogram, Info

# Business metrics
emails_processed_total = Counter(
    'emails_processed_total',
    'Total emails processed',
    ['status', 'sender_domain', 'action_type']
)

processing_time = Histogram(
    'email_processing_time_seconds',
    'Email processing time distribution',
    ['status', 'action_type'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

success_rate = Gauge(
    'email_success_rate',
    'Percentage of successful email processing (24h rolling)'
)

top_senders = Gauge(
    'email_top_senders',
    'Email count by top sender domains',
    ['sender_domain']
)

peak_hours = Gauge(
    'email_peak_hours',
    'Email processing count by hour',
    ['hour']
)

action_distribution = Counter(
    'email_action_distribution',
    'Distribution of email actions',
    ['action_type', 'status']
)

average_latency = Gauge(
    'email_average_latency_ms',
    'Average processing latency (last 5 min)',
    ['action_type']
)

queue_depth = Gauge(
    'email_queue_depth',
    'Current processing queue depth'
)

retry_count = Counter(
    'email_retry_total',
    'Total retries for failed processing',
    ['action_type', 'error_type']
)

# System metrics
active_workers = Gauge(
    'active_workers',
    'Number of active processing workers'
)

cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate percentage'
)

database_query_duration = Histogram(
    'database_query_duration_seconds',
    'Database query duration',
    ['query_type'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0)
)

# Application info
app_info = Info('email_intelligence_app', 'Application information')


def track_email_processing(
    email_id: str,
    sender: str,
    status: str,
    duration: float,
    action_type: str = "unknown"
):
    """Track email processing metrics.

    Args:
        email_id: Unique email identifier
        sender: Email sender address
        status: Processing status (success/failure/pending)
        duration: Processing time in seconds
        action_type: Type of action performed
    """
    # Extract sender domain
    sender_domain = sender.split('@')[1] if '@' in sender else 'unknown'

    # Track total processed
    emails_processed_total.labels(
        status=status,
        sender_domain=sender_domain,
        action_type=action_type
    ).inc()

    # Track processing time
    processing_time.labels(
        status=status,
        action_type=action_type
    ).observe(duration)

    # Update hourly peaks
    hour = datetime.now().hour
    peak_hours.labels(hour=str(hour)).inc()

    # Update top senders
    top_senders.labels(sender_domain=sender_domain).inc()

    # Track action distribution
    action_distribution.labels(
        action_type=action_type,
        status=status
    ).inc()


def track_retry(action_type: str, error_type: str):
    """Track retry attempts.

    Args:
        action_type: Type of action being retried
        error_type: Type of error that caused retry
    """
    retry_count.labels(
        action_type=action_type,
        error_type=error_type
    ).inc()


def update_success_rate(success_count: int, total_count: int):
    """Update rolling success rate.

    Args:
        success_count: Number of successful operations
        total_count: Total number of operations
    """
    if total_count > 0:
        rate = (success_count / total_count) * 100
        success_rate.set(rate)


def update_queue_depth(depth: int):
    """Update current queue depth.

    Args:
        depth: Current number of items in processing queue
    """
    queue_depth.set(depth)


def update_average_latency(action_type: str, latency_ms: float):
    """Update average processing latency.

    Args:
        action_type: Type of action
        latency_ms: Average latency in milliseconds
    """
    average_latency.labels(action_type=action_type).set(latency_ms)


def track_database_query(query_type: str, duration: float):
    """Track database query performance.

    Args:
        query_type: Type of query (select/insert/update/delete)
        duration: Query duration in seconds
    """
    database_query_duration.labels(query_type=query_type).observe(duration)


def set_active_workers(count: int):
    """Set number of active workers.

    Args:
        count: Number of active processing workers
    """
    active_workers.set(count)


def update_cache_hit_rate(hits: int, total: int):
    """Update cache hit rate.

    Args:
        hits: Number of cache hits
        total: Total cache requests
    """
    if total > 0:
        rate = (hits / total) * 100
        cache_hit_rate.set(rate)


def set_app_info(version: str, environment: str, region: str):
    """Set application information.

    Args:
        version: Application version
        environment: Deployment environment
        region: Deployment region
    """
    app_info.info({
        'version': version,
        'environment': environment,
        'region': region,
        'build_time': datetime.now().isoformat()
    })


# Analytics aggregation functions
class MetricsAggregator:
    """Aggregate metrics for reporting."""

    @staticmethod
    def get_hourly_stats() -> dict:
        """Get hourly processing statistics."""
        # This would query Prometheus for hourly aggregates
        return {
            'current_hour': datetime.now().hour,
            'emails_processed': 0,  # Would come from Prometheus query
            'success_rate': 0.0,
            'average_latency_ms': 0.0
        }

    @staticmethod
    def get_top_senders(limit: int = 10) -> dict:
        """Get top email senders."""
        # This would query Prometheus topk() function
        return {
            'timestamp': datetime.now().isoformat(),
            'top_senders': []  # Would come from Prometheus query
        }

    @staticmethod
    def get_daily_summary() -> dict:
        """Get daily summary statistics."""
        return {
            'date': datetime.now().date().isoformat(),
            'total_processed': 0,
            'success_count': 0,
            'failure_count': 0,
            'success_rate': 0.0,
            'average_latency_ms': 0.0,
            'peak_hour': 0,
            'total_retries': 0
        }
