"""Plot spread data from CSV log file

Usage:
    python plot_spread.py spreads_log_BTC_20251006_215224.csv
"""

import sys
import csv
import os
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def plot_spread(csv_filename):
    """Plot spread data from CSV file"""

    timestamps = []
    spreads = []
    spread_pcts = []
    bid_a_values = []
    ask_b_values = []

    # Read CSV (with or without header)
    with open(csv_filename, 'r') as f:
        # Check if first line is a header
        first_line = f.readline().strip()
        f.seek(0)

        if first_line.startswith('timestamp'):
            # Has header
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = datetime.fromisoformat(row['timestamp'])
                timestamps.append(timestamp)
                spreads.append(float(row['spread']))
                spread_pcts.append(float(row['spread_pct']))
                bid_a_values.append(float(row['bid_a']))
                ask_b_values.append(float(row['ask_b']))

            # Get exchange names from first row
            f.seek(0)
            reader = csv.DictReader(f)
            first_row = next(reader)
            exchange_a = first_row['exchange_a'].upper()
            exchange_b = first_row['exchange_b'].upper()
            symbol = first_row['symbol']
        else:
            # No header - read as plain CSV
            reader = csv.reader(f)
            first_row = next(reader)
            exchange_a = first_row[1].upper()
            exchange_b = first_row[2].upper()
            symbol = first_row[3]

            # Process first row
            timestamp = datetime.fromisoformat(first_row[0])
            timestamps.append(timestamp)
            bid_a_values.append(float(first_row[4]))
            ask_b_values.append(float(first_row[5]))
            spreads.append(float(first_row[6]))
            spread_pcts.append(float(first_row[7]))

            # Process remaining rows
            for row in reader:
                timestamp = datetime.fromisoformat(row[0])
                timestamps.append(timestamp)
                bid_a_values.append(float(row[4]))
                ask_b_values.append(float(row[5]))
                spreads.append(float(row[6]))
                spread_pcts.append(float(row[7]))

    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    # Plot 1: Bid A and Ask B
    ax1.plot(timestamps, bid_a_values, label=f'{exchange_a} Best Bid',
             color='green', linewidth=1.5, alpha=0.8)
    ax1.plot(timestamps, ask_b_values, label=f'{exchange_b} Best Ask',
             color='red', linewidth=1.5, alpha=0.8)
    ax1.set_ylabel('Price (USD)', fontsize=12)
    ax1.set_title(f'{symbol} Price Comparison: {exchange_a} vs {exchange_b}',
                  fontsize=14, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    # Plot 2: Spread (in percentage)
    ax2.plot(timestamps, spread_pcts, label='Spread % (Bid A - Ask B)',
             color='blue', linewidth=2)
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax2.fill_between(timestamps, spread_pcts, 0, where=[s >= 0 for s in spread_pcts],
                     color='green', alpha=0.2, label='Positive Spread')
    ax2.fill_between(timestamps, spread_pcts, 0, where=[s < 0 for s in spread_pcts],
                     color='red', alpha=0.2, label='Negative Spread')
    ax2.set_ylabel('Spread (%)', fontsize=12)
    ax2.set_xlabel('Time', fontsize=12)
    ax2.set_title('Price Spread Over Time', fontsize=14, fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    # Format x-axis
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.xticks(rotation=45)

    # Stats text
    avg_spread = sum(spreads) / len(spreads)
    max_spread = max(spreads)
    min_spread = min(spreads)
    avg_spread_pct = sum(spread_pcts) / len(spread_pcts)
    max_spread_pct = max(spread_pcts)
    min_spread_pct = min(spread_pcts)

    # Determine precision for dollar amounts based on magnitude
    max_abs_spread = max(abs(min_spread), abs(max_spread), abs(avg_spread))
    if max_abs_spread < 0.001:
        dollar_precision = 6
    elif max_abs_spread < 0.01:
        dollar_precision = 5
    elif max_abs_spread < 0.1:
        dollar_precision = 4
    elif max_abs_spread < 1:
        dollar_precision = 3
    else:
        dollar_precision = 2

    stats_text = f'Avg: {avg_spread_pct:.4f}% | Max: {max_spread_pct:.4f}% | Min: {min_spread_pct:.4f}%'
    fig.text(0.5, 0.02, stats_text, ha='center', fontsize=11,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.08)

    # Save and show
    png_dir = "exports/spreads/png"
    os.makedirs(png_dir, exist_ok=True)
    # Extract just the filename without path
    base_filename = os.path.basename(csv_filename)
    output_filename = os.path.join(png_dir, base_filename.replace('.csv', '.png'))
    plt.savefig(output_filename, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_filename}")
    print(f"\nSpread Statistics:")
    print(f"  Average: ${avg_spread:.{dollar_precision}f} ({avg_spread_pct:.4f}%)")
    print(f"  Maximum: ${max_spread:.{dollar_precision}f} ({max_spread_pct:.4f}%)")
    print(f"  Minimum: ${min_spread:.{dollar_precision}f} ({min_spread_pct:.4f}%)")
    print(f"  Data points: {len(spread_pcts)}")

    plt.show()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python plot_spread.py <csv_file>")
        print("Example: python plot_spread.py spreads_log_BTC_20251006_215224.csv")
        sys.exit(1)

    csv_file = sys.argv[1]
    plot_spread(csv_file)
