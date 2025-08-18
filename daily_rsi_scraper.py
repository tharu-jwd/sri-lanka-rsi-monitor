import time
import json
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

class DailyRSIScraper:
    def __init__(self, base_url, symbols):
        self.base_url = base_url
        self.symbols = symbols
        self.results = {}
    
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
            driver.implicitly_wait(10)
            return driver
        except Exception as e:
            print(f"Error creating Chrome driver: {e}")
            return None
    
    def build_url(self, symbol):
        """Build complete URL for a given symbol"""
        return self.base_url.replace("{SYMBOL}", symbol)
    
    def fetch_single_rsi(self, symbol):
        """Fetch RSI for a single stock symbol"""
        driver = None
        try:
            driver = self.create_driver()
            if not driver:
                return None, "Could not create Chrome driver"
            
            url = self.build_url(symbol)
            driver.get(url)
            time.sleep(5)
            
            wait = WebDriverWait(driver, 30)
            
            # Look for RSI row
            rsi_row = wait.until(
                EC.presence_of_element_located((By.XPATH, "//tr[contains(., 'Relative Strength Index')]"))
            )
            
            time.sleep(3)
            
            # Get the value cell
            value_cell = driver.find_element(By.XPATH, "//tr[contains(., 'Relative Strength Index')]//td[2]")
            rsi_text = value_cell.text.strip()
            
            # Wait for data to load if showing placeholder
            if rsi_text in ["—", "", "N/A", "Loading...", "--"]:
                for attempt in range(6):
                    time.sleep(5)
                    value_cell = driver.find_element(By.XPATH, "//tr[contains(., 'Relative Strength Index')]//td[2]")
                    rsi_text = value_cell.text.strip()
                    
                    if rsi_text not in ["—", "", "N/A", "Loading...", "--"]:
                        break
                
                if rsi_text in ["—", "", "N/A", "Loading...", "--"]:
                    return None, f"RSI data not loaded. Current value: '{rsi_text}'"
            
            try:
                rsi_value = float(rsi_text.replace(',', ''))
                return rsi_value, None
            except ValueError:
                return None, f"Cannot convert '{rsi_text}' to number"
                
        except Exception as e:
            return None, f"Error: {e}"
        finally:
            if driver:
                driver.quit()
    
    def fetch_all_rsi(self):
        """Fetch RSI for all symbols"""
        print(f"🚀 Daily RSI Fetch - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Processing {len(self.symbols)} symbols...")
        print("=" * 50)
        
        results = {}
        failed_count = 0
        
        for i, symbol in enumerate(self.symbols, 1):
            clean_symbol = symbol.replace("CSELK-", "")
            print(f"[{i:2d}/{len(self.symbols)}] {clean_symbol:<12}", end=" ")
            
            rsi_value, error = self.fetch_single_rsi(symbol)
            
            if rsi_value is not None:
                results[symbol] = {
                    'rsi': rsi_value,
                    'status': 'success',
                    'timestamp': datetime.now().isoformat()
                }
                
                # Determine status
                if rsi_value < 30:
                    status_text = "OVERSOLD 🔥"
                elif rsi_value > 70:
                    status_text = "OVERBOUGHT ⚠️"
                else:
                    status_text = "NEUTRAL"
                
                print(f"✅ {rsi_value:5.1f} ({status_text})")
            else:
                results[symbol] = {
                    'rsi': None,
                    'status': 'failed',
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                }
                failed_count += 1
                print(f"❌ FAILED - {error}")
            
            # Small delay between requests
            if i < len(self.symbols):
                time.sleep(2)
        
        print("=" * 50)
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
            'total_symbols': len(self.symbols),
            'successful_fetches': len([r for r in self.results.values() if r['status'] == 'success']),
            'failed_fetches': len([r for r in self.results.values() if r['status'] == 'failed']),
            'data': self.results
        }
        
        # Save to daily file
        filename = f"rsi_data_{timestamp.strftime('%Y_%m_%d')}.json"
        with open(filename, 'w') as f:
            json.dump(daily_data, f, indent=2)
        
        # Also save to latest.json for the webpage
        with open('latest_rsi.json', 'w') as f:
            json.dump(daily_data, f, indent=2)
        
        print(f"💾 Data saved to {filename} and latest_rsi.json")
        return filename
    
    def generate_html_page(self):
        """Generate HTML page for GitHub Pages"""
        timestamp = datetime.now()
        
        # Get successful results for display
        successful_results = {k: v for k, v in self.results.items() if v['status'] == 'success'}
        
        # Sort by RSI value
        sorted_results = sorted(successful_results.items(), key=lambda x: x[1]['rsi'])
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily RSI Monitor - Sri Lanka Stocks</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
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
        }}
        .rsi-cell {{
            font-weight: bold;
            font-size: 1.1em;
        }}
        .status-oversold {{
            background: #ffe6e6;
            color: #c0392b;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        .status-overbought {{
            background: #fff3cd;
            color: #856404;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        .status-neutral {{
            background: #e8f5e8;
            color: #155724;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9em;
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
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Daily RSI Monitor</h1>
            <p>Sri Lanka Stock Exchange - Last Updated: {timestamp.strftime('%B %d, %Y at %I:%M %p')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{len([r for r in successful_results.values() if r['rsi'] < 30])}</div>
                <div class="oversold">Oversold Stocks</div>
                <small>(RSI < 30)</small>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len([r for r in successful_results.values() if r['rsi'] > 70])}</div>
                <div class="overbought">Overbought Stocks</div>
                <small>(RSI > 70)</small>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len([r for r in successful_results.values() if 30 <= r['rsi'] <= 70])}</div>
                <div class="neutral">Neutral Stocks</div>
                <small>(RSI 30-70)</small>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(successful_results)}</div>
                <div>Total Monitored</div>
                <small>of {len(self.symbols)} symbols</small>
            </div>
        </div>
        
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Stock Symbol</th>
                        <th>RSI Value</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>"""
        
        for symbol, data in sorted_results:
            clean_symbol = symbol.replace("CSELK-", "")
            rsi = data['rsi']
            
            if rsi < 30:
                status_class = "status-oversold"
                status_text = "🔥 Oversold"
            elif rsi > 70:
                status_class = "status-overbought"
                status_text = "⚠️ Overbought"
            else:
                status_class = "status-neutral"
                status_text = "📊 Neutral"
            
            html += f"""
                    <tr>
                        <td>{clean_symbol}</td>
                        <td class="rsi-cell">{rsi:.1f}</td>
                        <td><span class="{status_class}">{status_text}</span></td>
                    </tr>"""
        
        html += f"""
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Data sourced from TradingView • Updated daily at market close</p>
            <p>Last successful update: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>"""
        
        with open('index.html', 'w') as f:
            f.write(html)
        
        print(f"📄 Generated index.html with {len(successful_results)} stocks")
        return 'index.html'

# Stock symbols from your CSV
STOCK_SYMBOLS = [
    "CSELK-ABAN.N0000", "CSELK-AFSL.N0000", "CSELK-AEL.N0000", "CSELK-ACL.N0000"
]

if __name__ == "__main__":
    print("🤖 Daily RSI Scraper for GitHub Pages")
    print("=" * 50)
    
    # Initialize scraper
    base_url = "https://tradingview.com/symbols/{SYMBOL}/technicals/"
    scraper = DailyRSIScraper(base_url, STOCK_SYMBOLS)
    
    # Fetch all RSI data
    results = scraper.fetch_all_rsi()
    
    if results:
        # Save data files
        json_file = scraper.save_daily_data()
        
        # Generate HTML page
        html_file = scraper.generate_html_page()
        
        print("\n🎉 Daily RSI fetch completed!")
        print(f"📊 Generated files:")
        print(f"   • {json_file} (daily data)")
        print(f"   • latest_rsi.json (for API access)")
        print(f"   • {html_file} (GitHub Pages website)")
        print("\n📤 Ready to upload to GitHub!")
        
    else:
        print("❌ No data retrieved. Check your internet connection and try again.")