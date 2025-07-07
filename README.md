# YTS RSS Converter

Convert YTS movie API to RSS feed with unlimited results (not limited to 100 items like the original RSS feed).

## Features

- 📡 Fetches ALL movies from YTS API (auto-pagination)
- 📰 Converts to proper RSS format
- 🎬 Filter by quality, genre, rating
- ⚡ Built-in caching (5 minutes)
- 🚀 Easy deployment to cloud platforms

## Usage

### Local Development
```bash
npm install
npm start
```

Visit `http://localhost:3000` for usage instructions.

### RSS Endpoints

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