"""
Scrape the Nate's Newsletter Substack index page and return a list of article dicts.
Uses the Firecrawl CLI (already installed and authenticated) via subprocess.
"""

import json
import os
import re
import subprocess
import tempfile
import time
from urllib.parse import urljoin, urlparse

FIRECRAWL_ATTEMPTS = 3
INITIAL_RETRY_DELAY_SECONDS = 1.0
