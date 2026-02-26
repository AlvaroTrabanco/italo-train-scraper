exports.handler = async (event) => {
  try {
    const pw = (event.queryStringParameters && event.queryStringParameters.pw) || "";

    if (!process.env.GTFS_DL_KEY || pw !== process.env.GTFS_DL_KEY) {
      return { statusCode: 403, body: "Forbidden" };
    }

    // Build the absolute URL to your own deployed ZIP
    const host =
      event.headers["x-forwarded-host"] ||
      event.headers["host"];

    const proto =
      event.headers["x-forwarded-proto"] || "https";

    const fileUrl = `${proto}://${host}/gtfs/italo_latest.zip`;

    const resp = await fetch(fileUrl);
    if (!resp.ok) {
      const txt = await resp.text().catch(() => "");
      return {
        statusCode: 502,
        body: `Upstream error fetching ${fileUrl}: HTTP ${resp.status}\n${txt}`.slice(0, 2000),
      };
    }

    const ab = await resp.arrayBuffer();
    const b64 = Buffer.from(ab).toString("base64");

    return {
      statusCode: 200,
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": 'attachment; filename="italo_latest.zip"',
        "Cache-Control": "no-store",
      },
      body: b64,
      isBase64Encoded: true,
    };
  } catch (e) {
    return {
      statusCode: 502,
      body: `Function crashed: ${e && e.stack ? e.stack : String(e)}`.slice(0, 2000),
    };
  }
};