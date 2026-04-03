#!/usr/bin/env python3
"""
Smoke Test Script for Legacy Admin
This script performs basic functionality tests on a deployed application.
It should be run after deployment to verify core functionality works.

Usage:
    python smoke_test.py [--host=https://app.example.com] [--credentials=file.json]
"""

import os
import sys
import json
import time
import logging
import argparse
import requests
from datetime import datetime
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"smoke_test_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("smoke_test")

# Default values
DEFAULT_HOST = os.getenv("SMOKE_TEST_HOST", "https://app.example.com")
DEFAULT_CREDENTIALS_FILE = os.getenv("SMOKE_TEST_CREDENTIALS", "credentials.json")
DEFAULT_CREDENTIALS = {
    "username": "smoke_test_user",
    "password": "SmokeTest123!"
}
DEFAULT_TIMEOUT = 10  # seconds

# Test categories
CRITICAL = "CRITICAL"    # Application is unusable if these fail
IMPORTANT = "IMPORTANT"  # Major functionality is impaired
NORMAL = "NORMAL"        # Some functionality is affected
MINOR = "MINOR"          # Non-essential functionality


class SmokeTest:
    """Main smoke test class for Legacy Admin"""
    
    def __init__(self, host, credentials=None, timeout=DEFAULT_TIMEOUT):
        """
        Initialize the smoke test.
        
        Args:
            host: The base URL of the application
            credentials: Dict with username and password for login
            timeout: Request timeout in seconds
        """
        self.host = host.rstrip('/')
        self.credentials = credentials or DEFAULT_CREDENTIALS
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Legacy-Admin-Smoke-Test/1.0',
        })
        self.csrf_token = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "host": host,
            "tests": {
                CRITICAL: {"passed": 0, "failed": 0, "results": []},
                IMPORTANT: {"passed": 0, "failed": 0, "results": []},
                NORMAL: {"passed": 0, "failed": 0, "results": []},
                MINOR: {"passed": 0, "failed": 0, "results": []},
            },
            "total": {"passed": 0, "failed": 0},
            "duration": 0
        }
    
    def run_all_tests(self):
        """Run all smoke tests and return results"""
        start_time = time.time()
        
        try:
            # Core accessibility tests
            self.test_homepage_accessibility(CRITICAL)
            self.test_health_endpoint(CRITICAL)
            self.test_static_files(IMPORTANT)
            
            # Authentication tests
            self.test_login_page_accessibility(CRITICAL)
            success = self.test_login(CRITICAL)
            
            # Only run authenticated tests if login was successful
            if success:
                self.test_dashboard_after_login(CRITICAL)
                self.test_underwriter_list(IMPORTANT)
                self.test_plan_list(IMPORTANT)
                self.test_member_search(IMPORTANT)
                self.test_policy_creation_form(IMPORTANT)
                self.test_report_generation(NORMAL)
                self.test_admin_access(NORMAL)
                self.test_user_profile(MINOR)
                self.test_logout(NORMAL)
        
        except Exception as e:
            logger.error(f"Unexpected error during tests: {str(e)}")
            self.record_result(CRITICAL, "test_suite_execution", False, f"Test suite failed to complete: {str(e)}")
        
        # Calculate total duration
        self.results["duration"] = round(time.time() - start_time, 2)
        
        # Calculate total results
        self.results["total"]["passed"] = sum(c["passed"] for c in self.results["tests"].values())
        self.results["total"]["failed"] = sum(c["failed"] for c in self.results["tests"].values())
        
        return self.results
    
    def record_result(self, category, test_name, passed, message="", response=None):
        """
        Record the result of a test.
        
        Args:
            category: Test category (CRITICAL, IMPORTANT, NORMAL, MINOR)
            test_name: Name of the test
            passed: Whether the test passed (True/False)
            message: Additional message about the test result
            response: The HTTP response object (optional)
        """
        result = {
            "test": test_name,
            "passed": passed,
            "message": message,
        }
        
        # Add response details if provided
        if response:
            result["status_code"] = response.status_code
            result["response_time"] = round(response.elapsed.total_seconds() * 1000, 2)  # in ms
        
        # Record the result
        self.results["tests"][category]["results"].append(result)
        
        # Update counters
        if passed:
            self.results["tests"][category]["passed"] += 1
            logger.info(f"✅ {test_name}: {message}")
        else:
            self.results["tests"][category]["failed"] += 1
            logger.error(f"❌ {test_name}: {message}")
        
        return passed
    
    def get_url(self, path):
        """Get the full URL for a path"""
        return urljoin(self.host, path)
    
    def get_csrf_token(self, response):
        """Extract CSRF token from response"""
        for line in response.text.splitlines():
            if 'csrfmiddlewaretoken' in line:
                import re
                match = re.search(r'value=["\']([^"\']+)["\']', line)
                if match:
                    return match.group(1)
        return None
    
    # Test implementations
    
    def test_homepage_accessibility(self, category):
        """Test if the homepage is accessible"""
        try:
            response = self.session.get(
                self.get_url("/"),
                timeout=self.timeout,
                allow_redirects=True
            )
            
            passed = 200 <= response.status_code < 300 or response.status_code == 302
            message = f"Homepage {'accessible' if passed else 'not accessible'} (Status: {response.status_code})"
            
            return self.record_result(category, "homepage_accessibility", passed, message, response)
        except requests.RequestException as e:
            return self.record_result(category, "homepage_accessibility", False, f"Error accessing homepage: {str(e)}")
    
    def test_health_endpoint(self, category):
        """Test if the health endpoint is reporting healthy"""
        try:
            response = self.session.get(
                self.get_url("/health/"),
                timeout=self.timeout
            )
            
            passed = response.status_code == 200
            
            if passed:
                try:
                    data = response.json()
                    passed = data.get("status") == "healthy"
                    message = f"Health endpoint reports: {data.get('status', 'unknown')}"
                except ValueError:
                    passed = False
                    message = "Health endpoint did not return valid JSON"
            else:
                message = f"Health endpoint not accessible (Status: {response.status_code})"
            
            return self.record_result(category, "health_endpoint", passed, message, response)
        except requests.RequestException as e:
            return self.record_result(category, "health_endpoint", False, f"Error accessing health endpoint: {str(e)}")
    
    def test_static_files(self, category):
        """Test if static files are being served correctly"""
        try:
            response = self.session.get(
                self.get_url("/static/css/main.css"),
                timeout=self.timeout
            )
            
            passed = response.status_code == 200 and 'text/css' in response.headers.get('Content-Type', '')
            message = f"Static files {'accessible' if passed else 'not accessible'} (Status: {response.status_code})"
            
            return self.record_result(category, "static_files", passed, message, response)
        except requests.RequestException as e:
            return self.record_result(category, "static_files", False, f"Error accessing static files: {str(e)}")
    
    def test_login_page_accessibility(self, category):
        """Test if the login page is accessible"""
        try:
            response = self.session.get(
                self.get_url("/accounts/login/"),
                timeout=self.timeout
            )
            
            passed = response.status_code == 200
            message = f"Login page {'accessible' if passed else 'not accessible'} (Status: {response.status_code})"
            
            # Store CSRF token for later use
            if passed:
                self.csrf_token = self.get_csrf_token(response)
                if not self.csrf_token:
                    passed = False
                    message += ". Could not find CSRF token."
            
            return self.record_result(category, "login_page_accessibility", passed, message, response)
        except requests.RequestException as e:
            return self.record_result(category, "login_page_accessibility", False, f"Error accessing login page: {str(e)}")
    
    def test_login(self, category):
        """Test login functionality"""
        if not self.csrf_token:
            return self.record_result(category, "login", False, "Cannot test login: No CSRF token available")
        
        try:
            login_data = {
                "username": self.credentials["username"],
                "password": self.credentials["password"],
                "csrfmiddlewaretoken": self.csrf_token
            }
            
            response = self.session.post(
                self.get_url("/accounts/login/"),
                data=login_data,
                headers={"Referer": self.get_url("/accounts/login/")},
                timeout=self.timeout,
                allow_redirects=True
            )
            
            # Check if login was successful (redirect to dashboard or home)
            passed = response.status_code == 200 and "logout" in response.text.lower()
            message = f"Login {'successful' if passed else 'failed'} (Status: {response.status_code})"
            
            return self.record_result(category, "login", passed, message, response)
        except requests.RequestException as e:
            return self.record_result(category, "login", False, f"Error during login: {str(e)}")
    
    def test_dashboard_after_login(self, category):
        """Test if dashboard is accessible after login"""
        try:
            response = self.session.get(
                self.get_url("/dashboard/"),
                timeout=self.timeout
            )
            
            passed = response.status_code == 200
            message = f"Dashboard {'accessible' if passed else 'not accessible'} after login (Status: {response.status_code})"
            
            return self.record_result(category, "dashboard_after_login", passed, message, response)
        except requests.RequestException as e:
            return self.record_result(category, "dashboard_after_login", False, f"Error accessing dashboard: {str(e)}")
    
    def test_underwriter_list(self, category):
        """Test if underwriter list is accessible"""
        try:
            response = self.session.get(
                self.get_url("/settings/underwriters/"),
                timeout=self.timeout
            )
            
            passed = response.status_code == 200
            message = f"Underwriter list {'accessible' if passed else 'not accessible'} (Status: {response.status_code})"
            
            return self.record_result(category, "underwriter_list", passed, message, response)
        except requests.RequestException as e:
            return self.record_result(category, "underwriter_list", False, f"Error accessing underwriter list: {str(e)}")
    
    def test_plan_list(self, category):
        """Test if plan list is accessible"""
        try:
            response = self.session.get(
                self.get_url("/settings/plans/"),
                timeout=self.timeout
            )
            
            passed = response.status_code == 200
            message = f"Plan list {'accessible' if passed else 'not accessible'} (Status: {response.status_code})"
            
            return self.record_result(category, "plan_list", passed, message, response)
        except requests.RequestException as e:
            return self.record_result(category, "plan_list", False, f"Error accessing plan list: {str(e)}")
    
    def test_member_search(self, category):
        """Test member search functionality"""
        try:
            response = self.session.get(
                self.get_url("/members/search/?q=test"),
                timeout=self.timeout
            )
            
            passed = response.status_code == 200
            message = f"Member search {'working' if passed else 'not working'} (Status: {response.status_code})"
            
            return self.record_result(category, "member_search", passed, message, response)
        except requests.RequestException as e:
            return self.record_result(category, "member_search", False, f"Error during member search: {str(e)}")
    
    def test_policy_creation_form(self, category):
        """Test if policy creation form is accessible"""
        try:
            response = self.session.get(
                self.get_url("/policies/new/"),
                timeout=self.timeout
            )
            
            passed = response.status_code == 200
            message = f"Policy creation form {'accessible' if passed else 'not accessible'} (Status: {response.status_code})"
            
            return self.record_result(category, "policy_creation_form", passed, message, response)
        except requests.RequestException as e:
            return self.record_result(category, "policy_creation_form", False, f"Error accessing policy creation form: {str(e)}")
    
    def test_report_generation(self, category):
        """Test if report generation is working"""
        try:
            response = self.session.get(
                self.get_url("/reports/"),
                timeout=self.timeout
            )
            
            passed = response.status_code == 200
            message = f"Reports section {'accessible' if passed else 'not accessible'} (Status: {response.status_code})"
            
            return self.record_result(category, "report_generation", passed, message, response)
        except requests.RequestException as e:
            return self.record_result(category, "report_generation", False, f"Error accessing reports: {str(e)}")
    
    def test_admin_access(self, category):
        """Test if admin interface is accessible (should be restricted)"""
        try:
            response = self.session.get(
                self.get_url("/admin/"),
                timeout=self.timeout,
                allow_redirects=False  # Don't follow redirects
            )
            
            # For admin, either we can access it (200) or we get redirected to login (302)
            # Both are valid responses depending on user permissions
            passed = response.status_code in (200, 302)
            message = f"Admin interface returns appropriate response (Status: {response.status_code})"
            
            return self.record_result(category, "admin_access", passed, message, response)
        except requests.RequestException as e:
            return self.record_result(category, "admin_access", False, f"Error accessing admin: {str(e)}")
    
    def test_user_profile(self, category):
        """Test if user profile is accessible"""
        try:
            response = self.session.get(
                self.get_url("/accounts/profile/"),
                timeout=self.timeout
            )
            
            passed = response.status_code == 200
            message = f"User profile {'accessible' if passed else 'not accessible'} (Status: {response.status_code})"
            
            return self.record_result(category, "user_profile", passed, message, response)
        except requests.RequestException as e:
            return self.record_result(category, "user_profile", False, f"Error accessing user profile: {str(e)}")
    
    def test_logout(self, category):
        """Test logout functionality"""
        try:
            # Get CSRF token first (might be different from login page)
            response = self.session.get(
                self.get_url("/accounts/logout/"),
                timeout=self.timeout
            )
            
            csrf_token = self.get_csrf_token(response)
            if not csrf_token:
                return self.record_result(category, "logout", False, "Could not find CSRF token for logout")
            
            # Perform logout
            logout_data = {
                "csrfmiddlewaretoken": csrf_token
            }
            
            response = self.session.post(
                self.get_url("/accounts/logout/"),
                data=logout_data,
                headers={"Referer": self.get_url("/")},
                timeout=self.timeout,
                allow_redirects=True
            )
            
            # After logout, we should be redirected to login page or home
            passed = response.status_code == 200 and "login" in response.text.lower()
            message = f"Logout {'successful' if passed else 'failed'} (Status: {response.status_code})"
            
            return self.record_result(category, "logout", passed, message, response)
        except requests.RequestException as e:
            return self.record_result(category, "logout", False, f"Error during logout: {str(e)}")


def load_credentials(filename):
    """Load credentials from a JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Credentials file {filename} not found. Using default credentials.")
        return DEFAULT_CREDENTIALS
    except json.JSONDecodeError:
        logger.warning(f"Credentials file {filename} is not valid JSON. Using default credentials.")
        return DEFAULT_CREDENTIALS


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description="Smoke tests for Legacy Admin")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host URL to test")
    parser.add_argument("--credentials", default=DEFAULT_CREDENTIALS_FILE, help="JSON file with credentials")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout in seconds")
    parser.add_argument("--report", default=None, help="File to write JSON report to")
    parser.add_argument("--slack", action="store_true", help="Send results to Slack")
    parser.add_argument("--slack-webhook", help="Slack webhook URL")
    
    args = parser.parse_args()
    
    # Load credentials
    credentials = load_credentials(args.credentials)
    
    # Run the tests
    logger.info(f"Starting smoke tests against {args.host}")
    smoke_test = SmokeTest(args.host, credentials, args.timeout)
    results = smoke_test.run_all_tests()
    
    # Write report to file if requested
    if args.report:
        with open(args.report, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Report written to {args.report}")
    
    # Send results to Slack if requested
    if args.slack and args.slack_webhook:
        try:
            import requests
            
            # Create a simple message
            total_passed = results["total"]["passed"]
            total_failed = results["total"]["failed"]
            total_tests = total_passed + total_failed
            
            status = "✅ PASSED" if total_failed == 0 else "❌ FAILED"
            color = "good" if total_failed == 0 else "danger"
            
            # Check for critical failures
            critical_failures = results["tests"][CRITICAL]["failed"]
            if critical_failures > 0:
                status = "🚨 CRITICAL FAILURES"
            
            message = {
                "attachments": [
                    {
                        "fallback": f"Smoke test results: {status}",
                        "color": color,
                        "title": f"Smoke Test Results for {args.host}",
                        "text": f"Status: {status}\nPassed: {total_passed}/{total_tests}\nFailed: {total_failed}/{total_tests}\nDuration: {results['duration']}s",
                        "fields": []
                    }
                ]
            }
            
            # Add details for each category
            for category in [CRITICAL, IMPORTANT, NORMAL, MINOR]:
                cat_results = results["tests"][category]
                if cat_results["passed"] + cat_results["failed"] > 0:
                    message["attachments"][0]["fields"].append({
                        "title": f"{category} Tests",
                        "value": f"Passed: {cat_results['passed']}, Failed: {cat_results['failed']}",
                        "short": True
                    })
            
            # Add details of failed tests
            failed_tests = []
            for category in [CRITICAL, IMPORTANT, NORMAL, MINOR]:
                for test in results["tests"][category]["results"]:
                    if not test["passed"]:
                        failed_tests.append(f"• {test['test']}: {test['message']}")
            
            if failed_tests:
                message["attachments"][0]["fields"].append({
                    "title": "Failed Tests",
                    "value": "\n".join(failed_tests),
                    "short": False
                })
            
            # Send to Slack
            response = requests.post(
                args.slack_webhook,
                json=message,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info("Results sent to Slack successfully")
            else:
                logger.error(f"Error sending results to Slack: {response.status_code} {response.text}")
        
        except Exception as e:
            logger.error(f"Error sending results to Slack: {str(e)}")
    
    # Exit with appropriate code
    if results["total"]["failed"] > 0:
        logger.error(f"Smoke tests FAILED: {results['total']['failed']} of {results['total']['passed'] + results['total']['failed']} tests failed")
        return 1
    else:
        logger.info(f"Smoke tests PASSED: All {results['total']['passed']} tests passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
