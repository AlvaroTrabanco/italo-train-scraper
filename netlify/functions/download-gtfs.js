exports.handler = async function (event) {
  const providedKey = event.queryStringParameters?.k;
  const expectedKey = process.env.GTFS_DL_KEY;

  if (!expectedKey) {
    return { statusCode: 500, body: "Server misconfiguration: GTFS_DL_KEY not set" };
  }
  if (!providedKey || providedKey !== expectedKey) {
    return { statusCode: 403, body: "Forbidden" };
  }

  const githubToken = process.env.GITHUB_PAT;
  if (!githubToken) {
    return { statusCode: 500, body: "Server misconfiguration: GITHUB_PAT not set" };
  }

  const repoOwner = "AlvaroTrabanco";
  const repoName = "italo-train-scraper";

  try {
    // 1) List artifacts
    const artifactsRes = await fetch(
      `https://api.github.com/repos/${repoOwner}/${repoName}/actions/artifacts?per_page=100`,
      {
        headers: {
          Authorization: `Bearer ${githubToken}`,
          Accept: "application/vnd.github+json",
          "User-Agent": "netlify-function",
        },
      }
    );

    if (!artifactsRes.ok) {
      const txt = await artifactsRes.text();
      return { statusCode: 502, body: `GitHub artifacts list failed: ${artifactsRes.status} ${txt}` };
    }

    const artifactsJson = await artifactsRes.json();
    const latest = (artifactsJson.artifacts || [])
      .filter((a) => a.name && a.name.startsWith("italo_gtfs_") && !a.expired)
      .sort((a, b) => (b.created_at || "").localeCompare(a.created_at || ""))[0];

    if (!latest) {
      return { statusCode: 404, body: "No GTFS artifact found" };
    }

    // 2) Download artifact zip (GitHub returns a redirect to a signed URL)
    const zipRes = await fetch(latest.archive_download_url, {
      headers: {
        Authorization: `Bearer ${githubToken}`,
        Accept: "application/vnd.github+json",
        "User-Agent": "netlify-function",
      },
      redirect: "follow",
    });

    if (!zipRes.ok) {
      const txt = await zipRes.text();
      return { statusCode: 502, body: `Artifact download failed: ${zipRes.status} ${txt}` };
    }

    const arrayBuffer = await zipRes.arrayBuffer();
    const base64 = Buffer.from(arrayBuffer).toString("base64");

    return {
      statusCode: 200,
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": "attachment; filename=italo_latest.zip",
        "Cache-Control": "no-store",
      },
      body: base64,
      isBase64Encoded: true,
    };
  } catch (err) {
    return { statusCode: 500, body: "Download failed: " + (err?.message || String(err)) };
  }
};