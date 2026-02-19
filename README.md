# MFTPlus Course Crawler

High-performance async web crawler for aggregating and synchronizing course data from the [MFTPlus](https://mftplus.com) educational platform.

## Overview

This project provides a robust, production-ready solution for:

- **Bulk course data extraction** from MFTPlus API
- **Real-time parameter synchronization** (departments, locations, course categories)
- **Advanced filtering capabilities** with interactive selection
- **Multi-format data export** (CSV, JSON)
- **Change tracking** with temporal auditing and active status management

Built with asynchronous concurrency patterns for optimal performance on large datasets.

## Architecture

### Core Components

| Module | Purpose |
|--------|---------|
| `update_courses.py` | Main async crawler for course data extraction with pagination |
| `update_courses_filter.py` | Interactive filtering with change tracking and data normalization |
| `update_params.py` | API parameter synchronization (departments, locations, categories) |

### Data Flow

```
MFTPlus API
    ↓
[fetch_all_courses] → async pagination with backoff
    ↓
[normalize_course] → data transformation & enrichment
    ↓
[filter_courses] → interactive filtering & change detection
    ↓
CSV + JSON exports + audit logs
```

## Features

### 🚀 Performance

- **Asynchronous I/O** with configurable concurrency limits
- **Intelligent pagination** with automatic termination on empty pages
- **Connection pooling** for optimal resource utilization
- **Batch processing** support for large datasets

### 🔍 Data Quality

- **Automatic deduplication** and conflict resolution
- **Temporal change tracking** with UTC timestamps
- **Active/inactive status management** for course lifecycle
- **MongoDB ObjectId support** for reliable ID handling
- **URL encoding** for special characters in course parameters

### 🎛️ Flexibility

- **Multi-criteria filtering** by department, location, course type, duration
- **Interactive selection interface** with bulk operations
- **Configurable concurrency** and pagination parameters
- **Timezone-aware** operations (Tehran: `Asia/Tehran`)

### 📊 Export Capabilities

- **CSV export** for spreadsheet analysis
- **JSON export** for downstream integrations
- **Structured JSON** with full course metadata
- **Audit logging** to markdown for transparency

## Prerequisites

- **Python** 3.10+
- **pip** or **conda** for package management
- **Internet connection** for MFTPlus API access

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd mftplus_course_crawler
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### Required Packages
- `aiohttp>=3.8.0` – Async HTTP client
- `pandas>=1.3.0` – Data manipulation
- `requests>=2.28.0` – Synchronous HTTP (parameter sync)

## Usage

### Quick Start: Fetch All Courses

```bash
python update_courses.py
```

This will:
1. Fetch all courses from MFTPlus API
2. Export to `mftplus_courses_async.csv`
3. Export to `mftplus_courses_async.json`
4. Log activity to `COURSE_LOG.md`

### Interactive Filtering

```bash
python update_courses_filter.py
```

Follow the interactive prompts to:
1. Select departments
2. Choose locations
3. Filter by course type and duration
4. Review detected changes
5. Confirm updates

### Synchronize Reference Data

```bash
python update_params.py
```

Updates reference data files in `/data/`:
- `departments.json` – Department metadata
- `places.json` – Location/center information
- `groups.json` – Course categories
- `courses.json` – Structured course listings
- `months.json` – Temporal metadata

## Configuration

### API Settings

```python
# update_courses.py
API_URL = "https://mftplus.com/ajax/default/calendar?need=search"
PAGE_SIZE = 9
MAX_CONCURRENCY = 5
MAX_EMPTY_PAGES = 2
```

**Tuning Recommendations:**

| Setting | Default | Range | Notes |
|---------|---------|-------|-------|
| `PAGE_SIZE` | 9 | 1-20 | Results per API request |
| `MAX_CONCURRENCY` | 5 | 1-20 | Simultaneous connections |
| `MAX_EMPTY_PAGES` | 2 | 1-5 | Termination threshold |

### Timezone Configuration

```python
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
```

All timestamps are Tehran-localized for consistency with source data.

## Data Schema

### Export Columns (CSV/JSON)

| Field | Type | Description |
|-------|------|-------------|
| `id` | ObjectId | Unique MFTPlus identifier |
| `title` | string | Course name |
| `department` | string | Department/subject area |
| `center` | string | Training location/organization |
| `teacher` | string | Instructor name |
| `start_date` | date | Course start date |
| `end_date` | date | Course completion date |
| `capacity` | integer | Maximum enrollment |
| `duration_hours` | float | Total instructional hours |
| `days` | string | Class schedule (pipe-delimited) |
| `min_price` | float | Minimum cost (Toman) |
| `max_price` | float | Maximum cost (Toman) |
| `course_url` | url | Direct MFTPlus course link |
| `cover` | string | Course thumbnail URL |
| `is_active` | boolean | Current availability status |
| `changed_at` | timestamp | Last modification time |
| `updated_at` | timestamp | Export timestamp |

### Data Files Structure

```
data/
├── departments.json     # {"id": {...}, "title": "..."}[]
├── places.json          # Location/center metadata
├── groups.json          # Course category classifications
├── courses.json         # Cached course structured data
└── months.json          # Temporal period definitions
```

## API Reference

### Fetch Page

```python
async def fetch_page(session, skip: int) -> List[dict]:
    """
    Fetch paginated course data from MFTPlus API.
    
    Args:
        session: aiohttp.ClientSession
        skip: Pagination offset
        
    Returns:
        List of course records or empty list on failure
    """
```

**Request Payload:**
```json
{
    "term": "",
    "sort": "",
    "skip": 0,
    "pSkip": 0,
    "type": "all"
}
```

### Error Handling

- Network errors are logged with skip offset for debugging
- Empty page detection enables graceful termination
- Concurrent request limits prevent API throttling

## Performance Considerations

### Throughput Optimization

- **Concurrency limit (5)** balances speed vs. API friendliness
- **Typical execution**: 500 courses/minute on standard connection
- **Memory footprint**: ~2GB for 50k+ courses (pandas DataFrame)

### Best Practices

1. **Run during off-peak hours** to minimize API load
2. **Monitor `MAX_CONCURRENCY`** – increase cautiously if throttled
3. **Store exports incrementally** for fault tolerance
4. **Implement rate limiting** if noticed 429 responses

### Scaling Considerations

For 100k+ courses:
- Consider database backend instead of CSV/JSON
- Implement incremental sync (delta updates)
- Add distributed crawling with worker pools

## Output Files

| File | Format | Purpose |
|------|--------|---------|
| `mftplus_courses_async.csv` | CSV | Tabular analysis, Excel import |
| `mftplus_courses_async.json` | JSON | API integration, normalized structure |
| `COURSE_LOG.md` | Markdown | Execution audit trail |

## Maintenance

### Periodic Updates

Schedule `update_params.py` **weekly** to capture:
- New departments/locations
- Category changes
- Temporal boundaries

Schedule `update_courses.py` **daily** or **on-demand** for course catalog refresh.
