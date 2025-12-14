"""Load testing scenarios for email intelligence platform."""

import random

from locust import HttpUser, between, task


class EmailProcessingUser(HttpUser):
    """Standard email processing load."""

    wait_time = between(1, 5)

    @task(3)
    def process_email(self):
        """Simulate email processing."""
        payload = {
            "email_id": f"test-{random.randint(1, 10000)}",
            "sender": f"user{random.randint(1, 1000)}@example.com",
            "subject": "Test email",
            "body": "This is a test email " * random.randint(1, 10),
        }
        self.client.post("/api/observations/analyze", json=payload)

    @task(1)
    def health_check(self):
        """Periodic health check."""
        self.client.get("/health")

    @task(1)
    def get_metrics(self):
        """Check metrics endpoint."""
        self.client.get("/metrics")


class EmailBurstUser(HttpUser):
    """Burst scenario - high volume."""

    wait_time = between(0.5, 1.5)

    @task
    def burst_emails(self):
        """Burst scenario - multiple emails rapidly."""
        for i in range(10):
            payload = {
                "email_id": f"burst-{random.randint(1, 100000)}",
                "sender": f"burst{i}@example.com",
                "subject": "Burst email",
                "body": "Burst test",
            }
            self.client.post("/api/observations/analyze", json=payload)


class StressTestUser(HttpUser):
    """Heavy load stress test."""

    wait_time = between(0.1, 0.5)

    @task
    def continuous_load(self):
        """Continuous heavy load."""
        payload = {
            "email_id": f"stress-{random.randint(1, 1000000)}",
            "sender": "stress@example.com",
            "subject": "Stress test",
            "body": "X" * random.randint(100, 1000),
        }
        with self.client.post(
            "/api/observations/analyze", json=payload, catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Failed with status {response.status_code}")
            elif response.elapsed.total_seconds() > 2.0:
                response.failure(f"Response too slow: {response.elapsed.total_seconds()}s")
            else:
                response.success()
