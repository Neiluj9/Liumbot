"""Time formatting utilities for funding rate countdowns"""

from datetime import datetime
from colorama import Fore


def format_time_until_funding(next_funding_time):
    """Format time until next funding as countdown string

    Args:
        next_funding_time: datetime object or None

    Returns:
        Formatted string like "2h 15m" or "N/A" if None
    """
    if next_funding_time is None:
        return "N/A"

    now = datetime.now(next_funding_time.tzinfo) if next_funding_time.tzinfo else datetime.now()
    time_diff = next_funding_time - now

    if time_diff.total_seconds() < 0:
        return "0s"

    total_seconds = int(time_diff.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m"
    else:
        return f"{seconds}s"


def get_countdown_color(next_funding_time):
    """Get color for countdown based on time remaining

    Args:
        next_funding_time: datetime object or None

    Returns:
        Colorama color constant
    """
    if next_funding_time is None:
        return Fore.WHITE

    now = datetime.now(next_funding_time.tzinfo) if next_funding_time.tzinfo else datetime.now()
    time_diff = next_funding_time - now
    hours_remaining = time_diff.total_seconds() / 3600

    if hours_remaining < 1:
        return Fore.RED
    elif hours_remaining < 4:
        return Fore.YELLOW
    else:
        return Fore.GREEN
