// netlify/functions/proxy.js

// node-fetchを動的にimportする
const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));
const { TextDecoder } = require('util');

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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
      },
    });

    if (!response.ok) {
      return {
        statusCode: response.status,
        body: `Failed to fetch from target URL: ${response.statusText}`,
      };
    }

    // EUC-JPの文字コードに対応するため、ArrayBufferとしてレスポンスを取得
    const buffer = await response.arrayBuffer();
    // TextDecoderを使用してEUC-JPからUTF-8に変換
    const decoder = new TextDecoder('euc-jp');
    const decodedHtml = decoder.decode(buffer);

    return {
      statusCode: 200,
      body: decodedHtml,
      headers: {
        'Content-Type': 'text/html; charset=utf-8', // クライアントにはUTF-8として返す
        'Access-Control-Allow-Origin': '*', 
      },
    };
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: `Failed to fetch from proxy: ${error.message}` }),
    };
  }
};