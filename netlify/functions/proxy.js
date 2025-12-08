// netlify/functions/proxy.js

// node-fetchを動的にimportする
const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));

exports.handler = async (event, context) => {
  // クエリパラメータからターゲットURLを取得
  const targetUrl = event.queryStringParameters.url;

  if (!targetUrl) {
    return {
      statusCode: 400,
      body: JSON.stringify({ error: 'url query parameter is required' }),
    };
  }

  try {
    const response = await fetch(targetUrl, {
      headers: {
        // netkeiba.comからのアクセスを模倣するためのヘッダー
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
      },
    });

    if (!response.ok) {
      return {
        statusCode: response.status,
        body: `Failed to fetch from target URL: ${response.statusText}`,
      };
    }

    const data = await response.text();

    return {
      statusCode: 200,
      body: data,
      headers: {
        'Content-Type': 'text/html; charset=UTF-8',
        'Access-Control-Allow-Origin': '*', // すべてのオリジンからのアクセスを許可
      },
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: `Failed to fetch from proxy: ${error.message}` }),
    };
  }
};
