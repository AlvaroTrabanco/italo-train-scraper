export default async (req) => {
  const url = new URL(req.url);
  const key = url.searchParams.get("key");

  if (!process.env.GTFS_DL_KEY || key !== process.env.GTFS_DL_KEY) {
    return new Response("Forbidden", { status: 403 });
  }

  const owner = process.env.GITHUB_OWNER;
  const repo = process.env.GITHUB_REPO;
  const token = process.env.GITHUB_TOKEN;

  // 1) Find latest successful workflow run (you can also target a specific workflow file)
  const runsRes = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/runs?status=success&per_page=1`,
    { headers: { Authorization: `Bearer ${token}`, "User-Agent": "netlify" } }
  );
  if (!runsRes.ok) return new Response("Failed to list runs", { status: 500 });
  const runs = await runsRes.json();
  const runId = runs.workflow_runs?.[0]?.id;
  if (!runId) return new Response("No successful runs found", { status: 404 });

  // 2) List artifacts for that run
  const artRes = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/runs/${runId}/artifacts`,
    { headers: { Authorization: `Bearer ${token}`, "User-Agent": "netlify" } }
  );
  if (!artRes.ok) return new Response("Failed to list artifacts", { status: 500 });
  const arts = await artRes.json();

  // Pick the artifact name you used in upload-artifact step
  const artifact = (arts.artifacts || []).find(a => (a.name || "").startsWith("italo_gtfs_"));
  if (!artifact) return new Response("GTFS artifact not found", { status: 404 });

  // 3) Download artifact as a zip
  // GitHub returns a redirect or a binary depending on endpoint behavior.
  const dlRes = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/artifacts/${artifact.id}/zip`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        "User-Agent": "netlify",
        Accept: "application/vnd.github+json",
      },
      redirect: "follow",
    }
  );

  if (!dlRes.ok) return new Response("Failed to download artifact", { status: 500 });

  return new Response(dlRes.body, {
    status: 200,
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition": `attachment; filename="italo_latest.zip"`,
      // Avoid caching if you want “always latest”
      "Cache-Control": "no-store",
    },
  });
};