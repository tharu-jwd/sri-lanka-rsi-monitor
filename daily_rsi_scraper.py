import time
import json
import os
from datetime import datetime, timezone, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor, as_completed

class MultiTimeframeRSIScraper:
    def __init__(self, base_url, symbols):
        self.base_url = base_url
        self.symbols = symbols
        self.results = {}
        self.timeframes = ['1h', '1D', '1W', '1M']
    
    def create_driver(self):
        """Create a Chrome driver for scraping"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.implicitly_wait(5)
            return driver
        except Exception as e:
            print(f"Error creating Chrome driver: {e}")
            return None
    
    def build_url(self, symbol):
        """Build complete URL for a given symbol"""
        return self.base_url.replace("{SYMBOL}", symbol)
    
    def fetch_rsi_for_timeframe(self, driver, timeframe):
        """Fetch RSI for a specific timeframe"""
        try:
            # Click on the timeframe button
            timeframe_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, timeframe))
            )
            timeframe_button.click()
            
            # Wait for data to update
            time.sleep(2)
            
            # Wait for RSI row to be present
            rsi_row = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//tr[contains(., 'Relative Strength Index')]"))
            )
            
            # Get the value cell
            value_cell = driver.find_element(By.XPATH, "//tr[contains(., 'Relative Strength Index')]//td[2]")
            rsi_text = value_cell.text.strip()
            
            # Wait for data to load if showing placeholder
            retry_count = 0
            while rsi_text in ["—", "", "N/A", "Loading...", "--"] and retry_count < 5:
                time.sleep(1)
                value_cell = driver.find_element(By.XPATH, "//tr[contains(., 'Relative Strength Index')]//td[2]")
                rsi_text = value_cell.text.strip()
                retry_count += 1
            
            if rsi_text in ["—", "", "N/A", "Loading...", "--"]:
                return None
            
            return float(rsi_text.replace(',', ''))
            
        except Exception as e:
            print(f"    Error fetching {timeframe}: {e}")
            return None
    
    def fetch_single_stock_all_timeframes(self, symbol):
        """Fetch RSI for all timeframes for a single stock"""
        driver = None
        try:
            driver = self.create_driver()
            if not driver:
                return symbol, None, "Could not create Chrome driver"
            
            url = self.build_url(symbol)
            driver.get(url)
            time.sleep(3)
            
            # Wait for page to load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//tr[contains(., 'Relative Strength Index')]"))
            )
            
            rsi_data = {}
            for timeframe in self.timeframes:
                rsi_value = self.fetch_rsi_for_timeframe(driver, timeframe)
                rsi_data[timeframe] = rsi_value
                
            return symbol, rsi_data, None
            
        except Exception as e:
            return symbol, None, f"Error: {e}"
        finally:
            if driver:
                driver.quit()
    
    def fetch_all_rsi(self):
        """Fetch RSI for all symbols and timeframes using parallel processing"""
        print(f"🚀 Multi-Timeframe RSI Fetch - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Processing {len(self.symbols)} symbols with {len(self.timeframes)} timeframes each...")
        print("=" * 70)
        
        results = {}
        failed_count = 0
        
        # Use parallel processing with 2 workers to avoid overwhelming the server
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit all tasks
            future_to_symbol = {
                executor.submit(self.fetch_single_stock_all_timeframes, symbol): symbol 
                for symbol in self.symbols
            }
            
            # Collect results as they complete
            for i, future in enumerate(as_completed(future_to_symbol), 1):
                symbol = future_to_symbol[future]
                clean_symbol = symbol.replace("CSELK-", "")
                
                print(f"[{i:2d}/{len(self.symbols)}] {clean_symbol:<12}", end=" ")
                
                try:
                    symbol_result, rsi_data, error = future.result()
                    
                    if rsi_data is not None:
                        # Check how many timeframes were successful
                        successful_timeframes = sum(1 for v in rsi_data.values() if v is not None)
                        
                        if successful_timeframes > 0:
                            results[symbol] = {
                                'rsi_data': rsi_data,
                                'status': 'success',
                                'successful_timeframes': successful_timeframes,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            # Show summary
                            timeframe_summary = []
                            for tf in self.timeframes:
                                value = rsi_data.get(tf)
                                if value is not None:
                                    timeframe_summary.append(f"{tf}:{value:.1f}")
                                else:
                                    timeframe_summary.append(f"{tf}:--")
                            
                            print(f"✅ {' '.join(timeframe_summary)}")
                        else:
                            results[symbol] = {
                                'rsi_data': rsi_data,
                                'status': 'failed',
                                'error': 'No timeframes successful',
                                'timestamp': datetime.now().isoformat()
                            }
                            failed_count += 1
                            print(f"❌ No data for any timeframe")
                    else:
                        results[symbol] = {
                            'rsi_data': None,
                            'status': 'failed',
                            'error': error,
                            'timestamp': datetime.now().isoformat()
                        }
                        failed_count += 1
                        print(f"❌ {error}")
                        
                except Exception as e:
                    results[symbol] = {
                        'rsi_data': None,
                        'status': 'failed',
                        'error': f"Processing error: {e}",
                        'timestamp': datetime.now().isoformat()
                    }
                    failed_count += 1
                    print(f"❌ Processing error")
        
        print("=" * 70)
        print(f"✅ Success: {len(results) - failed_count}/{len(self.symbols)}")
        print(f"❌ Failed: {failed_count}/{len(self.symbols)}")
        
        self.results = results
        return results
    
    def save_daily_data(self):
        """Save daily RSI data to JSON file"""
        timestamp = datetime.now()
        
        daily_data = {
            'date': timestamp.strftime('%Y-%m-%d'),
            'timestamp': timestamp.isoformat(),
            'timeframes': self.timeframes,
            'total_symbols': len(self.symbols),
            'successful_fetches': len([r for r in self.results.values() if r['status'] == 'success']),
            'failed_fetches': len([r for r in self.results.values() if r['status'] == 'failed']),
            'data': self.results
        }
        
        # Create directory if it doesn't exist
        os.makedirs('dailydata', exist_ok=True)
        
        # Save to daily file
        filename = f"dailydata/rsi_data_{timestamp.strftime('%Y_%m_%d')}.json"
        with open(filename, 'w') as f:
            json.dump(daily_data, f, indent=2)
        
        # Also save to latest.json for the webpage
        with open('latest_rsi.json', 'w') as f:
            json.dump(daily_data, f, indent=2)
        
        print(f"💾 Data saved to {filename} and latest_rsi.json")
        return filename
    
    def generate_html_page(self):
        """Generate HTML page with multi-timeframe support"""
        # Convert to Sri Lanka time (UTC+5:30)
        utc_now = datetime.utcnow()
        sl_timezone = timezone(timedelta(hours=5, minutes=30))
        sl_time = utc_now.replace(tzinfo=timezone.utc).astimezone(sl_timezone)
        
        # Get successful results for display
        successful_results = {k: v for k, v in self.results.items() if v['status'] == 'success'}
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Timeframe RSI Monitor - Sri Lanka Stocks</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .timeframe-selector {{
            padding: 20px 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #eee;
        }}
        .selector-label {{
            font-weight: 600;
            color: #555;
            margin-bottom: 10px;
            display: block;
        }}
        .timeframe-dropdown {{
            padding: 10px 15px;
            border: 2px solid #ddd;
            border-radius: 6px;
            background: white;
            font-size: 16px;
            color: #333;
            cursor: pointer;
            min-width: 200px;
        }}
        .timeframe-dropdown:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            cursor: pointer;
            transition: all 0.3s ease;
            border: 2px solid transparent;
        }}
        .stat-card:hover {{
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            transform: translateY(-2px);
        }}
        .stat-card.active {{
            border-color: #667eea;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }}
        .filter-info {{
            background: #e3f2fd;
            border: 1px solid #2196f3;
            border-radius: 6px;
            padding: 15px;
            margin: 20px 30px 0 30px;
            text-align: center;
            color: #1976d2;
            font-weight: 500;
        }}
        .filter-info .clear-filter {{
            color: #d32f2f;
            cursor: pointer;
            text-decoration: underline;
            margin-left: 10px;
        }}
        .filter-info .clear-filter:hover {{
            color: #b71c1c;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .oversold {{ color: #27ae5f; }}
        .overbought {{ color: #e74c3c; }}
        .neutral {{ color: #f39c12; }}
        .table-container {{
            padding: 0 30px 30px 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
            cursor: pointer;
            user-select: none;
            position: relative;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        th:hover {{
            background: #e9ecef;
        }}
        th.sortable::after {{
            content: ' ↕️';
            font-size: 0.8em;
            opacity: 0.5;
        }}
        th.sort-asc::after {{
            content: ' ↑';
            color: #007bff;
            opacity: 1;
        }}
        th.sort-desc::after {{
            content: ' ↓';
            color: #007bff;
            opacity: 1;
        }}
        .symbol-cell {{
            font-family: 'Courier New', monospace;
            font-weight: bold;
            color: #0066cc;
        }}
        .company-cell {{
            color: #666;
            font-size: 0.9em;
            min-width: 200px;
        }}
        .rsi-cell {{
            font-weight: bold;
            font-size: 1.1em;
            text-align: center;
        }}
        .rsi-oversold {{
            color: #27ae5f;
        }}
        .rsi-overbought {{
            color: #e74c3c;
        }}
        .rsi-neutral {{
            color: #f57c00;
        }}
        .no-data {{
            color: #999;
            font-style: italic;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }}
        @media (max-width: 768px) {{
            .container {{
                margin: 10px;
            }}
            .stats {{
                grid-template-columns: 1fr;
                padding: 20px;
            }}
            .table-container {{
                padding: 0 15px 20px 15px;
                overflow-x: auto;
            }}
            .company-cell {{
                min-width: 150px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Daily RSI Monitor</h1>
            <p>Colombo Stock Exchange</p>
        </div>
        
        <div class="timeframe-selector">
            <label class="selector-label">Select Timeframe:</label>
            <select class="timeframe-dropdown" id="timeframeSelect" onchange="switchTimeframe()">
                <option value="1h">1 Hour</option>
                <option value="1D" selected>1 Day</option>
                <option value="1W">1 Week</option>
                <option value="1M">1 Month</option>
            </select>
        </div>
        
        <div class="stats" id="statsSection">
            <!-- Stats will be updated by JavaScript -->
        </div>
        
        <div class="filter-info" id="filterInfo" style="display: none;">
            <!-- Filter info will be shown here -->
        </div>
        
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th class="sortable" onclick="sortTable(0)">Symbol</th>
                        <th class="sortable" onclick="sortTable(1)">Company</th>
                        <th class="sortable" onclick="sortTable(2)" id="rsiHeader">RSI</th>
                    </tr>
                </thead>
                <tbody id="stockTableBody">
                    <!-- Table body will be populated by JavaScript -->
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Updated daily at 4 PM</p>
            <p>Last successful update: {sl_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>

    <script>
        // Stock data with all timeframes
        const stockData = ["""
        
        # Add stock data as JavaScript array with all timeframes
        stock_entries = []
        for symbol, data in successful_results.items():
            clean_symbol = symbol.replace("CSELK-", "")
            company_name = SYMBOL_TO_COMPANY.get(symbol, "Unknown Company")
            rsi_data = data.get('rsi_data', {})
            
            # Create entry with all timeframes
            entry = f'["{clean_symbol}", "{company_name}"'
            for tf in self.timeframes:
                rsi_value = rsi_data.get(tf)
                if rsi_value is not None:
                    entry += f', {rsi_value}'
                else:
                    entry += ', null'
            entry += ']'
            stock_entries.append(entry)
        
        html += ',\n            '.join(stock_entries)
        
        html += f"""
        ];

        const timeframes = {json.dumps(self.timeframes)};
        let currentTimeframe = '1D';
        let currentSort = {{ column: 2, direction: 'asc' }};
        let currentFilter = null; // 'oversold', 'overbought', 'neutral', or null

        function getTimeframeIndex(timeframe) {{
            return timeframes.indexOf(timeframe) + 2; // +2 because first two columns are symbol and company
        }}

        function updateStats(timeframe) {{
            const timeframeIndex = getTimeframeIndex(timeframe);
            let oversold = 0, overbought = 0, neutral = 0, total = 0;
            
            stockData.forEach(row => {{
                const rsiValue = row[timeframeIndex];
                if (rsiValue !== null) {{
                    total++;
                    if (rsiValue < 50) oversold++;
                    else if (rsiValue > 70) overbought++;
                    else neutral++;
                }}
            }});
            
            document.getElementById('statsSection').innerHTML = `
                <div class="stat-card" onclick="filterStocks('oversold')" id="oversoldCard">
                    <div class="stat-number">${{oversold}}</div>
                    <div class="oversold">Oversold Stocks</div>
                    <small>(RSI < 50)</small>
                </div>
                <div class="stat-card" onclick="filterStocks('overbought')" id="overboughtCard">
                    <div class="stat-number">${{overbought}}</div>
                    <div class="overbought">Overbought Stocks</div>
                    <small>(RSI > 70)</small>
                </div>
                <div class="stat-card" onclick="filterStocks('neutral')" id="neutralCard">
                    <div class="stat-number">${{neutral}}</div>
                    <div class="neutral">Neutral Stocks</div>
                    <small>(RSI 50-70)</small>
                </div>
                <div class="stat-card" onclick="filterStocks('all')" id="allCard">
                    <div class="stat-number">${{total}}</div>
                    <div>Monitored</div>
                    <small>out of 304 stocks</small>
                </div>
            `;
            
            // Reapply active state if filter is active
            if (currentFilter) {{
                const activeCard = document.getElementById(currentFilter + 'Card');
                if (activeCard) {{
                    activeCard.classList.add('active');
                }}
            }}
        }}

        function getFilteredData(data, filter) {{
            if (!filter || filter === 'all') {{
                return data;
            }}
            
            const timeframeIndex = getTimeframeIndex(currentTimeframe);
            
            return data.filter(row => {{
                const rsiValue = row[timeframeIndex];
                if (rsiValue === null) return false;
                
                switch(filter) {{
                    case 'oversold':
                        return rsiValue < 50;
                    case 'overbought':
                        return rsiValue > 70;
                    case 'neutral':
                        return rsiValue >= 50 && rsiValue <= 70;
                    default:
                        return true;
                }}
            }});
        }}

        function updateFilterInfo() {{
            const filterInfo = document.getElementById('filterInfo');
            
            if (!currentFilter || currentFilter === 'all') {{
                filterInfo.style.display = 'none';
                return;
            }}
            
            let filterText = '';
            let countText = '';
            
            switch(currentFilter) {{
                case 'oversold':
                    filterText = 'Oversold Stocks (RSI < 50)';
                    countText = 'green';
                    break;
                case 'overbought':
                    filterText = 'Overbought Stocks (RSI > 70)';
                    countText = 'red';
                    break;
                case 'neutral':
                    filterText = 'Neutral Stocks (RSI 50-70)';
                    countText = 'orange';
                    break;
            }}
            
            const filteredData = getFilteredData(stockData, currentFilter);
            
            filterInfo.innerHTML = `
                Showing ${{filteredData.length}} ${{filterText}} for ${{currentTimeframe}} timeframe
                <span class="clear-filter" onclick="clearFilter()">Show All Stocks</span>
            `;
            filterInfo.style.display = 'block';
        }}

        function filterStocks(filterType) {{
            // Remove active class from all cards
            document.querySelectorAll('.stat-card').forEach(card => {{
                card.classList.remove('active');
            }});
            
            // Set current filter
            currentFilter = filterType === 'all' ? null : filterType;
            
            // Add active class to clicked card
            if (filterType !== 'all') {{
                const activeCard = document.getElementById(filterType + 'Card');
                if (activeCard) {{
                    activeCard.classList.add('active');
                }}
            }} else {{
                const allCard = document.getElementById('allCard');
                if (allCard) {{
                    allCard.classList.add('active');
                }}
            }}
            
            // Update filter info
            updateFilterInfo();
            
            // Apply filter and re-sort
            sortTable(currentSort.column);
        }}

        function clearFilter() {{
            currentFilter = null;
            
            // Remove active class from all cards
            document.querySelectorAll('.stat-card').forEach(card => {{
                card.classList.remove('active');
            }});
            
            // Add active to "all" card
            const allCard = document.getElementById('allCard');
            if (allCard) {{
                allCard.classList.add('active');
            }}
            
            updateFilterInfo();
            sortTable(currentSort.column);
        }}

        function updateTableBody(data, timeframe) {{
            const timeframeIndex = getTimeframeIndex(timeframe);
            
            // Apply current filter
            const filteredData = getFilteredData(data, currentFilter);
            
            const tbody = document.getElementById('stockTableBody');
            tbody.innerHTML = '';
            
            if (filteredData.length === 0) {{
                const tr = document.createElement('tr');
                const td = document.createElement('td');
                td.colSpan = 3;
                td.style.textAlign = 'center';
                td.style.padding = '30px';
                td.style.color = '#666';
                td.style.fontStyle = 'italic';
                td.textContent = 'No stocks match the current filter criteria';
                tr.appendChild(td);
                tbody.appendChild(tr);
                return;
            }}
            
            filteredData.forEach(row => {{
                const tr = document.createElement('tr');
                
                // Symbol
                const symbolTd = document.createElement('td');
                symbolTd.className = 'symbol-cell';
                symbolTd.textContent = row[0];
                tr.appendChild(symbolTd);
                
                // Company Name
                const companyTd = document.createElement('td');
                companyTd.className = 'company-cell';
                companyTd.textContent = row[1];
                tr.appendChild(companyTd);
                
                // RSI Value
                const rsiTd = document.createElement('td');
                rsiTd.className = 'rsi-cell';
                
                const rsiValue = row[timeframeIndex];
                if (rsiValue !== null) {{
                    rsiTd.textContent = rsiValue.toFixed(1);
                    if (rsiValue < 50) {{
                        rsiTd.classList.add('rsi-oversold');
                    }} else if (rsiValue > 70) {{
                        rsiTd.classList.add('rsi-overbought');
                    }} else {{
                        rsiTd.classList.add('rsi-neutral');
                    }}
                }} else {{
                    rsiTd.textContent = '--';
                    rsiTd.classList.add('no-data');
                }}
                
                tr.appendChild(rsiTd);
                tbody.appendChild(tr);
            }});
        }}

        function sortTable(columnIndex) {{
            const headers = document.querySelectorAll('th.sortable');
            
            // Remove previous sort classes
            headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
            
            // Determine sort direction
            if (currentSort.column === columnIndex) {{
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            }} else {{
                currentSort.direction = 'asc';
            }}
            currentSort.column = columnIndex;
            
            // Add sort class to current header
            const currentHeader = headers[columnIndex];
            currentHeader.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
            
            // Sort the data
            const timeframeIndex = getTimeframeIndex(currentTimeframe);
            const sortedData = [...stockData].sort((a, b) => {{
                let valueA, valueB;
                
                if (columnIndex === 0) {{ // Symbol
                    valueA = a[0].toLowerCase();
                    valueB = b[0].toLowerCase();
                }} else if (columnIndex === 1) {{ // Company
                    valueA = a[1].toLowerCase();
                    valueB = b[1].toLowerCase();
                }} else if (columnIndex === 2) {{ // RSI Value
                    valueA = a[timeframeIndex];
                    valueB = b[timeframeIndex];
                    
                    // Handle null values
                    if (valueA === null && valueB === null) return 0;
                    if (valueA === null) return 1;
                    if (valueB === null) return -1;
                }}
                
                if (currentSort.direction === 'asc') {{
                    return valueA < valueB ? -1 : valueA > valueB ? 1 : 0;
                }} else {{
                    return valueA > valueB ? -1 : valueA < valueB ? 1 : 0;
                }}
            }});
            
            updateTableBody(sortedData, currentTimeframe);
        }}

        function switchTimeframe() {{
            const select = document.getElementById('timeframeSelect');
            currentTimeframe = select.value;
            
            // Update header
            document.getElementById('rsiHeader').textContent = `RSI`;
            
            // Update stats
            updateStats(currentTimeframe);
            
            // Update filter info
            updateFilterInfo();
            
            // Update table
            sortTable(currentSort.column);
        }}

        // Initialize page
        document.addEventListener('DOMContentLoaded', function() {{
            switchTimeframe(); // Initialize with default timeframe
            sortTable(2); // Sort by RSI by default
        }});
    </script>
</body>
</html>"""
        
        with open('index.html', 'w') as f:
            f.write(html)
        
        successful_count = len(successful_results)
        print(f"📄 Generated index.html with {successful_count} stocks and {len(self.timeframes)} timeframes")
        return 'index.html'

# Stock symbols with company names
STOCK_DATA = [
    {"symbol": "CSELK-ABAN.N0000", "company": "ABANS ELECTRICALS PLC"},
    {"symbol": "CSELK-AFSL.N0000", "company": "ABANS FINANCE PLC"},
    {"symbol": "CSELK-AEL.N0000", "company": "ACCESS ENGINEERING PLC"},
    {"symbol": "CSELK-ACL.N0000", "company": "ACL CABLES PLC"},
    {"symbol": "CSELK-APLA.N0000", "company": "ACL PLASTICS PLC"},
    {"symbol": "CSELK-ACME.N0000", "company": "ACME PRINTING & PACKAGING PLC"},
    {"symbol": "CSELK-AGAL.N0000", "company": "AGALAWATTE PLANTATIONS PLC"},
    {"symbol": "CSELK-AGST.N0000", "company": "AGSTAR PLC"},
    {"symbol": "CSELK-AGST.X0000", "company": "AGSTAR PLC - Non Voting"},
    {"symbol": "CSELK-AHUN.N0000", "company": "AHUNGALLA RESORTS LTD"},
    {"symbol": "CSELK-ASPM.N0000", "company": "ASIA SIYAKA COMMODITIES PLC"},
    {"symbol": "CSELK-SPEN.N0000", "company": "ASIAN ALLIANCE INSURANCE PLC"},
    {"symbol": "CSELK-ALLI.N0000", "company": "ALLIANCE FINANCE COMPANY PLC"},
    {"symbol": "CSELK-AFS.N0000", "company": "ASIA ASSET FINANCE PLC"},
    {"symbol": "CSELK-ALUM.N0000", "company": "ALUMEX PLC"},
    {"symbol": "CSELK-ABL.N0000", "company": "AMANA BANK PLC"},
    {"symbol": "CSELK-ATL.N0000", "company": "AMANA TAKAFUL PLC"},
    {"symbol": "CSELK-ATLL.N0000", "company": "AMANA TAKAFUL LIFE PLC"},
    {"symbol": "CSELK-GREG.N0000", "company": "AMBEON HOLDINGS PLC"},
    {"symbol": "CSELK-AMCL.N0000", "company": "AMW CAPITAL LEASING & FINANCE PLC"},
    {"symbol": "CSELK-ALHP.N0000", "company": "ALHOKAIR GROUP (LANKA) LIMITED"},
    {"symbol": "CSELK-AINS.N0000", "company": "AITKEN SPENCE INSURANCE PLC"},
    {"symbol": "CSELK-AAF.N0000", "company": "ASIA ASSET FINANCE PLC"},
    {"symbol": "CSELK-AAF.P0000", "company": "ASIA ASSET FINANCE PLC - Preference"},
    {"symbol": "CSELK-ACAP.N0000", "company": "ACCESS CAPITAL PARTNERS PLC"},
    {"symbol": "CSELK-ASIY.N0000", "company": "ASIA SIYAKA COMMODITIES PLC"},
    {"symbol": "CSELK-AHPL.N0000", "company": "AITKEN SPENCE HOTEL HOLDINGS PLC"},
    {"symbol": "CSELK-AMSL.N0000", "company": "AITKEN SPENCE MARITIME & LOGISTICS PLC"},
    {"symbol": "CSELK-ASIR.N0000", "company": "AITKEN SPENCE INSURANCE REINSURANCE PLC"},
    {"symbol": "CSELK-AMF.N0000", "company": "ASIA ASSET FINANCE PLC"},
    {"symbol": "CSELK-AGPL.N0000", "company": "AGALAWATTE PLANTATIONS PLC"},
    {"symbol": "CSELK-BPPL.N0000", "company": "B P P L HOLDINGS PLC"},
    {"symbol": "CSELK-BFL.N0000", "company": "BAIRAHA FARMS PLC"},
    {"symbol": "CSELK-BALA.N0000", "company": "BALANGODA PLANTATIONS PLC"},
    {"symbol": "CSELK-BRR.N0000", "company": "BANSEI ROYAL RESORTS HIKKADUWA PLC"},
    {"symbol": "CSELK-BERU.N0000", "company": "BERUWALA RESORTS PLC"},
    {"symbol": "CSELK-BLI.N0000", "company": "BIMPUTH LANKA INVESTMENTS PLC"},
    {"symbol": "CSELK-BLUE.X0000", "company": "BLUE DIAMONDS JEWELLERY WORLDWIDE PLC - Non Voting"},
    {"symbol": "CSELK-BLUE.N0000", "company": "BLUE DIAMONDS JEWELLERY WORLDWIDE PLC"},
    {"symbol": "CSELK-BOGA.N0000", "company": "BOGALA GRAPHITE LANKA PLC"},
    {"symbol": "CSELK-BOPL.N0000", "company": "BOGAWANTALAWA TEA ESTATES PLC"},
    {"symbol": "CSELK-BRWN.N0000", "company": "BROWN & COMPANY PLC"},
    {"symbol": "CSELK-BBH.N0000", "company": "BROWNS BEACH HOTELS PLC"},
    {"symbol": "CSELK-BIL.N0000", "company": "BROWNS INVESTMENTS PLC"},
    {"symbol": "CSELK-BUKI.N0000", "company": "BUKIT DARAH PLC"},
    {"symbol": "CSELK-COLO.N0000", "company": "C M HOLDINGS PLC"},
    {"symbol": "CSELK-CTHR.N0000", "company": "C T HOLDINGS PLC"},
    {"symbol": "CSELK-CTLD.N0000", "company": "C T LAND DEVELOPMENT PLC"},
    {"symbol": "CSELK-CWM.N0000", "company": "C. W. MACKIE PLC"},
    {"symbol": "CSELK-CSLK.N0000", "company": "CABLE SOLUTIONS PLC"},
    {"symbol": "CSELK-CALC.U0000", "company": "CAL FIVE YEAR CLOSED END FUND (Units)"},
    {"symbol": "CSELK-CALI.U0000", "company": "CAL FIVE YEAR OPTIMUM FUND (Units)"},
    {"symbol": "CSELK-CALH.N0000", "company": "CAPITAL ALLIANCE HOLDINGS LIMITED"},
    {"symbol": "CSELK-CALT.N0000", "company": "CAPITAL ALLIANCE PLC"},
    {"symbol": "CSELK-CARG.N0000", "company": "CARGILLS (CEYLON) PLC"},
    {"symbol": "CSELK-CBNK.N0000", "company": "CARGILLS BANK PLC"},
    {"symbol": "CSELK-CABO.N0000", "company": "CARGO BOAT DEVELOPMENT COMPANY PLC"},
    {"symbol": "CSELK-CARS.N0000", "company": "CARSON CUMBERBATCH PLC"},
    {"symbol": "CSELK-CFIN.N0000", "company": "CENTRAL FINANCE COMPANY PLC"},
    {"symbol": "CSELK-CIND.N0000", "company": "CENTRAL INDUSTRIES PLC"},
    {"symbol": "CSELK-CINS.X0000", "company": "CEYLINCO HOLDINGS PLC - Non Voting"},
    {"symbol": "CSELK-CINS.N0000", "company": "CEYLINCO HOLDINGS PLC"},
    {"symbol": "CSELK-BREW.N0000", "company": "CEYLON BEVERAGE HOLDINGS PLC"},
    {"symbol": "CSELK-CCS.N0000", "company": "CEYLON COLD STORES PLC"},
    {"symbol": "CSELK-GRAN.N0000", "company": "CEYLON GRAIN ELEVATORS PLC"},
    {"symbol": "CSELK-GUAR.N0000", "company": "CEYLON GUARDIAN INVESTMENT TRUST PLC"},
    {"symbol": "CSELK-CHL.X0000", "company": "CEYLON HOSPITALS PLC - Non Voting"},
    {"symbol": "CSELK-CHL.N0000", "company": "CEYLON HOSPITALS PLC"},
    {"symbol": "CSELK-CHOT.N0000", "company": "CEYLON HOTELS CORPORATION PLC"},
    {"symbol": "CSELK-CINV.N0000", "company": "CEYLON INVESTMENT PLC"},
    {"symbol": "CSELK-KZOO.N0000", "company": "CEYLON LAND & EQUITY PLC"},
    {"symbol": "CSELK-CPRT.N0000", "company": "CEYLON PRINTERS PLC"},
    {"symbol": "CSELK-CTBL.N0000", "company": "CEYLON TEA BROKERS PLC"},
    {"symbol": "CSELK-CTC.N0000", "company": "CEYLON TOBACCO COMPANY PLC"},
    {"symbol": "CSELK-CHMX.N0000", "company": "CHEMANEX PLC"},
    {"symbol": "CSELK-LLUB.N0000", "company": "CHEVRON LUBRICANTS LANKA PLC"},
    {"symbol": "CSELK-CWL.N0000", "company": "CHRISSWORLD PLC"},
    {"symbol": "CSELK-CIC.X0000", "company": "C I C HOLDINGS PLC - Non Voting"},
    {"symbol": "CSELK-CIC.N0000", "company": "C I C HOLDINGS PLC"},
    {"symbol": "CSELK-CDB.N0000", "company": "CITIZENS DEVELOPMENT BUSINESS FINANCE PLC"},
    {"symbol": "CSELK-CDB.X0000", "company": "CITIZENS DEVELOPMENT BUSINESS FINANCE PLC - Non Voting"},
    {"symbol": "CSELK-REEF.N0000", "company": "CITRUS LEISURE PLC"},
    {"symbol": "CSELK-CHOU.N0000", "company": "CITY HOUSING & REAL ESTATE CO. PLC"},
    {"symbol": "CSELK-COOP.N0000", "company": "Co-operative Insurance Company PLC"},
    {"symbol": "CSELK-PHAR.N0000", "company": "COLOMBO CITY HOLDINGS PLC"},
    {"symbol": "CSELK-DOCK.N0000", "company": "COLOMBO DOCKYARD PLC"},
    {"symbol": "CSELK-CFI.N0000", "company": "COLOMBO FORT INVESTMENTS PLC"},
    {"symbol": "CSELK-CIT.N0000", "company": "COLOMBO INVESTMENT TRUST PLC"},
    {"symbol": "CSELK-CLND.N0000", "company": "COLOMBO LAND AND DEVELOPMENT COMPANY PLC"},
    {"symbol": "CSELK-COMB.N0000", "company": "COMMERCIAL BANK OF CEYLON PLC"},
    {"symbol": "CSELK-COMB.X0000", "company": "COMMERCIAL BANK OF CEYLON PLC - Non Voting"},
    {"symbol": "CSELK-COCR.N0000", "company": "COMMERCIAL CREDIT AND FINANCE PLC"},
    {"symbol": "CSELK-COMD.N0000", "company": "COMMERCIAL DEVELOPMENT COMPANY PLC"},
    {"symbol": "CSELK-SOY.N0000", "company": "CONVENIENCE FOODS LANKA PLC"},
    {"symbol": "CSELK-DPL.N0000", "company": "DANKOTUWA PORCELAIN PLC"},
    {"symbol": "CSELK-DFCC.N0000", "company": "DFCC BANK PLC"},
    {"symbol": "CSELK-DIAL.N0000", "company": "DIALOG AXIATA PLC"},
    {"symbol": "CSELK-CALF.N0000", "company": "DIALOG FINANCE PLC"},
    {"symbol": "CSELK-DIMO.N0000", "company": "DIESEL & MOTOR ENGINEERING PLC"},
    {"symbol": "CSELK-PKME.N0000", "company": "DIGITAL MOBILITY SOLUTIONS LANKA PLC"},
    {"symbol": "CSELK-CTEA.N0000", "company": "DILMAH CEYLON TEA COMPANY PLC"},
    {"symbol": "CSELK-DIPD.N0000", "company": "DIPPED PRODUCTS PLC"},
    {"symbol": "CSELK-DIST.N0000", "company": "DISTILLERIES COMPANY OF SRI LANKA PLC"},
    {"symbol": "CSELK-STAF.N0000", "company": "DOLPHIN HOTELS PLC"},
    {"symbol": "CSELK-ASCO.N0000", "company": "LANKA REALTY INVESTMENTS PLC"},
    {"symbol": "CSELK-ASHO.N0000", "company": "LANKA ASHOK LEYLAND PLC"},
    {"symbol": "CSELK-ASPH.N0000", "company": "INDUSTRIAL ASPHALTS (CEYLON) PLC"},
    {"symbol": "CSELK-BFN.N0000", "company": "JANASHAKTHI FINANCE PLC"},
    {"symbol": "CSELK-CERA.N0000", "company": "LANKA CERAMIC PLC"},
    {"symbol": "CSELK-CFVF.N0000", "company": "FIRST CAPITAL HOLDINGS PLC"},
    {"symbol": "CSELK-CITH.N0000", "company": "HIKKADUWA BEACH RESORT PLC"},
    {"symbol": "CSELK-CONN.N0000", "company": "HAYLEYS LEISURE PLC"},
    {"symbol": "CSELK-CSF.N0000", "company": "NATION LANKA FINANCE PLC"},
    {"symbol": "CSELK-EAST.N0000", "company": "EAST WEST PROPERTIES PLC"},
    {"symbol": "CSELK-EBCR.N0000", "company": "E B CREASY & COMPANY PLC"},
    {"symbol": "CSELK-ECL.N0000", "company": "E - CHANNELLING PLC"},
    {"symbol": "CSELK-EDEN.N0000", "company": "EDEN HOTEL LANKA PLC"},
    {"symbol": "CSELK-ELPL.N0000", "company": "ELPITIYA PLANTATIONS PLC"},
    {"symbol": "CSELK-EMER.N0000", "company": "EASTERN MERCHANTS PLC"},
    {"symbol": "CSELK-EML.N0000", "company": "E M L CONSULTANTS PLC"},
    {"symbol": "CSELK-ETWO.N0000", "company": "EQUITY TWO PLC"},
    {"symbol": "CSELK-EXT.N0000", "company": "EXTERMINATORS PLC"},
    {"symbol": "CSELK-FCT.N0000", "company": "First Capital Treasuries PLC"},
    {"symbol": "CSELK-GEST.N0000", "company": "GESTETNER OF CEYLON PLC"},
    {"symbol": "CSELK-GHLL.N0000", "company": "GALADARI HOTELS (LANKA) PLC"},
    {"symbol": "CSELK-HAPU.N0000", "company": "HAPUGASTENNE PLANTATIONS PLC"},
    {"symbol": "CSELK-HARI.N0000", "company": "HARISCHANDRA MILLS PLC"},
    {"symbol": "CSELK-HASU.N0000", "company": "HNB ASSURANCE PLC"},
    {"symbol": "CSELK-HAYC.N0000", "company": "HAYCARB PLC"},
    {"symbol": "CSELK-HAYL.N0000", "company": "HAYLEYS PLC"},
    {"symbol": "CSELK-HBS.N0000", "company": "hSenid Business Solutions PLC"},
    {"symbol": "CSELK-HDFC.N0000", "company": "HOUSING DEVELOPMENT FINANCE CORPORATION BANK OF SL"},
    {"symbol": "CSELK-HELA.N0000", "company": "HELA APPAREL HOLDINGS PLC"},
    {"symbol": "CSELK-HEXP.N0000", "company": "HAYLEYS FIBRE PLC"},
    {"symbol": "CSELK-HHL.N0000", "company": "HEMAS HOLDINGS PLC"},
    {"symbol": "CSELK-HNB.N0000", "company": "HATTON NATIONAL BANK PLC"},
    {"symbol": "CSELK-HNB.X0000", "company": "HATTON NATIONAL BANK PLC"},
    {"symbol": "CSELK-HNBF.N0000", "company": "HNB FINANCE PLC"},
    {"symbol": "CSELK-HNBF.R0000", "company": "HNB FINANCE PLC"},
    {"symbol": "CSELK-HNBF.R0001", "company": "HNB FINANCE PLC"},
    {"symbol": "CSELK-HNBF.X0000", "company": "HNB FINANCE PLC"},
    {"symbol": "CSELK-HOPL.N0000", "company": "HORANA PLANTATIONS PLC"},
    {"symbol": "CSELK-HPFL.N0000", "company": "LOTUS HYDRO POWER PLC"},
    {"symbol": "CSELK-HPL.N0000", "company": "HATTON PLANTATIONS PLC"},
    {"symbol": "CSELK-HSIG.N0000", "company": "HOTEL SIGIRIYA PLC"},
    {"symbol": "CSELK-HUNA.N0000", "company": "HUNAS HOLDINGS PLC"},
    {"symbol": "CSELK-HUNT.N0000", "company": "HUNTER & COMPANY PLC"},
    {"symbol": "CSELK-HVA.N0000", "company": "HVA FOODS PLC"},
    {"symbol": "CSELK-JAT.N0000", "company": "JAT HOLDINGS PLC"},
    {"symbol": "CSELK-JETS.N0000", "company": "JETWING SYMPHONY PLC"},
    {"symbol": "CSELK-JINS.N0000", "company": "JANASHAKTHI INSURANCE PLC"},
    {"symbol": "CSELK-JKH.N0000", "company": "JOHN KEELLS HOLDINGS PLC"},
    {"symbol": "CSELK-JKL.N0000", "company": "JOHN KEELLS PLC"},
    {"symbol": "CSELK-KAHA.N0000", "company": "KAHAWATTE PLANTATIONS PLC"},
    {"symbol": "CSELK-KCAB.N0000", "company": "KELANI CABLES PLC"},
    {"symbol": "CSELK-KDL.N0000", "company": "KELSEY DEVELOPMENTS PLC"},
    {"symbol": "CSELK-KFP.N0000", "company": "KEELLS FOOD PRODUCTS PLC"},
    {"symbol": "CSELK-KGAL.N0000", "company": "KEGALLE PLANTATIONS PLC"},
    {"symbol": "CSELK-KHL.N0000", "company": "JOHN KEELLS HOTELS PLC"},
    {"symbol": "CSELK-KOTA.N0000", "company": "KOTAGALA PLANTATIONS PLC"},
    {"symbol": "CSELK-KPHL.N0000", "company": "KAPRUKA HOLDINGS PLC"},
    {"symbol": "CSELK-KVAL.N0000", "company": "KELANI VALLEY PLANTATIONS PLC"},
    {"symbol": "CSELK-LALU.N0000", "company": "LANKA ALUMINIUM INDUSTRIES PLC"},
    {"symbol": "CSELK-LAMB.N0000", "company": "KOTMALE HOLDINGS PLC"},
    {"symbol": "CSELK-LCBF.N0000", "company": "LANKA CREDIT AND BUSINESS FINANCE PLC"},
    {"symbol": "CSELK-LCEY.N0000", "company": "LANKEM CEYLON PLC"},
    {"symbol": "CSELK-LDEV.N0000", "company": "LANKEM DEVELOPMENTS PLC"},
    {"symbol": "CSELK-LFIN.N0000", "company": "LB FINANCE PLC"},
    {"symbol": "CSELK-LGIL.N0000", "company": "LOLC GENERAL INSURANCE PLC"},
    {"symbol": "CSELK-LGL.N0000", "company": "LAUGFS GAS PLC"},
    {"symbol": "CSELK-LGL.X0000", "company": "LAUGFS GAS PLC"},
    {"symbol": "CSELK-LIOC.N0000", "company": "LANKA IOC PLC"},
    {"symbol": "CSELK-LION.N0000", "company": "LION BREWERY (CEYLON) PLC"},
    {"symbol": "CSELK-LITE.N0000", "company": "LAXAPANA PLC"},
    {"symbol": "CSELK-LMF.N0000", "company": "LANKA MILK FOODS (CWE) PLC"},
    {"symbol": "CSELK-LOFC.N0000", "company": "LOLC FINANCE PLC"},
    {"symbol": "CSELK-LOLC.N0000", "company": "L O L C HOLDINGS PLC"},
    {"symbol": "CSELK-LPL.N0000", "company": "LAUGFS POWER PLC"},
    {"symbol": "CSELK-LPL.X0000", "company": "LAUGFS POWER PLC"},
    {"symbol": "CSELK-LPRT.N0000", "company": "LAKE HOUSE PRINTERS & PUBLISHERS PLC"},
    {"symbol": "CSELK-LUMX.N0000", "company": "LUMINEX PLC"},
    {"symbol": "CSELK-LVEF.N0000", "company": "L V L ENERGY FUND PLC"},
    {"symbol": "CSELK-LVEN.N0000", "company": "LANKA VENTURES PLC"},
    {"symbol": "CSELK-LWL.N0000", "company": "LANKA WALLTILE PLC"},
    {"symbol": "CSELK-MADU.N0000", "company": "MADULSIMA PLANTATIONS PLC"},
    {"symbol": "CSELK-MAL.N0000", "company": "MALWATTE VALLEY PLANTATION PLC"},
    {"symbol": "CSELK-MAL.X0000", "company": "MALWATTE VALLEY PLANTATION PLC"},
    {"symbol": "CSELK-MAWA.N0000", "company": "MARAWILA RESORTS PLC"},
    {"symbol": "CSELK-MASK.N0000", "company": "MASKELIYA PLANTATIONS PLC"},
    {"symbol": "CSELK-MBSL.N0000", "company": "MERCHANT BANK OF SRI LANKA & FINANCE PLC"},
    {"symbol": "CSELK-MCPL.N0000", "company": "MAHAWELI COCONUT PLANTATIONS PLC"},
    {"symbol": "CSELK-MDL.N0000", "company": "MYLAND DEVELOPMENTS PLC"},
    {"symbol": "CSELK-MEL.N0000", "company": "GREENTECH ENERGY PLC"},
    {"symbol": "CSELK-MELS.N0000", "company": "MELSTACORP PLC"},
    {"symbol": "CSELK-MERC.N0000", "company": "MERCANTILE INVESTMENTS AND FINANCE PLC"},
    {"symbol": "CSELK-MFPE.N0000", "company": "MAHARAJA FOODS PLC"},
    {"symbol": "CSELK-MGT.N0000", "company": "HAYLEYS FABRIC PLC"},
    {"symbol": "CSELK-MHDL.N0000", "company": "MILLENNIUM HOUSING DEVELOPERS PLC"},
    {"symbol": "CSELK-MRH.N0000", "company": "MAHAWELI REACH HOTELS PLC"},
    {"symbol": "CSELK-MSL.N0000", "company": "MERCANTILE SHIPPING COMPANY PLC"},
    {"symbol": "CSELK-MULL.N0000", "company": "MULLER & PHIPPS (CEYLON) PLC"},
    {"symbol": "CSELK-NAMU.N0000", "company": "NAMUNUKULA PLANTATIONS PLC"},
    {"symbol": "CSELK-NAVF.U0000", "company": "NAMAL ACUITY VALUE FUND"},
    {"symbol": "CSELK-NDB.N0000", "company": "NATIONAL DEVELOPMENT BANK PLC"},
    {"symbol": "CSELK-NHL.N0000", "company": "NAWALOKA HOSPITALS PLC"},
    {"symbol": "CSELK-NTB.N0000", "company": "NATIONS TRUST BANK PLC"},
    {"symbol": "CSELK-NTB.X0000", "company": "NATIONS TRUST BANK PLC"},
    {"symbol": "CSELK-PACK.N0000", "company": "Ex-pack Corrugated Cartons PLC"},
    {"symbol": "CSELK-SHAW.N0000", "company": "LEE HEDGES PLC"},
    {"symbol": "CSELK-TILE.N0000", "company": "LANKA TILES PLC"},
    {"symbol": "CSELK-TYRE.N0000", "company": "KELANI TYRES PLC"},
    {"symbol": "CSELK-WAPO.N0000", "company": "GALLE FACE CAPITAL PARTNERS PLC"},
    {"symbol": "CSELK-AAIC.N0000", "company": "SOFTLOGIC LIFE INSURANCE PLC"},
    {"symbol": "CSELK-AUTO.N0000", "company": "THE AUTODROME PLC"},
    {"symbol": "CSELK-CARE.N0000", "company": "PRINTCARE PLC"},
    {"symbol": "CSELK-CFLB.N0000", "company": "THE COLOMBO FORT LAND AND BUILDING PLC"},
    {"symbol": "CSELK-COCO.N0000", "company": "RENUKA FOODS PLC"},
    {"symbol": "CSELK-COCO.X0000", "company": "RENUKA FOODS PLC"},
    {"symbol": "CSELK-COF.U0000", "company": "SENFIN SECURITIES LIMITED"},
    {"symbol": "CSELK-CRL.N0000", "company": "SOFTLOGIC FINANCE PLC"},
    {"symbol": "CSELK-CSD.N0000", "company": "SEYLAN DEVELOPMENTS PLC"},
    {"symbol": "CSELK-GLAS.N0000", "company": "PGP GLASS CEYLON PLC"},
    {"symbol": "CSELK-HPWR.N0000", "company": "RESUS ENERGY PLC"},
    {"symbol": "CSELK-IDL.N0000", "company": "SERENDIB ENGINEERING GROUP PLC"},
    {"symbol": "CSELK-KHC.N0000", "company": "THE KANDY HOTELS COMPANY (1938) PLC"},
    {"symbol": "CSELK-LHCL.N0000", "company": "THE LANKA HOSPITALS CORPORATION PLC"},
    {"symbol": "CSELK-LHL.N0000", "company": "THE LIGHTHOUSE HOTEL PLC"},
    {"symbol": "CSELK-NEH.N0000", "company": "THE NUWARA ELIYA HOTELS COMPANY PLC"},
    {"symbol": "CSELK-ODEL.N0000", "company": "ODEL PLC"},
    {"symbol": "CSELK-OFEQ.N0000", "company": "OFFICE EQUIPMENT PLC"},
    {"symbol": "CSELK-ONAL.N0000", "company": "ON'ALLY HOLDINGS PLC"},
    {"symbol": "CSELK-OSEA.N0000", "company": "OVERSEAS REALTY (CEYLON) PLC"},
    {"symbol": "CSELK-PABC.N0000", "company": "PAN ASIA BANKING CORPORATION PLC"},
    {"symbol": "CSELK-PALM.N0000", "company": "PALM GARDEN HOTELS PLC"},
    {"symbol": "CSELK-PAP.N0000", "company": "PANASIAN POWER PLC"},
    {"symbol": "CSELK-PARA.N0000", "company": "PARAGON CEYLON PLC"},
    {"symbol": "CSELK-PARQ.N0000", "company": "SWISSTEK (CEYLON) PLC"},
    {"symbol": "CSELK-PEG.N0000", "company": "PEGASUS HOTELS OF CEYLON PLC"},
    {"symbol": "CSELK-PINS.N0000", "company": "PEOPLE'S INSURANCE PLC"},
    {"symbol": "CSELK-PLC.N0000", "company": "PEOPLE'S LEASING & FINANCE PLC"},
    {"symbol": "CSELK-PLR.N0000", "company": "PRIME LANDS RESIDENCIES PLC"},
    {"symbol": "CSELK-PMB.N0000", "company": "PMF FINANCE PLC"},
    {"symbol": "CSELK-RAL.N0000", "company": "RENUKA AGRI FOODS PLC"},
    {"symbol": "CSELK-RCH.N0000", "company": "RENUKA HOTELS PLC"},
    {"symbol": "CSELK-RCL.N0000", "company": "ROYAL CERAMICS LANKA PLC"},
    {"symbol": "CSELK-RENU.N0000", "company": "RENUKA CITY HOTELS PLC."},
    {"symbol": "CSELK-REXP.N0000", "company": "RICHARD PIERIS EXPORTS PLC"},
    {"symbol": "CSELK-RFL.N0000", "company": "RAMBODA FALLS PLC"},
    {"symbol": "CSELK-RGEM.N0000", "company": "RADIANT GEMS INTERNATIONAL PLC"},
    {"symbol": "CSELK-RHL.N0000", "company": "RENUKA HOLDINGS PLC"},
    {"symbol": "CSELK-RHL.X0000", "company": "RENUKA HOLDINGS PLC"},
    {"symbol": "CSELK-RHTL.N0000", "company": "THE FORTRESS RESORTS PLC"},
    {"symbol": "CSELK-RICH.N0000", "company": "RICHARD PIERIS AND COMPANY PLC"},
    {"symbol": "CSELK-RIL.N0000", "company": "R I L PROPERTY PLC"},
    {"symbol": "CSELK-RPBH.N0000", "company": "ROYAL PALMS BEACH HOTELS PLC"},
    {"symbol": "CSELK-RWSL.N0000", "company": "RAIGAM WAYAMBA SALTERNS PLC"},
    {"symbol": "CSELK-SAMP.N0000", "company": "SAMPATH BANK PLC"},
    {"symbol": "CSELK-SCAP.N0000", "company": "SOFTLOGIC CAPITAL PLC"},
    {"symbol": "CSELK-SDB.N0000", "company": "SANASA DEVELOPMENT BANK PLC"},
    {"symbol": "CSELK-SDF.N0000", "company": "SARVODAYA DEVELOPMENT FINANCE PLC"},
    {"symbol": "CSELK-SEMB.N0000", "company": "SMB FINANCE PLC"},
    {"symbol": "CSELK-SEMB.X0000", "company": "SMB FINANCE PLC"},
    {"symbol": "CSELK-SERV.N0000", "company": "THE KINGSBURY PLC"},
    {"symbol": "CSELK-SEYB.N0000", "company": "SEYLAN BANK PLC"},
    {"symbol": "CSELK-SEYB.X0000", "company": "SEYLAN BANK PLC"},
    {"symbol": "CSELK-SFCL.N0000", "company": "SENKADAGALA FINANCE COMPANY PLC"},
    {"symbol": "CSELK-SFIN.N0000", "company": "SINGER FINANCE LANKA PLC"},
    {"symbol": "CSELK-SHL.N0000", "company": "SOFTLOGIC HOLDINGS PLC"},
    {"symbol": "CSELK-SHL.W0000", "company": "SOFTLOGIC HOLDINGS PLC"},
    {"symbol": "CSELK-SHOT.N0000", "company": "SERENDIB HOTELS PLC"},
    {"symbol": "CSELK-SHOT.X0000", "company": "SERENDIB HOTELS PLC"},
    {"symbol": "CSELK-SIGV.N0000", "company": "SIGIRIYA VILLAGE HOTELS PLC"},
    {"symbol": "CSELK-SIL.N0000", "company": "SAMSON INTERNATIONAL PLC"},
    {"symbol": "CSELK-SING.N0000", "company": "STANDARD CAPITAL PLC"},
    {"symbol": "CSELK-SINH.N0000", "company": "SINGHE HOSPITALS PLC"},
    {"symbol": "CSELK-SINS.N0000", "company": "SINGER (SRI LANKA) PLC"},
    {"symbol": "CSELK-SIRA.N0000", "company": "SIERRA CABLES PLC"},
    {"symbol": "CSELK-SLND.N0000", "company": "SERENDIB LAND PLC"},
    {"symbol": "CSELK-SLTL.N0000", "company": "SRI LANKA TELECOM PLC"},
    {"symbol": "CSELK-SMOT.N0000", "company": "SATHOSA MOTORS PLC"},
    {"symbol": "CSELK-SUN.N0000", "company": "SUNSHINE HOLDINGS PLC"},
    {"symbol": "CSELK-SWAD.N0000", "company": "SWADESHI INDUSTRIAL WORKS PLC"},
    {"symbol": "CSELK-TAFL.N0000", "company": "THREE ACRE FARMS PLC"},
    {"symbol": "CSELK-TAJ.N0000", "company": "TAL LANKA HOTELS PLC"},
    {"symbol": "CSELK-TANG.N0000", "company": "TANGERINE BEACH HOTELS PLC"},
    {"symbol": "CSELK-TESS.N0000", "company": "TESS AGRO PLC"},
    {"symbol": "CSELK-TESS.X0000", "company": "TESS AGRO PLC"},
    {"symbol": "CSELK-TJL.N0000", "company": "TEEJAY LANKA PLC"},
    {"symbol": "CSELK-TKYO.N0000", "company": "TOKYO CEMENT COMPANY (LANKA) PLC"},
    {"symbol": "CSELK-TKYO.X0000", "company": "TOKYO CEMENT COMPANY (LANKA) PLC"},
    {"symbol": "CSELK-TPL.N0000", "company": "TALAWAKELLE TEA ESTATES PLC"},
    {"symbol": "CSELK-TRAN.N0000", "company": "TRANS ASIA HOTELS PLC"},
    {"symbol": "CSELK-TSML.N0000", "company": "TEA SMALLHOLDER FACTORIES PLC"},
    {"symbol": "CSELK-UAL.N0000", "company": "UNION ASSURANCE PLC"},
    {"symbol": "CSELK-UBC.N0000", "company": "UNION BANK OF COLOMBO PLC"},
    {"symbol": "CSELK-UBF.N0000", "company": "UB FINANCE PLC"},
    {"symbol": "CSELK-UCAR.N0000", "company": "UNION CHEMICALS LANKA PLC"},
    {"symbol": "CSELK-UDPL.N0000", "company": "UDAPUSSELLAWA PLANTATIONS PLC"},
    {"symbol": "CSELK-UML.N0000", "company": "UNITED MOTORS LANKA PLC"},
    {"symbol": "CSELK-VFIN.N0000", "company": "VALLIBEL FINANCE PLC"},
    {"symbol": "CSELK-VLL.N0000", "company": "VIDULLANKA PLC"},
    {"symbol": "CSELK-VLL.X0000", "company": "VIDULLANKA PLC"},
    {"symbol": "CSELK-VONE.N0000", "company": "VALLIBEL ONE PLC"},
    {"symbol": "CSELK-VPEL.N0000", "company": "VALLIBEL POWER ERATHNA PLC"}
]

# Extract just symbols for backward compatibility
STOCK_SYMBOLS = [stock["symbol"] for stock in STOCK_DATA]

# Create a mapping for easy lookup
SYMBOL_TO_COMPANY = {stock["symbol"]: stock["company"] for stock in STOCK_DATA}

if __name__ == "__main__":
    print("🤖 Multi-Timeframe RSI Scraper for GitHub Pages")
    print("=" * 60)
    
    # Initialize scraper
    base_url = "https://tradingview.com/symbols/{SYMBOL}/technicals/"
    scraper = MultiTimeframeRSIScraper(base_url, STOCK_SYMBOLS)
    
    # Fetch all RSI data for all timeframes
    results = scraper.fetch_all_rsi()
    
    if results:
        # Save data files
        json_file = scraper.save_daily_data()
        
        # Generate HTML page
        html_file = scraper.generate_html_page()
        
        print("\n🎉 Multi-timeframe RSI fetch completed!")
        print(f"📊 Generated files:")
        print(f"   • {json_file} (daily data with all timeframes)")
        print(f"   • latest_rsi.json (for API access)")
        print(f"   • {html_file} (GitHub Pages website)")
        print(f"\n📈 Timeframes included: {', '.join(scraper.timeframes)}")
        print("\n📤 Ready to upload to GitHub!")
        
    else:
        print("❌ No data retrieved. Check your internet connection and try again.")
