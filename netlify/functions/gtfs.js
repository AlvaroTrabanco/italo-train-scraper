import fetch from "node-fetch";

export async function handler(event) {
  const pw = event.queryStringParameters.pw || "";

  if (!process.env.GTFS_DL_KEY || pw !== process.env.GTFS_DL_KEY) {
    return { statusCode: 403, body: "Forbidden" };
  }

  const url = `${process.env.URL || ""}/gtfs/italo_latest.zip`;
  const resp = await fetch(url);
  if (!resp.ok) return { statusCode: 502, body: `Upstream error: ${resp.status}` };

  const buf = await resp.arrayBuffer();

  return {
    statusCode: 200,
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition": 'attachment; filename="italo_latest.zip"',
    },
    body: Buffer.from(buf).toString("base64"),
    isBase64Encoded: true,
  };
}