 Centralized Market Data API - Implementation Plan                                                                                    
                                                                                                                                      
 Overview                                                                                                                             
                                                                                                                                      
 Create a brand new standalone project at /Users/ravivedula/Library/CloudStorage/Dropbox/1-projects/market-data-api for:              
 1. Centralized credential storage at ~/.config/market-data/                                                                          
 2. Automatic Barchart cookie refresh every 4 hours                                                                                   
 3. Simple unified API: get_prices(ticker, start, end, frequency, provider) → DataFrame with adjusted + unadjusted OHLCV              
                                                                                                                                      
 Note: No modifications to existing ffn directory - this is a fresh implementation.                                                   
                                                                                                                                      
 ---                                                                                                                                  
 Architecture                                                                                                                         
                                                                                                                                      
 /Users/ravivedula/Library/CloudStorage/Dropbox/1-projects/market-data-api/                                                           
 ├── pyproject.toml                                                                                                                   
 ├── README.md                                                                                                                        
 ├── market_data/                                                                                                                     
 │   ├── __init__.py           # Exports: get_prices, Frequency, Provider                                                             
 │   ├── api.py                # Main get_prices() function                                                                           
 │   ├── credentials.py        # Load from ~/.config/market-data/                                                                     
 │   ├── providers/                                                                                                                   
 │   │   ├── __init__.py                                                                                                              
 │   │   ├── base.py           # Abstract provider interface                                                                          
 │   │   ├── barchart.py       # Barchart: 2 queries (dividends=true/false)                                                           
 │   │   └── tiingo.py         # Tiingo provider                                                                                      
 │   └── refresh/                                                                                                                     
 │       ├── __init__.py                                                                                                              
 │       └── capture_cookies.py  # Playwright cookie capture (standalone)                                                             
 ├── scripts/                                                                                                                         
 │   └── refresh-barchart-cookies  # Shell script for launchd                                                                         
 └── launchd/                                                                                                                         
     └── com.market-data.barchart-refresh.plist                                                                                       
                                                                                                                                      
 ~/.config/market-data/                                                                                                               
 ├── credentials.json          # API keys, Barchart username                                                                          
 ├── barchart_cookies.json     # Auto-refreshed every 4 hours                                                                         
 └── logs/                     # Refresh logs                                                                                         
                                                                                                                                      
 ---                                                                                                                                  
 API Design                                                                                                                           
                                                                                                                                      
 from market_data import get_prices, Frequency, Provider                                                                              
                                                                                                                                      
 # Simple usage - returns DataFrame with all columns                                                                                  
 df = get_prices("AAPL", "2024-01-01", "2024-12-31").df                                                                               
                                                                                                                                      
 # Full API                                                                                                                           
 data = get_prices(                                                                                                                   
     ticker="AAPL",                                                                                                                   
     start_date="2024-01-01",                                                                                                         
     end_date="2024-12-31",                                                                                                           
     frequency=Frequency.DAILY,      # DAILY | WEEKLY | MONTHLY                                                                       
     provider=Provider.AUTO          # AUTO | TIINGO | BARCHART                                                                       
 )                                                                                                                                    
                                                                                                                                      
 # Returns PriceData with:                                                                                                            
 # - data.df: DataFrame with columns:                                                                                                 
 #   Date (index), Open, High, Low, Close, Volume,                                                                                    
 #   Adj_Open, Adj_High, Adj_Low, Adj_Close, Adj_Volume                                                                               
 # - data.provider: str ("tiingo" or "barchart")                                                                                      
 # - data.ticker: str                                                                                                                 
                                                                                                                                      
 ---                                                                                                                                  
 Barchart Implementation                                                                                                              
                                                                                                                                      
 Two separate API calls for each ticker:                                                                                              
                                                                                                                                      
 1. Unadjusted prices: dividends=false                                                                                                
   - Returns: Open, High, Low, Close, Volume                                                                                          
 2. Adjusted prices: dividends=true                                                                                                   
   - Returns: Adj_Open, Adj_High, Adj_Low, Adj_Close, Adj_Volume                                                                      
                                                                                                                                      
 Merge both into single DataFrame by date.                                                                                            
                                                                                                                                      
 # Pseudocode                                                                                                                         
 unadj_df = fetch_barchart(ticker, dividends=False)  # OHLCV                                                                          
 adj_df = fetch_barchart(ticker, dividends=True)     # Adj OHLCV                                                                      
                                                                                                                                      
 # Rename adjusted columns                                                                                                            
 adj_df.columns = ['Adj_Open', 'Adj_High', 'Adj_Low', 'Adj_Close', 'Adj_Volume']                                                      
                                                                                                                                      
 # Merge on date                                                                                                                      
 result = unadj_df.join(adj_df)                                                                                                       
                                                                                                                                      
 ---                                                                                                                                  
 Credential Storage                                                                                                                   
                                                                                                                                      
 ~/.config/market-data/credentials.json:                                                                                              
 {                                                                                                                                    
   "tiingo_api_key": "your-tiingo-key",                                                                                               
   "barchart_username": "email@example.com",                                                                                          
   "barchart_password_env": "BARCHART_PASSWORD"                                                                                       
 }                                                                                                                                    
                                                                                                                                      
 ~/.config/market-data/barchart_cookies.json:                                                                                         
 {                                                                                                                                    
   "cookie_string": "...",                                                                                                            
   "xsrf_token": "...",                                                                                                               
   "user_agent": "...",                                                                                                               
   "captured_at": "2026-01-18T16:20:05Z"                                                                                              
 }                                                                                                                                    
                                                                                                                                      
 Password stays in ~/.zshrc as export BARCHART_PASSWORD="...".                                                                        
                                                                                                                                      
 ---                                                                                                                                  
 Implementation Steps                                                                                                                 
                                                                                                                                      
 Phase 1: Project Setup                                                                                                               
                                                                                                                                      
 1. Create project directory structure at /Users/ravivedula/Library/CloudStorage/Dropbox/1-projects/market-data-api/                  
 2. Create pyproject.toml with dependencies (requests, pandas, playwright, python-dotenv)                                             
 3. Create ~/.config/market-data/ directory and credential files                                                                      
                                                                                                                                      
 Phase 2: Credential Management                                                                                                       
                                                                                                                                      
 1. Implement credentials.py - load API keys and cookies from central location                                                        
 2. Implement capture_cookies.py - Playwright-based Barchart cookie capture                                                           
 3. Write cookies to ~/.config/market-data/barchart_cookies.json                                                                      
                                                                                                                                      
 Phase 3: Providers                                                                                                                   
                                                                                                                                      
 1. Implement barchart.py:                                                                                                            
   - Cookie-based authentication                                                                                                      
   - Two queries: dividends=true and dividends=false                                                                                  
   - Merge into single DataFrame with Adj_* columns                                                                                   
   - Rate limiting (20s between requests)                                                                                             
 2. Implement tiingo.py:                                                                                                              
   - API key authentication                                                                                                           
   - Returns both adjusted and unadjusted in one call                                                                                 
                                                                                                                                      
 Phase 4: Unified API                                                                                                                 
                                                                                                                                      
 1. Implement api.py with get_prices() function                                                                                       
 2. Provider auto-selection (Tiingo preferred, Barchart fallback)                                                                     
 3. Consistent DataFrame output format                                                                                                
                                                                                                                                      
 Phase 5: Cookie Refresh Automation                                                                                                   
                                                                                                                                      
 1. Create launchd plist for 4-hour refresh schedule                                                                                  
 2. Create shell wrapper script                                                                                                       
 3. Install and load launchd service                                                                                                  
                                                                                                                                      
 Phase 6: Installation & Testing                                                                                                      
                                                                                                                                      
 1. Install package: pip install -e /Users/ravivedula/Library/CloudStorage/Dropbox/1-projects/market-data-api                         
 2. Test from multiple directories                                                                                                    
                                                                                                                                      
 ---                                                                                                                                  
 Files to Create                                                                                                                      
 ┌────────────────────────────────────────────────────────────────┬────────────────────────────────────┐                              
 │                              File                              │              Purpose               │                              
 ├────────────────────────────────────────────────────────────────┼────────────────────────────────────┤                              
 │ market-data-api/pyproject.toml                                 │ Package configuration              │                              
 ├────────────────────────────────────────────────────────────────┼────────────────────────────────────┤                              
 │ market-data-api/market_data/__init__.py                        │ Package exports                    │                              
 ├────────────────────────────────────────────────────────────────┼────────────────────────────────────┤                              
 │ market-data-api/market_data/api.py                             │ Main get_prices() function         │                              
 ├────────────────────────────────────────────────────────────────┼────────────────────────────────────┤                              
 │ market-data-api/market_data/credentials.py                     │ Central credential loader          │                              
 ├────────────────────────────────────────────────────────────────┼────────────────────────────────────┤                              
 │ market-data-api/market_data/providers/base.py                  │ Abstract provider interface        │                              
 ├────────────────────────────────────────────────────────────────┼────────────────────────────────────┤                              
 │ market-data-api/market_data/providers/barchart.py              │ Barchart (2 queries for adj/unadj) │                              
 ├────────────────────────────────────────────────────────────────┼────────────────────────────────────┤                              
 │ market-data-api/market_data/providers/tiingo.py                │ Tiingo provider                    │                              
 ├────────────────────────────────────────────────────────────────┼────────────────────────────────────┤                              
 │ market-data-api/market_data/refresh/capture_cookies.py         │ Cookie capture script              │                              
 ├────────────────────────────────────────────────────────────────┼────────────────────────────────────┤                              
 │ market-data-api/scripts/refresh-barchart-cookies               │ Shell wrapper for launchd          │                              
 ├────────────────────────────────────────────────────────────────┼────────────────────────────────────┤                              
 │ market-data-api/launchd/com.market-data.barchart-refresh.plist │ 4-hour schedule                    │                              
 ├────────────────────────────────────────────────────────────────┼────────────────────────────────────┤                              
 │ ~/.config/market-data/credentials.json                         │ API keys                           │                              
 ├────────────────────────────────────────────────────────────────┼────────────────────────────────────┤                              
 │ ~/.config/market-data/barchart_cookies.json                    │ Session cookies                    │                              
 └────────────────────────────────────────────────────────────────┴────────────────────────────────────┘                              
 ---                                                                                                                                  
 Verification                                                                                                                         
                                                                                                                                      
 1. Test API from Python:                                                                                                             
 python -c "from market_data import get_prices; print(get_prices('SPY', '2024-01-01', '2024-01-10').df)"                              
 1. Should return DataFrame with: Open, High, Low, Close, Volume, Adj_Open, Adj_High, Adj_Low, Adj_Close, Adj_Volume                  
 2. Check cookies are fresh:                                                                                                          
 cat ~/.config/market-data/barchart_cookies.json | python -m json.tool                                                                
 3. Verify launchd service:                                                                                                           
 launchctl list | grep market-data                                                                                                    
 4. Test from different project directory - should work without local .env                                                            
                                                                                                                                      
 ---                                                                                                                                  
 Dependencies                                                                                                                         
                                                                                                                                      
 - pandas - DataFrame handling                                                                                                        
 - requests - HTTP requests                                                                                                           
 - playwright - Browser automation for cookie capture                                                                                 
 - playwright-stealth - Anti-detection for Playwright            