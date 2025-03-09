# Multithreaded Content Scraping for GlovePost

This document outlines the improvements made to enhance the performance and efficiency of the content scraping system in GlovePost through multithreading and parallel processing.

## Overview of Improvements

We've implemented several key improvements to transform the scraping system from a sequential, single-threaded architecture to a highly efficient multithreaded system:

1. **Continuous scraper daemon**: Replaced the scheduled bash script with a daemon process that constantly refreshes content
2. **Multithreaded content sources**: Process multiple content sources (RSS, Twitter, Facebook, Reddit, 4chan) in parallel
3. **Multithreaded post fetching**: Added threading to individual scrapers to fetch post details concurrently
4. **Enhanced error handling**: Implemented robust retry mechanisms with exponential backoff
5. **Systemd service integration**: Created proper system service for automatic startup and monitoring

## Components

The multithreaded scraping system consists of these main components:

1. **`refresh_content.py`**: Main Python script that manages worker threads and coordinates scraping
2. **Enhanced individual scrapers**:
   - `content_aggregator.py`: Now fetches from different sources in parallel
   - `reddit_scraper.py`: Adds parallel subreddit processing and post detail fetching
   - `4chan_scraper.py`: Adds parallel board processing (already had thread detail parallelism)

3. **System integration**:
   - `glovepost-scraper.service`: Systemd service definition
   - `install_scraper_service.sh`: Installation script for the systemd service

4. **Testing**:
   - `test_scraper_performance.py`: Simple benchmarking tool for performance comparison

## Performance Improvements

The multithreaded approach provides significant performance improvements:

- **Reduced overall scraping time**: By running multiple scrapers in parallel, the total execution time is now closer to the time of the slowest scraper, rather than the sum of all scrapers.
- **Better resource utilization**: The system efficiently uses available CPU cores and network bandwidth.
- **Responsiveness to new content**: The continuous daemon mode allows for more frequent content updates without overloading servers.
- **Reliability**: Enhanced error handling with retries ensures content is scraped even when temporary issues occur.

## Implementation Details

### Thread Pool Architecture

Each component in the system uses Python's `ThreadPoolExecutor` to manage worker threads:

1. **Top level** (`refresh_content.py`): Creates a thread pool to run multiple source scrapers concurrently
2. **Source level** (e.g., `reddit_scraper.py`): Uses a thread pool to process multiple subreddits concurrently
3. **Detail level** (within individual scrapers): Uses a thread pool to fetch details for multiple posts/threads concurrently

### Rate Limiting and Throttling

We've implemented careful rate limiting to prevent overwhelming the source websites:

- **Global limits**: The main process limits the total number of worker threads
- **Per-source limits**: Each source has a specific concurrency limit (e.g., 2-3 threads for Reddit)
- **Jitter and backoff**: Random delays and exponential backoff on failures prevent request bursts

### Thread Safety

To ensure thread safety when multiple threads access shared resources:

- **Locks for shared data**: Each shared resource (e.g., content lists) is protected with a threading.Lock
- **Local processing first**: Data is processed locally in each thread before updating shared resources
- **Immutable inputs**: Thread functions receive immutable inputs to avoid race conditions

## Usage Instructions

### Running the Multithreaded Scraper

For a one-time scraper run:

```bash
./refresh_content.py
```

To run the scraper with specific settings:

```bash
./refresh_content.py --scrapers=rss,twitter,reddit --workers=4 --interval=3600
```

For daemon mode (continuous operation):

```bash
./refresh_content.py --daemon --interval=1800  # Run every 30 minutes
```

### Installing as a System Service

To install as a systemd service that starts automatically:

```bash
sudo ./install_scraper_service.sh
```

This will:
1. Install the service to run at system startup
2. Set up proper resource limits and restrictions
3. Configure logging to the system journal

### Managing the Service

```bash
# Check status
sudo systemctl status glovepost-scraper.service

# Start/stop/restart
sudo systemctl start glovepost-scraper.service
sudo systemctl stop glovepost-scraper.service
sudo systemctl restart glovepost-scraper.service

# View logs
sudo journalctl -u glovepost-scraper.service
```

### Performance Testing

To benchmark the performance:

```bash
./test_scraper_performance.py
```

Compare different settings:

```bash
./test_scraper_performance.py --scrapers=reddit,4chan --limit=20
```

## Customization

### Adjusting Thread Counts

Thread counts can be adjusted based on your specific requirements:

1. **Main worker threads**: Adjust the `--workers` parameter in `refresh_content.py` (default: 4)
2. **Content source concurrency**: Modify the `max_workers` value in individual scraper files

### Adding New Content Sources

To add a new content source:
1. Create a new scraper script with threading support (or modify an existing one)
2. Add it to the `SCRAPER_COMMANDS` dictionary in `refresh_content.py`
3. Update the `--scrapers` argument in the service file if needed

## Troubleshooting

- **Rate limiting**: If you encounter rate limiting (HTTP 429 errors), reduce the number of worker threads
- **Memory usage**: If memory usage is high, lower the number of concurrent threads
- **CPU usage**: If CPU usage is excessive, add longer delays between requests

## Technical Notes

- **I/O-bound operations**: The threading approach is chosen because web scraping is primarily I/O-bound
- **GIL limitations**: Python's Global Interpreter Lock (GIL) is not a significant bottleneck for this workload
- **Error isolation**: Errors in one thread don't affect other threads, improving overall reliability

## Future Enhancements

Potential future improvements include:

1. **Async I/O**: Replace threading with async/await for even more efficient I/O handling
2. **Distributed processing**: Distribute scraping across multiple nodes for very large scale
3. **Dynamic rate limiting**: Adjust concurrency based on response times and rate limit headers
4. **Queue-based architecture**: Implement a proper task queue system (e.g., Redis Queue or Celery)