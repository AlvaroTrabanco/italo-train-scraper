exports.handler = async function(event) {
  const key = event.queryStringParameters.key;

  if (!key || key !== process.env.GTFS_DL_KEY) {
    return {
      statusCode: 403,
      body: "Forbidden"
    };
  }

  // Fetch the private artifact or build URL
  const response = await fetch(process.env.GTFS_SOURCE_URL);

  if (!response.ok) {
    return {
      statusCode: 500,
      body: "Failed to fetch GTFS"
    };
  }

  const buffer = await response.arrayBuffer();

  return {
    statusCode: 200,
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition": "attachment; filename=italo_latest.zip"
    },
    body: Buffer.from(buffer).toString("base64"),
    isBase64Encoded: true
  };
};