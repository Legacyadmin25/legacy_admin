#!/usr/bin/env python3
"""
Load Test Script for Legacy Admin
This script uses Locust to run load tests against the application.

Usage:
    python load_test.py [--headless] [--users=100] [--spawn-rate=10] [--runtime=300]

Requirements:
    pip install locust
"""

import os
import sys
import time
import random
import logging
import json
from datetime import datetime
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging

# Configure logging
setup_logging("INFO", None)
logger = logging.getLogger(__name__)

# Test configuration
DEFAULT_HOST = os.getenv("TARGET_HOST", "https://staging.legacyadmin.example.com")
DEFAULT_USERS = int(os.getenv("USERS", "100"))
DEFAULT_SPAWN_RATE = int(os.getenv("SPAWN_RATE", "10"))
DEFAULT_RUNTIME = int(os.getenv("RUNTIME", "300"))  # 5 minutes
DEFAULT_USER_CREDENTIALS = [
    {"username": "test_user1", "password": "LoadTest123!"},
    {"username": "test_user2", "password": "LoadTest123!"},
    {"username": "test_user3", "password": "LoadTest123!"},
]


class LegacyAdminUser(HttpUser):
    """
    Simulated user for load testing the Legacy Admin application.
    """
    wait_time = between(1, 5)
    credentials = None
    is_authenticated = False
    
    def on_start(self):
        """
        Initialize the user and log in.
        """
        if not self.credentials:
            # Pick random credentials from the pool
            self.credentials = random.choice(DEFAULT_USER_CREDENTIALS)
        
        self.login()
    
    def login(self):
        """
        Perform login to get a session.
        """
        logger.info(f"Logging in as {self.credentials['username']}")
        
        # First get the login page to obtain CSRF token
        response = self.client.get("/accounts/login/")
        
        if response.status_code != 200:
            logger.error(f"Failed to get login page: {response.status_code}")
            return
        
        # Extract CSRF token from the page
        csrf_token = None
        for line in response.text.splitlines():
            if 'csrfmiddlewaretoken' in line:
                import re
                match = re.search(r'value=["\']([^"\']+)["\']', line)
                if match:
                    csrf_token = match.group(1)
                    break
        
        if not csrf_token:
            logger.error("Could not find CSRF token in login page")
            return
        
        # Perform login
        login_data = {
            "username": self.credentials["username"],
            "password": self.credentials["password"],
            "csrfmiddlewaretoken": csrf_token
        }
        
        response = self.client.post(
            "/accounts/login/",
            data=login_data,
            headers={"Referer": f"{self.host}/accounts/login/"}
        )
        
        self.is_authenticated = response.status_code == 200 or response.status_code == 302
        logger.info(f"Login {'successful' if self.is_authenticated else 'failed'}")
    
    @task(10)
    def view_dashboard(self):
        """
        View the main dashboard.
        """
        self.client.get("/")
    
    @task(5)
    def view_underwriters(self):
        """
        View the underwriters list.
        """
        self.client.get("/settings/underwriters/")
    
    @task(3)
    def view_plans(self):
        """
        View the plans list.
        """
        self.client.get("/settings/plans/")
    
    @task(7)
    def search_members(self):
        """
        Search for members.
        """
        search_terms = ["Smith", "Johnson", "Williams", "Jones", "Brown"]
        term = random.choice(search_terms)
        self.client.get(f"/members/search/?q={term}")
    
    @task(2)
    def view_reports(self):
        """
        View reports section.
        """
        self.client.get("/reports/")
    
    @task(1)
    def create_policy(self):
        """
        Simulate creating a new policy.
        This is a complex flow that involves multiple steps.
        """
        if not self.is_authenticated:
            logger.warning("Cannot create policy: Not authenticated")
            return
        
        # Step 1: Visit the new policy page
        response = self.client.get("/policies/new/")
        
        if response.status_code != 200:
            logger.error(f"Failed to get new policy page: {response.status_code}")
            return
        
        # Extract CSRF token
        csrf_token = None
        for line in response.text.splitlines():
            if 'csrfmiddlewaretoken' in line:
                import re
                match = re.search(r'value=["\']([^"\']+)["\']', line)
                if match:
                    csrf_token = match.group(1)
                    break
        
        if not csrf_token:
            logger.error("Could not find CSRF token in new policy page")
            return
        
        # Step 2: Submit basic policy info
        policy_data = {
            "csrfmiddlewaretoken": csrf_token,
            "member_first_name": random.choice(["John", "Jane", "Robert", "Mary", "David"]),
            "member_last_name": random.choice(["Smith", "Johnson", "Williams", "Jones", "Brown"]),
            "member_id_number": f"{random.randint(6000000000000, 9999999999999)}",
            "member_email": f"test{random.randint(1000, 9999)}@example.com",
            "member_phone": f"07{random.randint(10000000, 99999999)}",
            "plan_id": "1",  # Assuming plan ID 1 exists
            "underwriter_id": "1",  # Assuming underwriter ID 1 exists
            "start_date": datetime.now().strftime("%Y-%m-%d"),
        }
        
        response = self.client.post(
            "/policies/new/",
            data=policy_data,
            headers={"Referer": f"{self.host}/policies/new/"}
        )
        
        # Check if we got redirected to the policy details page
        if response.status_code != 302:
            logger.error(f"Failed to create policy: {response.status_code}")
            return
        
        logger.info("Successfully created a new policy")


def run_headless(host, users, spawn_rate, runtime):
    """
    Run the load test in headless mode.
    """
    # Setup environment and runner
    env = Environment(user_classes=[LegacyAdminUser])
    env.create_local_runner()
    
    # Set host
    env.host = host
    
    # Start a greenlet to periodically print stats
    stats_printer_greenlet = env.create_stats_printer(stats_printer)
    stats_printer_greenlet.start()
    
    # Start a greenlet to save history to a file
    stats_history_greenlet = env.create_stats_history_writer(
        f"./load_test_history_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
    )
    stats_history_greenlet.start()
    
    # Start the test
    env.runner.start(users, spawn_rate=spawn_rate)
    
    # Wait for the specified runtime
    logger.info(f"Running load test for {runtime} seconds with {users} users at spawn rate {spawn_rate}")
    time.sleep(runtime)
    
    # Stop the test
    env.runner.quit()
    
    # Stop the stats printer and history writer
    stats_printer_greenlet.kill(block=False)
    stats_history_greenlet.kill(block=False)
    
    # Get the stats
    stats = env.runner.stats
    
    # Print the final stats
    logger.info("Load test completed. Results:")
    logger.info(f"Total Requests: {stats.total.num_requests}")
    logger.info(f"Failed Requests: {stats.total.num_failures}")
    logger.info(f"Median Response Time: {stats.total.median_response_time} ms")
    logger.info(f"95th Percentile: {stats.total.get_response_time_percentile(0.95)} ms")
    logger.info(f"Requests Per Second: {stats.total.current_rps}")
    
    # Write detailed report
    report = {
        "timestamp": datetime.now().isoformat(),
        "duration": runtime,
        "num_users": users,
        "spawn_rate": spawn_rate,
        "host": host,
        "total_requests": stats.total.num_requests,
        "failed_requests": stats.total.num_failures,
        "median_response_time": stats.total.median_response_time,
        "average_response_time": stats.total.avg_response_time,
        "min_response_time": stats.total.min_response_time,
        "max_response_time": stats.total.max_response_time,
        "percentile_95": stats.total.get_response_time_percentile(0.95),
        "percentile_99": stats.total.get_response_time_percentile(0.99),
        "requests_per_second": stats.total.current_rps,
        "endpoints": {},
    }
    
    # Add per-endpoint stats
    for name, stats_entry in stats.entries.items():
        report["endpoints"][name] = {
            "method": name.split()[0] if " " in name else "GET",
            "url": name.split()[1] if " " in name else name,
            "num_requests": stats_entry.num_requests,
            "num_failures": stats_entry.num_failures,
            "median_response_time": stats_entry.median_response_time,
            "average_response_time": stats_entry.avg_response_time,
            "min_response_time": stats_entry.min_response_time,
            "max_response_time": stats_entry.max_response_time,
        }
    
    # Write report to file
    report_file = f"load_test_report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Detailed report written to {report_file}")
    
    # Return non-zero exit code if there were too many failures
    failure_rate = stats.total.fail_ratio
    logger.info(f"Failure rate: {failure_rate:.2%}")
    
    if failure_rate > 0.1:  # More than 10% failures
        logger.error("LOAD TEST FAILED: Too many failures")
        return 1
    
    return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Load test for Legacy Admin")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Target host URL (default: {DEFAULT_HOST})")
    parser.add_argument("--users", type=int, default=DEFAULT_USERS, help=f"Number of users to simulate (default: {DEFAULT_USERS})")
    parser.add_argument("--spawn-rate", type=int, default=DEFAULT_SPAWN_RATE, help=f"Rate of user spawning per second (default: {DEFAULT_SPAWN_RATE})")
    parser.add_argument("--runtime", type=int, default=DEFAULT_RUNTIME, help=f"Test duration in seconds (default: {DEFAULT_RUNTIME})")
    
    args = parser.parse_args()
    
    if args.headless:
        sys.exit(run_headless(args.host, args.users, args.spawn_rate, args.runtime))
    else:
        # For non-headless mode, use Locust's web UI
        os.system(f"locust -f {__file__} --host={args.host}")
