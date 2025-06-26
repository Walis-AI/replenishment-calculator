const express = require('express');
const cors = require('cors');
const { execSync } = require('child_process');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = 4000;
//const BACKEND_URL = 'https://walis-api-106234732913.us-central1.run.app'; // Update if needed
const BACKEND_URL = 'http://localhost:8000';


app.use(cors({
  origin: 'http://localhost:3000', // React dev server
  credentials: true,
}));
app.use(express.json());

// Proxy all /api requests to the backend, adding Google identity token
app.use('/api', createProxyMiddleware({
  target: BACKEND_URL,
  changeOrigin: true,
  pathRewrite: { '^/api': '' },
  onProxyReq: (proxyReq, req, res) => {
    try {
      const token = execSync('gcloud auth print-identity-token').toString().trim();
      proxyReq.setHeader('Authorization', `Bearer ${token}`);
    } catch (err) {
      // If token fetch fails, respond with error
      res.statusCode = 500;
      res.end(JSON.stringify({ error: 'Failed to fetch Google identity token', detail: err.message }));
    }
  },
  onError: (err, req, res) => {
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: err.message }));
  },
}));

app.listen(PORT, () => {
  console.log(`Proxy server running on http://localhost:${PORT}`);
}); 