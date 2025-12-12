// netlify/functions/race-data.js
// スクレイピングしたCSVデータをJSON APIとして提供

const fs = require('fs').promises;
const path = require('path');

/**
 * CSVをパースしてJSONに変換
 */
function parseCSV(csvText) {
  const lines = csvText.trim().split('\n');
  if (lines.length < 2) return [];

  const headers = lines[0].split(',').map(h => h.trim());
  const data = [];

  for (let i = 1; i < lines.length; i++) {
    const values = lines[i].split(',');
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index] ? values[index].trim() : '';
    });
    data.push(row);
  }

  return data;
}

exports.handler = async (event, context) => {
  try {
    // クエリパラメータから年月を取得
    const params = event.queryStringParameters || {};
    const year = params.year || '2019';
    const month = params.month || '01';
    const type = params.type || 'race'; // 'race' or 'horse'

    // CSVファイルのパスを構築
    const csvFileName = `${type}-${year}-${month}.csv`;
    const csvPath = path.join(process.cwd(), 'scraper', 'data', 'csv', csvFileName);

    // ファイルが存在するか確認
    try {
      await fs.access(csvPath);
    } catch (error) {
      return {
        statusCode: 404,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
        body: JSON.stringify({
          error: 'Data not found',
          message: `CSV file for ${year}-${month} (${type}) does not exist`,
          path: csvFileName
        }),
      };
    }

    // CSVファイルを読み込み
    const csvContent = await fs.readFile(csvPath, 'utf-8');
    const jsonData = parseCSV(csvContent);

    return {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Cache-Control': 'public, max-age=3600', // 1時間キャッシュ
      },
      body: JSON.stringify({
        year,
        month,
        type,
        count: jsonData.length,
        data: jsonData,
      }),
    };

  } catch (error) {
    console.error('Error reading CSV:', error);
    return {
      statusCode: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
      body: JSON.stringify({
        error: 'Internal server error',
        message: error.message,
      }),
    };
  }
};
