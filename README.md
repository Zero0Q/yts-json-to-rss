# YTS RSS Converter with Real-Debrid Integration

Convert YTS movie API to RSS feed with unlimited results and automatically send new torrents to Real-Debrid.

## Features

- 📡 Fetches ALL movies from YTS API (auto-pagination)
- 📰 Converts to proper RSS format
- 🎬 Filter by quality, genre, rating
- ⚡ Built-in caching (5 minutes)
- 🚀 Easy deployment to cloud platforms
- ⏰ **Automatic hourly updates via GitHub Actions**
- 📁 **Static RSS files generated automatically**
- 🔄 **Real-Debrid integration - auto-download new torrents**

## How Data Pulling Works

Your RSS converter pulls new items **directly through JSON API calls** to YTS:

1. **Real-time fetching**: Makes HTTP requests to `https://yts.mx/api/v2/list_movies.json`
2. **Auto-pagination**: Loops through ALL pages (unlimited items vs 100 limit of original RSS)
3. **Smart caching**: Results cached for 5 minutes to respect API limits
4. **Automatic updates**: GitHub Actions runs every hour to generate fresh static RSS files
5. **Real-Debrid sync**: Automatically sends new torrents to your Real-Debrid account

## Real-Debrid Integration

The project includes a Python script that automatically processes your RSS feeds and sends new torrents to Real-Debrid:

### Features
- ✅ Converts YTS torrent URLs to magnet links
- ✅ Automatically adds new torrents to Real-Debrid
- ✅ Selects all files for download
- ✅ Tracks what's already been added (no duplicates)
- ✅ Runs automatically with RSS updates

### Setup Real-Debrid Integration

#### For GitHub Actions (Automatic):
1. **Get your Real-Debrid API token:**
   - Go to https://real-debrid.com/apitoken
   - Copy your token

2. **Add token to GitHub Secrets:**
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add a new secret: `RD_TOKEN` with your Real-Debrid token

3. **The script will automatically:**
   - Add your RSS feeds to the monitoring list
   - Check for new movies every hour
   - Send new torrents to Real-Debrid
   - Select all files for download

#### For Local Development:
1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup environment file:**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your Real-Debrid token
   # RD_TOKEN=your_real_debrid_token_here
   ```

3. **Run the script:**
   ```bash
   # Auto-add your RSS feeds
   python3 rd_rss.py --auto-add-feeds
   
   # Process feeds (add new torrents to Real-Debrid)
   python3 rd_rss.py
   ```

### Manual Real-Debrid Usage

You can also run the Real-Debrid script manually with command line options:

```bash
# Set your token (stored in config file)
python3 rd_rss.py --token YOUR_RD_TOKEN

# Auto-add your RSS feeds
python3 rd_rss.py --auto-add-feeds

# Process feeds (add new torrents to Real-Debrid)
python3 rd_rss.py

# List configured RSS feeds
python3 rd_rss.py --list

# Add a custom RSS feed
python3 rd_rss.py --add "https://example.com/feed.xml"

# Remove an RSS feed (use --list to get index)
python3 rd_rss.py --remove 1
```

## Usage

### Option 1: Live API (Dynamic)
Run the server and get real-time data:
```bash
npm install
npm start
```

Visit `http://localhost:3000` for usage instructions.

### Option 2: Static RSS Files (Updated Hourly)
Access pre-generated RSS files that update every hour automatically:

- `https://raw.githubusercontent.com/Zero0Q/yts-json-to-rss/main/feeds/all.xml` - All movies
- `https://raw.githubusercontent.com/Zero0Q/yts-json-to-rss/main/feeds/2160p.xml` - 4K movies only
- `https://raw.githubusercontent.com/Zero0Q/yts-json-to-rss/main/feeds/1080p.xml` - 1080p movies only
- `https://raw.githubusercontent.com/Zero0Q/yts-json-to-rss/main/feeds/720p.xml` - 720p movies only
- `https://raw.githubusercontent.com/Zero0Q/yts-json-to-rss/main/feeds/1080p-action.xml` - 1080p action movies
- `https://raw.githubusercontent.com/Zero0Q/yts-json-to-rss/main/feeds/1080p-horror.xml` - 1080p horror movies

### Manual RSS Generation
Generate static RSS files locally:
```bash
node index.js
```

### RSS Endpoints (Live Server)

- `/rss` - All movies
- `/rss?quality=2160p` - 4K movies only
- `/rss?quality=1080p&genre=action` - 1080p action movies
- `/rss?rating=7&sort_by=rating` - Movies rated 7+ sorted by rating

### Available Parameters

- **quality**: all, 2160p, 1080p, 720p, 480p
- **genre**: all, action, adventure, animation, comedy, horror, sci-fi, etc.
- **rating**: minimum rating (0-9)
- **sort_by**: title, year, rating, seeds, date_added, etc.
- **order_by**: desc, asc

## Automatic Updates

The repository includes GitHub Actions that:
- ✅ Run every hour automatically
- ✅ Fetch latest movies from YTS API
- ✅ Generate fresh RSS files
- ✅ Auto-add RSS feeds to Real-Debrid monitoring
- ✅ Send new torrents to Real-Debrid automatically
- ✅ Commit changes back to repository
- ✅ No server maintenance required!

## Environment Variables

- `PORT` - Server port (default: 3000)
- `BASE_URL` - Your deployed URL for RSS feed URLs
- `RD_TOKEN` - Real-Debrid API token (for GitHub Actions)

## Deployment

### Deploy to Railway
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template)

### Deploy to Render
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### Deploy to Vercel
```bash
npm i -g vercel
vercel
```

### Deploy to Heroku
```bash
git add .
git commit -m "Initial commit"
heroku create your-app-name
git push heroku main
```

## License

MIT