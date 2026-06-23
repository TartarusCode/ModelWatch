# External cron via cron-job.org

GitHub's built-in `schedule` trigger is best-effort and often runs only a handful of times per day. ModelWatch uses [cron-job.org](https://cron-job.org) to call the GitHub Actions API every 30 minutes and dispatch **Build and deploy** reliably.

## 1. Create a GitHub fine-grained PAT

1. GitHub → **Settings** → **Developer settings** → **Fine-grained tokens** → **Generate new token**
2. **Repository access**: Only select repositories → `ModelWatch`
3. **Permissions**:
   - **Actions**: Read and write
   - **Metadata**: Read-only (required)
4. Generate and copy the token — you will not see it again.

Classic PAT alternative: scope `repo` (private) or `public_repo` + `workflow` (legacy).

## 2. Add repository secrets (if not already set)

In **TartarusCode/ModelWatch** → **Settings** → **Secrets and variables** → **Actions**:

| Secret | Purpose |
|--------|---------|
| `OPENROUTER_API_KEY` | Optional; improves OpenRouter API reliability |

No cron-specific secret is required — the PAT on cron-job.org is the auth boundary.

## 3. Create the cron-job.org job

1. Sign up / log in at [console.cron-job.org](https://console.cron-job.org)
2. **Cronjobs** → **Create cronjob**

### Schedule

| Field | Value |
|-------|-------|
| Title | `ModelWatch build` |
| URL | `https://api.github.com/repos/TartarusCode/ModelWatch/actions/workflows/build-and-deploy.yml/dispatches` |
| Schedule | Every 30 minutes (or custom: `*/30 * * * *`) |
| Request method | **POST** |

### Request headers

Add these headers (cron-job.org → **Advanced** → **Headers**):

| Header | Value |
|--------|-------|
| `Accept` | `application/vnd.github+json` |
| `Authorization` | `Bearer YOUR_FINE_GRAINED_PAT` |
| `X-GitHub-Api-Version` | `2022-11-28` |
| `Content-Type` | `application/json` |

Replace `YOUR_FINE_GRAINED_PAT` with the token from step 1.

### Request body

**Required.** GitHub returns **422** if the body is missing or not valid JSON.

In cron-job.org: **Advanced** → **Request body** (or **Import from cURL** using the example below):

```json
{
  "ref": "main"
}
```

Use the **default branch** name if it is not `main`.

### Options

- Enable **Save response** temporarily while testing; disable once stable.
- Set **Notify on failure** if you want email when the HTTP call fails (204 = success).

## 4. Test

1. In cron-job.org, use **Run now** on the job.
2. In GitHub → **Actions**, confirm **Build and deploy** started with event **workflow_dispatch**.
3. A successful API call returns **HTTP 204** with an empty body.

Manual runs still work from GitHub → **Actions** → **Build and deploy** → **Run workflow**.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| HTTP 401 | PAT expired or wrong `Authorization` header (`Bearer ` prefix required) |
| HTTP 404 | Wrong repo name or workflow filename; path must be `build-and-deploy.yml` |
| HTTP 422 | Missing/malformed JSON body (`nil is not an object`) — set body to `{"ref":"main"}` or import the curl example below; or invalid `ref` (branch does not exist) |
| Workflow not listed | PAT missing **Actions: Read and write** on this repo |
| Duplicate runs | Remove any old GitHub `schedule` cron on the workflow (should already be removed) |

## curl reference

```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer YOUR_FINE_GRAINED_PAT" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "Content-Type: application/json" \
  -d '{"ref":"main"}' \
  https://api.github.com/repos/TartarusCode/ModelWatch/actions/workflows/build-and-deploy.yml/dispatches
```

Expected response: `204 No Content`.
