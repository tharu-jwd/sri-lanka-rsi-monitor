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
        .oversold {{ color: #e74c3c; }}
        .overbought {{ color: #f39c12; }}
        .neutral {{ color: #27ae60; }}
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
            color: #2e7d32;
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
                <option value="1h">1 Hour RSI</option>
                <option value="1D" selected>1 Day RSI (Default)</option>
                <option value="1W">1 Week RSI</option>
                <option value="1M">1 Month RSI</option>
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
                        <th class="sortable" onclick="sortTable(2)" id="rsiHeader">RSI Value (1D)</th>
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
                    <div>Total Available</div>
                    <small>of {len(self.symbols)} symbols</small>
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
            document.getElementById('rsiHeader').textContent = `RSI Value (${{currentTimeframe}})`;
            
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
