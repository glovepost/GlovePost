# GlovePost Multithreaded Content Scraper

This document explains the new multithreaded content scraper implementation for GlovePost.

## Overview

The multithreaded scraper replaces the previous sequential bash script (`refresh_content.sh`) with a more efficient Python-based system that:

1. Runs multiple scrapers concurrently using a thread pool
2. Provides robust error handling with retries and exponential backoff
3. Can run continuously as a daemon process
4. Offers proper logging and process management

## Components

- `refresh_content.py`: Main Python script that manages the thread pool and runs scrapers
- `glovepost-scraper.service`: Systemd service file for running the scraper as a system service
- `install_scraper_service.sh`: Helper script for installing the systemd service

## Usage

### Basic Usage

Run the scraper once and exit:

```bash
./refresh_content.py
```

### Custom Run Options

Specify which scrapers to run:

```bash
./refresh_content.py --scrapers=rss,twitter,reddit
```

Adjust the number of worker threads:

```bash
./refresh_content.py --workers=2
```

### Daemon Mode

Run continuously with a specific interval (in seconds):

```bash
./refresh_content.py --daemon --interval=3600  # Run every hour
```

### Installing as a System Service

To install as a systemd service (runs automatically even after system restart):

```bash
sudo ./install_scraper_service.sh
```

This will:
1. Install the service to start at boot
2. Configure it to run as your user
3. Set it to run every hour by default

### Managing the Service

Once installed as a service, you can control it using standard systemd commands:

```bash
# Check status
sudo systemctl status glovepost-scraper.service

# Start/stop/restart
sudo systemctl start glovepost-scraper.service
sudo systemctl stop glovepost-scraper.service
sudo systemctl restart glovepost-scraper.service

# View logs
sudo journalctl -u glovepost-scraper.service
sudo journalctl -u glovepost-scraper.service -f  # Follow logs in real-time
```

## Configuration

### Scraper Commands

The available scrapers and their commands are configured in the `SCRAPER_COMMANDS` dictionary in `refresh_content.py`:

```python
SCRAPER_COMMANDS = {
    "rss": ["content_aggregator.py", "--sources", "rss"],
    "twitter": ["twitter_scraper.py", "--accounts", "BBCWorld CNN ...", "--limit", "5"],
    "facebook": ["facebook_scraper.py", "--pages", "BBCNews CNN ...", "--limit", "5"],
    "reddit": ["content_aggregator.py", "--sources", "reddit", "--limit", "30"],
    "4chan": ["content_aggregator.py", "--sources", "4chan", "--limit", "20"]
}
```

To add a new scraper or modify existing ones, update this dictionary.

### Service Configuration

If installed as a service, you can modify the service configuration:

```bash
sudo systemctl edit glovepost-scraper.service
```

For example, to change the scraping interval to 30 minutes (1800 seconds):

```
[Service]
ExecStart=
ExecStart=/usr/bin/python3 /path/to/refresh_content.py --daemon --workers=4 --interval=1800
```

## Architecture

### Threading Model

The scraper uses Python's `ThreadPoolExecutor` to manage a pool of worker threads. Each worker processes tasks from a shared queue.

This approach is ideal for web scraping which is I/O-bound (waiting for network responses) rather than CPU-bound.

### Error Handling

- **Retries**: Failed scraper tasks are retried with exponential backoff (increasing wait times between attempts)
- **Jitter**: Random time added to retry waits to prevent thundering herd problems
- **Isolation**: Each scraper runs in isolation, so one failure doesn't affect others
- **Graceful Shutdown**: Handles SIGINT/SIGTERM signals to finish current tasks before exiting

### Logging

Comprehensive logging includes:
- Scraper execution times
- Success/failure status
- Detailed error information
- Timing information for performance analysis

Logs are written to `logs/refresh_content.log` and also output to the console.

## Performance Considerations

- **Thread Count**: The default is 4 worker threads, which is sufficient for most setups. Too many threads can trigger rate limiting or IP blocks.
- **Interval**: The default interval in daemon mode is 15 minutes (900 seconds). Adjust based on how frequently you need fresh content.
- **Resource Usage**: The multithreaded scraper uses more memory than the sequential script but completes much faster.

## Troubleshooting

- **Service fails to start**: Check logs with `journalctl -u glovepost-scraper.service`
- **Scrapers timing out**: May indicate network issues or changes in site structure. Check individual scraper logs.
- **High resource usage**: Reduce the number of worker threads.
- **Scripts not found**: Ensure paths in the service file point to the correct locations.