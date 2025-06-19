const express = require('express');
const cors = require('cors');
const { execSync } = require('child_process');
const fetch = require('node-fetch');

const app = express();
const PORT = 4000;
//const BACKEND_URL = 'https://walis-api-106234732913.us-central1.run.app'; // Update if needed
const BACKEND_URL = 'https://walis-api-p2bueaisoa-uc.a.run.app';


app.use(cors({
  origin: 'http://localhost:3000', // React dev server
  credentials: true,
}));
app.use(express.json());

app.use('/api', async (req, res) => {
  try {
    // Get identity token using gcloud
    const token = execSync('gcloud auth print-identity-token').toString().trim();
    // Build the proxied URL
    const url = BACKEND_URL + req.originalUrl.replace(/^\/api/, '');
    // Exclude 'host' from headers
    const { host, ...headers } = req.headers;
    // Forward the request
    const response = await fetch(url, {
      method: req.method,
      headers: {
        ...headers,
        'Authorization': `Bearer ${token}`,
      },
      body: ['GET', 'HEAD'].includes(req.method) ? undefined : JSON.stringify(req.body),
    });
    // Forward response
    const contentType = response.headers.get('content-type');
    res.status(response.status);
    if (contentType && contentType.includes('application/json')) {
      res.json(await response.json());
    } else {
      res.send(await response.text());
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.listen(PORT, () => {
  console.log(`Proxy server running on http://localhost:${PORT}`);
}); 