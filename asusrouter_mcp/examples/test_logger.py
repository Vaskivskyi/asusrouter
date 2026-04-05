#!/usr/bin/env python3
"""Test logging utility for MCP server tests."""

from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any


class TestLogger:
    """Logger for storing test outputs with timestamps."""

    def __init__(self, test_name: str = "mcp_test"):
        self.test_name = test_name
        self.start_time = datetime.now()
        self.logs: list[dict[str, Any]] = []

        # Create logs directory
        self.logs_dir = Path("test_logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Create timestamped log file
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.log_file = self.logs_dir / f"{test_name}_{timestamp}.json"

        self.log("info", f"Test session started: {test_name}")
        self.log("info", f"Log file: {self.log_file}")

    def log(self, level: str, message: str, data: Any = None):
        """Log a message with optional data."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "data": data
        }

        self.logs.append(entry)

        # Print to console
        timestamp_str = datetime.now().strftime("%H:%M:%S")
        level_str = f"[{level.upper()}]"
        print(f"{timestamp_str} {level_str} {message}")

        if data and level in ["error", "debug"]:
            print(f"  Data: {data}")

    def log_test_result(self, test_name: str, success: bool, output: str = "", error: str = ""):
        """Log a test result."""
        self.log(
            "info" if success else "error",
            f"Test {test_name}: {'PASS' if success else 'FAIL'}",
            {
                "test_name": test_name,
                "success": success,
                "output": output,
                "error": error
            }
        )

    def log_tool_call(self, tool_name: str, arguments: dict[str, Any], result: str, success: bool):
        """Log an MCP tool call."""
        self.log(
            "info" if success else "error",
            f"Tool call: {tool_name}",
            {
                "tool_name": tool_name,
                "arguments": arguments,
                "result": result,
                "success": success
            }
        )

    def save(self):
        """Save logs to file."""
        log_data = {
            "test_session": self.test_name,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "logs": self.logs
        }

        with open(self.log_file, 'w') as f:
            json.dump(log_data, f, indent=2)

        self.log("info", f"Test logs saved to {self.log_file}")
        return self.log_file

    def get_summary(self) -> dict[str, Any]:
        """Get test session summary."""
        # Only count actual test results (messages with ": PASS" or ": FAIL")
        test_result_logs = [log for log in self.logs if ": PASS" in log["message"] or ": FAIL" in log["message"]]
        total_tests = len(test_result_logs)
        passed_tests = len([log for log in test_result_logs if ": PASS" in log["message"]])
        failed_tests = len([log for log in test_result_logs if ": FAIL" in log["message"]])

        errors = [log for log in self.logs if log["level"] == "error"]

        return {
            "test_name": self.test_name,
            "duration": (datetime.now() - self.start_time).total_seconds(),
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "errors": len(errors),
            "log_file": str(self.log_file)
        }


def get_latest_log_file(test_name: str = None) -> Path:
    """Get the most recent log file."""
    logs_dir = Path("test_logs")
    if not logs_dir.exists():
        raise FileNotFoundError("No test logs directory found")

    pattern = f"{test_name}_*.json" if test_name else "*.json"
    log_files = list(logs_dir.glob(pattern))

    if not log_files:
        raise FileNotFoundError(f"No log files found matching {pattern}")

    return max(log_files, key=lambda f: f.stat().st_mtime)


def view_log(log_file: Path = None):
    """View a log file in a readable format."""
    if log_file is None:
        log_file = get_latest_log_file()

    with open(log_file) as f:
        data = json.load(f)

    print(f"\n=== Test Log: {data['test_session']} ===")
    print(f"Start: {data['start_time']}")
    print(f"End: {data['end_time']}")
    print(f"Duration: {data['duration_seconds']:.2f} seconds")
    print(f"Total Logs: {len(data['logs'])}")

    print("\n=== Log Entries ===")
    for log in data["logs"]:
        timestamp = datetime.fromisoformat(log["timestamp"]).strftime("%H:%M:%S")
        level = log["level"].upper()
        message = log["message"]
        print(f"{timestamp} [{level}] {message}")

        if log.get("data") and level in ["ERROR", "DEBUG"]:
            print(f"  Data: {json.dumps(log['data'], indent=4)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "view":
        # View latest log file
        try:
            view_log()
        except FileNotFoundError as e:
            print(f"Error: {e}")
    else:
        # Test the logger
        logger = TestLogger("logger_test")
        logger.log("info", "Testing logger functionality")
        logger.log("debug", "Debug message with data", {"key": "value"})
        logger.log_test_result("sample_test", True, "All good!")
        logger.log_tool_call("connect_router", {"host": "192.168.1.1"}, "Success", True)

        summary = logger.get_summary()
        print(f"\nTest Summary: {json.dumps(summary, indent=2)}")

        logger.save()
        print("\nTo view logs later, run: python test_logger.py view")
