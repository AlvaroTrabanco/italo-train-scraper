const fetch = require("node-fetch");

exports.handler = async function(event) {
  const providedKey = event.queryStringParameters?.k;
  const expectedKey = process.env.GTFS_DL_KEY;

  if (!expectedKey) {
    return {
      statusCode: 500,
      body: "Server misconfiguration: GTFS_DL_KEY not set"
    };
  }

  if (!providedKey || providedKey !== expectedKey) {
    return {
      statusCode: 403,
      body: "Forbidden"
    };
  }

  const githubToken = process.env.GITHUB_PAT;
  if (!githubToken) {
    return {
      statusCode: 500,
      body: "Server misconfiguration: GITHUB_PAT not set"
    };
  }

  try {
    // Get latest artifact from your repo
    const repoOwner = "AlvaroTrabanco";
    const repoName = "italo-train-scraper";

    const artifactsRes = await fetch(
      `https://api.github.com/repos/${repoOwner}/${repoName}/actions/artifacts`,
      {
        headers: {
          Authorization: `Bearer ${githubToken}`,
          Accept: "application/vnd.github+json"
        }
      }
    );

    const artifacts = await artifactsRes.json();
    const latest = artifacts.artifacts
      .filter(a => a.name.startsWith("italo_gtfs_"))
      .sort((a,b) => b.created_at.localeCompare(a.created_at))[0];

    if (!latest) {
      return { statusCode: 404, body: "No GTFS artifact found" };
    }

    const zipRes = await fetch(latest.archive_download_url, {
      headers: {
        Authorization: `Bearer ${githubToken}`,
        Accept: "application/vnd.github+json"
      }
    });

    const buffer = await zipRes.buffer();

    return {
      statusCode: 200,
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": "attachment; filename=italo_latest.zip"
      },
      body: buffer.toString("base64"),
      isBase64Encoded: true
    };

  } catch (err) {
    return {
      statusCode: 500,
      body: "Download failed: " + err.message
    };
  }
};