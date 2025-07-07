const express = require('express');
const RSS = require('rss');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Cache to store fetched data temporarily
let cache = {
  data: null,
  timestamp: null,
  ttl: 5 * 60 * 1000 // 5 minutes cache
};

// Helper function to fetch YTS API data
async function fetchYTSData(params = {}) {
  const {
    quality = 'all',
    genre = 'all',
    rating = 0,
    sort_by = 'date_added',
    order_by = 'desc',
    page = 1,
    limit = 50
  } = params;

  const apiUrl = `https://yts.mx/api/v2/list_movies.json?quality=${quality}&genre=${genre}&minimum_rating=${rating}&sort_by=${sort_by}&order_by=${order_by}&page=${page}&limit=${limit}`;
  
  try {
    const response = await fetch(apiUrl);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching YTS data:', error);
    throw error;
  }
}

// Helper function to fetch all pages
async function fetchAllMovies(params = {}) {
  const allMovies = [];
  let page = 1;
  let hasMore = true;
  
  // Limit to first few pages to avoid timeout in GitHub Actions
  const maxPages = 5; // This will get ~250 movies instead of trying to fetch ALL
  
  while (hasMore && page <= maxPages) {
    try {
      console.log(`Fetching page ${page} for ${params.quality || 'all'} ${params.genre || 'all'}...`);
      const data = await fetchYTSData({ ...params, page, limit: 50 });
      
      console.log(`Page ${page} response:`, {
        status: data.status,
        hasData: !!data.data,
        hasMovies: !!data.data?.movies,
        movieCount: data.data?.movies?.length || 0
      });
      
      if (data.status === 'ok' && data.data && data.data.movies && Array.isArray(data.data.movies)) {
        allMovies.push(...data.data.movies);
        page++;
        // Continue if we got a full page of results
        hasMore = data.data.movies.length === 50;
        
        // Add delay to be respectful to the API
        if (hasMore && page <= maxPages) {
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      } else {
        console.log('No more movies found or invalid response');
        hasMore = false;
      }
    } catch (error) {
      console.error(`Error fetching page ${page}:`, error);
      hasMore = false;
    }
  }
  
  console.log(`Total movies collected: ${allMovies.length}`);
  return allMovies;
}

// Convert movie data to RSS
function createRSSFeed(movies, params = {}) {
  const { quality = 'all', genre = 'all' } = params;
  
  const feed = new RSS({
    title: `YTS Movies RSS Feed - ${quality} - ${genre}`,
    description: `Latest movies from YTS in ${quality} quality for ${genre} genre`,
    feed_url: `${process.env.BASE_URL || 'http://localhost:3000'}/rss`,
    site_url: 'https://yts.mx',
    image_url: 'https://yts.mx/assets/images/website/logo-YTS.svg',
    managingEditor: 'YTS',
    webMaster: 'YTS',
    copyright: '2025 YTS',
    language: 'en',
    categories: ['Movies', 'Entertainment'],
    pubDate: new Date(),
    ttl: '60'
  });

  movies.forEach(movie => {
    const torrents = movie.torrents || [];
    
    // Filter torrents by requested quality if specified
    const filteredTorrents = quality === 'all' 
      ? torrents 
      : torrents.filter(t => t.quality === quality);
    
    // Use the best quality torrent available
    const bestTorrent = filteredTorrents.length > 0 
      ? filteredTorrents[0] 
      : torrents[0];
    
    if (!bestTorrent) return; // Skip if no torrent available
    
    // Generate magnet link from hash
    const magnetLink = `magnet:?xt=urn:btih:${bestTorrent.hash}&dn=${encodeURIComponent(movie.title + ' (' + movie.year + ') [' + bestTorrent.quality + '] [YTS.MX]')}&tr=udp://open.demonii.com:1337/announce&tr=udp://tracker.openbittorrent.com:80&tr=udp://tracker.coppersurfer.tk:6969&tr=udp://glotorrents.pw:6969/announce&tr=udp://tracker.opentrackr.org:1337/announce&tr=udp://torrent.gresille.org:80/announce&tr=udp://p4p.arenabg.com:1337&tr=udp://tracker.leechers-paradise.org:6969`;
    
    const torrentLinks = filteredTorrents.map(t => 
      `${t.quality} - ${t.size} - Seeds: ${t.seeds} - Peers: ${t.peers}`
    ).join('\n');
    
    const description = `
      <p><strong>Year:</strong> ${movie.year}</p>
      <p><strong>Rating:</strong> ${movie.rating}/10 (${movie.runtime} min)</p>
      <p><strong>Genres:</strong> ${movie.genres ? movie.genres.join(', ') : 'N/A'}</p>
      <p><strong>Quality:</strong> ${bestTorrent.quality}</p>
      <p><strong>Size:</strong> ${bestTorrent.size}</p>
      <p><strong>Seeds/Peers:</strong> ${bestTorrent.seeds}/${bestTorrent.peers}</p>
      <p><strong>Summary:</strong> ${movie.summary || 'No summary available'}</p>
      <p><strong>Available Torrents:</strong></p>
      <pre>${torrentLinks}</pre>
      <p><a href="${movie.url}">View on YTS</a></p>
    `;

    feed.item({
      title: `${movie.title} (${movie.year}) [${bestTorrent.quality}]`,
      description: description,
      url: magnetLink,  // Use magnet link instead of YTS page URL
      guid: movie.id.toString() + '-' + bestTorrent.hash,
      date: new Date(movie.date_uploaded),
      enclosure: {
        url: magnetLink,
        type: 'application/x-bittorrent'
      }
    });
  });

  return feed.xml();
}

// Generate static RSS files
async function generateStaticRSS() {
  const feedConfigs = [
    { quality: 'all', genre: 'all', filename: 'all.xml' },
    { quality: '2160p', genre: 'all', filename: '2160p.xml' },
    { quality: '1080p', genre: 'all', filename: '1080p.xml' },
    { quality: '720p', genre: 'all', filename: '720p.xml' },
    { quality: '1080p', genre: 'action', filename: '1080p-action.xml' },
    { quality: '1080p', genre: 'horror', filename: '1080p-horror.xml' }
  ];

  const outputDir = path.join(__dirname, 'feeds');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir);
  }

  for (const config of feedConfigs) {
    try {
      console.log(`Generating RSS for ${config.quality} ${config.genre}...`);
      const movies = await fetchAllMovies(config);
      const rssXml = createRSSFeed(movies, config);
      
      const filePath = path.join(outputDir, config.filename);
      fs.writeFileSync(filePath, rssXml);
      console.log(`✅ Generated ${config.filename} with ${movies.length} movies`);
      
      // Wait between API calls
      await new Promise(resolve => setTimeout(resolve, 1000));
    } catch (error) {
      console.error(`❌ Error generating ${config.filename}:`, error);
    }
  }
}

// Routes
app.get('/', (req, res) => {
  res.send(`
    <h1>YTS RSS Converter</h1>
    <p>Convert YTS API to RSS format</p>
    <h2>Available endpoints:</h2>
    <ul>
      <li><a href="/rss">/rss</a> - All movies RSS feed</li>
      <li><a href="/rss?quality=2160p">/rss?quality=2160p</a> - 4K movies only</li>
      <li><a href="/rss?quality=1080p">/rss?quality=1080p</a> - 1080p movies only</li>
      <li><a href="/rss?genre=action">/rss?genre=action</a> - Action movies only</li>
      <li><a href="/rss?quality=1080p&genre=action">/rss?quality=1080p&genre=action</a> - 1080p Action movies</li>
    </ul>
    <h2>Available parameters:</h2>
    <ul>
      <li>quality: all, 2160p, 1080p, 720p, 480p</li>
      <li>genre: all, action, adventure, animation, biography, comedy, crime, documentary, drama, family, fantasy, film-noir, history, horror, music, musical, mystery, romance, sci-fi, sport, thriller, war, western</li>
      <li>rating: minimum rating (0-9)</li>
      <li>sort_by: title, year, rating, peers, seeds, download_count, like_count, date_added</li>
      <li>order_by: desc, asc</li>
    </ul>
  `);
});

app.get('/rss', async (req, res) => {
  try {
    const params = {
      quality: req.query.quality || 'all',
      genre: req.query.genre || 'all',
      rating: req.query.rating || 0,
      sort_by: req.query.sort_by || 'date_added',
      order_by: req.query.order_by || 'desc'
    };

    console.log('Fetching movies with params:', params);
    const movies = await fetchAllMovies(params);
    console.log(`Found ${movies.length} movies`);

    const rssXml = createRSSFeed(movies, params);
    
    res.set('Content-Type', 'application/rss+xml');
    res.send(rssXml);
  } catch (error) {
    console.error('Error generating RSS:', error);
    res.status(500).send('Error generating RSS feed');
  }
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    cache: {
      hasData: !!cache.data,
      movieCount: cache.data ? cache.data.length : 0,
      lastUpdated: cache.timestamp ? new Date(cache.timestamp).toISOString() : null
    }
  });
});

// Run if called directly (don't start server)
if (require.main === module) {
  generateStaticRSS().then(() => {
    console.log('✅ All RSS feeds generated successfully!');
    process.exit(0);
  }).catch(error => {
    console.error('❌ Error generating RSS feeds:', error);
    process.exit(1);
  });
} else {
  // Only start server if imported as module
  app.listen(PORT, () => {
    console.log(`YTS RSS Converter running on port ${PORT}`);
    console.log(`Visit http://localhost:${PORT} for usage instructions`);
  });
}