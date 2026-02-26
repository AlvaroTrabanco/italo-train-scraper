// netlify/functions/download-gtfs.js

export default async (req, context) => {
  try {
    const token = process.env.GITHUB_PAT;
    const owner = process.env.GITHUB_OWNER;
    const repo = process.env.GITHUB_REPO;

    if (!token || !owner || !repo) {
      return new Response("Server not configured (missing env vars).", { status: 500 });
    }

    const ghHeaders = {
      "Authorization": `Bearer ${token}`,
      "Accept": "application/vnd.github+json",
      "User-Agent": "netlify-download-gtfs",
      "X-GitHub-Api-Version": "2022-11-28",
    };

    // 1) List recent artifacts (repo-wide)
    const listUrl = `https://api.github.com/repos/${owner}/${repo}/actions/artifacts?per_page=100`;
    const listRes = await fetch(listUrl, { headers: ghHeaders });

    if (!listRes.ok) {
      const txt = await listRes.text();
      return new Response(`GitHub list artifacts failed: ${listRes.status} ${txt}`, { status: 502 });
    }

    const listJson = await listRes.json();
    const artifacts = Array.isArray(listJson.artifacts) ? listJson.artifacts : [];

    // Pick most recent matching artifact name
    const candidates = artifacts
      .filter(a =>
        a &&
        a.name &&
        a.name.startsWith("italo_gtfs_") &&
        a.expired === false &&
        a.archive_download_url
      )
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

    if (candidates.length === 0) {
      return new Response("No non-expired GTFS artifact found.", { status: 404 });
    }

    const latest = candidates[0];

    // 2) Request the artifact archive download URL.
    // GitHub replies with a 302 to a signed URL.
    const dlRes = await fetch(latest.archive_download_url, {
      headers: ghHeaders,
      redirect: "manual",
    });

    const location = dlRes.headers.get("location");
    if (!(dlRes.status === 302 || dlRes.status === 301) || !location) {
      const txt = await dlRes.text().catch(() => "");
      return new Response(
        `GitHub artifact download did not redirect as expected: ${dlRes.status} ${txt}`,
        { status: 502 }
      );
    }

    // 3) Fetch the signed URL (no auth needed here typically)
    const signedRes = await fetch(location);

    if (!signedRes.ok || !signedRes.body) {
      const txt = await signedRes.text().catch(() => "");
      return new Response(`Signed download failed: ${signedRes.status} ${txt}`, { status: 502 });
    }

    // 4) Stream back to client
    const filename = `${latest.name}.zip`;
    return new Response(signedRes.body, {
      status: 200,
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": `attachment; filename="${filename}"`,
        // Optional: prevent caching if you want always-fresh
        "Cache-Control": "no-store",
      },
    });
  } catch (e) {
    return new Response(`Server error: ${e?.message || String(e)}`, { status: 500 });
  }
};