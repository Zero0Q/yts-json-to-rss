# YTS RSS Converter

Convert YTS movie API to RSS feed with unlimited results (not limited to 100 items like the original RSS feed).

## Features

- 📡 Fetches ALL movies from YTS API (auto-pagination)
- 📰 Converts to proper RSS format
- 🎬 Filter by quality, genre, rating
- ⚡ Built-in caching (5 minutes)
- 🚀 Easy deployment to cloud platforms
- ⏰ **Automatic hourly updates via GitHub Actions**
- 📁 **Static RSS files generated automatically**

## How Data Pulling Works

Your RSS converter pulls new items **directly through JSON API calls** to YTS:

1. **Real-time fetching**: Makes HTTP requests to `https://yts.mx/api/v2/list_movies.json`
2. **Auto-pagination**: Loops through ALL pages (unlimited items vs 100 limit of original RSS)
3. **Smart caching**: Results cached for 5 minutes to respect API limits
4. **Automatic updates**: GitHub Actions runs every hour to generate fresh static RSS files

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
- ✅ Commit changes back to repository
- ✅ No server maintenance required!

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

## Environment Variables

- `PORT` - Server port (default: 3000)
- `BASE_URL` - Your deployed URL for RSS feed URLs

## License

MIT