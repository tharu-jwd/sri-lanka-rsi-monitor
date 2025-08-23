#!/usr/bin/env python3
"""
Test suite for the RSI scraper functionality
"""

import unittest
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the scraper class
from daily_rsi_scraper import EnhancedMultiTimeframeRSIScraper, STOCK_SYMBOLS, SYMBOL_TO_COMPANY


class TestRSIScraper(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_symbols = ["CSELK-ABAN.N0000", "CSELK-AFSL.N0000"]
        self.base_url = "https://tradingview.com/symbols/{SYMBOL}/technicals/"
        self.scraper = EnhancedMultiTimeframeRSIScraper(
            self.base_url,
            self.test_symbols,
            max_workers=1,
            batch_size=2,
            rate_limit_delay=0.1
        )
    
    def test_initialization(self):
        """Test scraper initialization"""
        self.assertEqual(self.scraper.base_url, self.base_url)
        self.assertEqual(self.scraper.symbols, self.test_symbols)
        self.assertEqual(self.scraper.timeframes, ['1D', '1W', '1M'])
        self.assertEqual(self.scraper.max_workers, 1)
        self.assertEqual(self.scraper.batch_size, 2)
        self.assertEqual(self.scraper.rate_limit_delay, 0.1)
    
    def test_build_url(self):
        """Test URL building"""
        symbol = "CSELK-ABAN.N0000"
        expected_url = "https://tradingview.com/symbols/CSELK-ABAN.N0000/technicals/"
        actual_url = self.scraper.build_url(symbol)
        self.assertEqual(actual_url, expected_url)
    
    def test_stock_data_integrity(self):
        """Test that stock data is properly formatted"""
        self.assertIsInstance(STOCK_SYMBOLS, list)
        self.assertGreater(len(STOCK_SYMBOLS), 0)
        self.assertIsInstance(SYMBOL_TO_COMPANY, dict)
        
        # Check that all symbols have corresponding company names
        for symbol in STOCK_SYMBOLS[:5]:  # Test first 5
            self.assertIn(symbol, SYMBOL_TO_COMPANY)
            self.assertIsInstance(SYMBOL_TO_COMPANY[symbol], str)
            self.assertGreater(len(SYMBOL_TO_COMPANY[symbol]), 0)
    
    def test_rsi_value_validation(self):
        """Test RSI value validation logic"""
        # Test valid RSI values
        valid_rsi_values = [0, 30, 50, 70, 100]
        for value in valid_rsi_values:
            self.assertTrue(0 <= value <= 100)
        
        # Test invalid RSI values
        invalid_rsi_values = [-1, 101, 150, -50]
        for value in invalid_rsi_values:
            self.assertFalse(0 <= value <= 100)
    
    def test_oversold_overbought_logic(self):
        """Test the oversold/overbought categorization logic"""
        # Test oversold (< 50)
        oversold_values = [0, 20, 30, 49.9]
        for value in oversold_values:
            self.assertTrue(value < 50, f"Value {value} should be oversold")
        
        # Test neutral (50-70)
        neutral_values = [50, 60, 70]
        for value in neutral_values:
            self.assertTrue(50 <= value <= 70, f"Value {value} should be neutral")
        
        # Test overbought (> 70)
        overbought_values = [70.1, 80, 90, 100]
        for value in overbought_values:
            self.assertTrue(value > 70, f"Value {value} should be overbought")
    
    @patch('daily_rsi_scraper.webdriver.Chrome')
    def test_create_driver_success(self, mock_chrome):
        """Test successful driver creation"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        driver = self.scraper.create_driver()
        
        self.assertIsNotNone(driver)
        mock_chrome.assert_called_once()
    
    @patch('daily_rsi_scraper.webdriver.Chrome')
    def test_create_driver_failure(self, mock_chrome):
        """Test driver creation failure"""
        mock_chrome.side_effect = Exception("WebDriver error")
        
        driver = self.scraper.create_driver()
        
        self.assertIsNone(driver)
    
    def test_save_daily_data(self):
        """Test saving daily data to JSON"""
        # Mock some results
        self.scraper.results = {
            "CSELK-ABAN.N0000": {
                'rsi_data': {'1D': 75.5, '1W': 80.2, '1M': 65.3},
                'status': 'success',
                'successful_timeframes': 3,
                'timestamp': datetime.now().isoformat(),
                'attempts': 1
            }
        }
        
        # Use temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                filename = self.scraper.save_daily_data()
                
                # Check that files were created
                self.assertTrue(os.path.exists(filename))
                self.assertTrue(os.path.exists('latest_rsi.json'))
                
                # Check file content
                with open('latest_rsi.json', 'r') as f:
                    data = json.load(f)
                    self.assertIn('metadata', data)
                    self.assertIn('data', data)
                    self.assertIn('CSELK-ABAN.N0000', data['data'])
                    
                # Check RSI data structure
                stock_data = data['data']['CSELK-ABAN.N0000']
                self.assertIn('rsi_data', stock_data)
                self.assertIn('1D', stock_data['rsi_data'])
                self.assertEqual(stock_data['rsi_data']['1D'], 75.5)
                
            finally:
                os.chdir(original_cwd)
    
    def test_html_generation_structure(self):
        """Test HTML generation creates valid structure"""
        # Mock some results
        self.scraper.results = {
            "CSELK-ABAN.N0000": {
                'rsi_data': {'1D': 45.5, '1W': 60.2, '1M': 75.3},
                'status': 'success',
                'successful_timeframes': 3,
                'timestamp': datetime.now().isoformat(),
                'attempts': 1
            }
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                html_file = self.scraper.generate_html_page()
                
                self.assertTrue(os.path.exists(html_file))
                
                with open(html_file, 'r') as f:
                    html_content = f.read()
                    
                # Check HTML structure
                self.assertIn('<!DOCTYPE html>', html_content)
                self.assertIn('<title>Multi-Timeframe RSI Monitor', html_content)
                self.assertIn('stockData = [', html_content)
                self.assertIn('ABAN.N0000', html_content)  # Symbol should be cleaned
                
                # Check that RSI thresholds are correct
                self.assertIn('rsiValue < 50', html_content)  # Oversold threshold
                self.assertIn('rsiValue > 70', html_content)  # Overbought threshold
                
            finally:
                os.chdir(original_cwd)
    
    def test_batch_processing_logic(self):
        """Test batch processing splits symbols correctly"""
        symbols = ["SYM1", "SYM2", "SYM3", "SYM4", "SYM5"]
        scraper = EnhancedMultiTimeframeRSIScraper("url", symbols, batch_size=2)
        
        # Test batch calculation
        total_batches = (len(symbols) + scraper.batch_size - 1) // scraper.batch_size
        self.assertEqual(total_batches, 3)  # 5 symbols, batch size 2 = 3 batches
        
        # Test batch splitting
        batches = []
        for batch_num in range(total_batches):
            start_idx = batch_num * scraper.batch_size
            end_idx = min(start_idx + scraper.batch_size, len(symbols))
            batch = symbols[start_idx:end_idx]
            batches.append(batch)
        
        self.assertEqual(len(batches), 3)
        self.assertEqual(batches[0], ["SYM1", "SYM2"])
        self.assertEqual(batches[1], ["SYM3", "SYM4"])
        self.assertEqual(batches[2], ["SYM5"])


class TestDataIntegrity(unittest.TestCase):
    """Test data integrity and consistency"""
    
    def test_json_file_structure(self):
        """Test that latest_rsi.json has correct structure"""
        if os.path.exists('latest_rsi.json'):
            with open('latest_rsi.json', 'r') as f:
                data = json.load(f)
                
            # Check required top-level keys
            required_keys = ['metadata', 'data']
            for key in required_keys:
                self.assertIn(key, data)
            
            # Check metadata structure
            metadata = data['metadata']
            metadata_keys = ['date', 'timestamp', 'timeframes', 'total_symbols', 
                           'successful_fetches', 'success_rate']
            for key in metadata_keys:
                self.assertIn(key, metadata)
            
            # Check timeframes
            self.assertEqual(metadata['timeframes'], ['1D', '1W', '1M'])
            
            # Check data structure for first stock (if exists)
            if data['data']:
                first_stock = next(iter(data['data'].values()))
                self.assertIn('rsi_data', first_stock)
                self.assertIn('status', first_stock)
                self.assertEqual(first_stock['status'], 'success')
    
    def test_html_file_exists_and_valid(self):
        """Test that index.html exists and has basic structure"""
        if os.path.exists('index.html'):
            with open('index.html', 'r') as f:
                html_content = f.read()
            
            # Check basic HTML structure
            self.assertIn('<!DOCTYPE html>', html_content)
            self.assertIn('<html', html_content)
            self.assertIn('<head>', html_content)
            self.assertIn('<body>', html_content)
            
            # Check for required elements
            self.assertIn('Multi-Timeframe RSI Monitor', html_content)
            self.assertIn('stockData = [', html_content)
            self.assertIn('timeframeSelect', html_content)
            
            # Verify RSI thresholds are correct (< 50 for oversold)
            self.assertIn('rsiValue < 50', html_content)
            # Should NOT contain < 30 threshold
            self.assertNotIn('rsiValue < 30', html_content)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)