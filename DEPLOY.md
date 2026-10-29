# Deploying the dashboard to Vercel (password-protected)

The scan produces a **static HTML snapshot**. To host it at a custom domain
and keep it fresh, GitHub Actions runs the scan on a schedule and deploys the
result to Vercel. Access is gated by HTTP Basic Auth in `middleware.ts`, which
works on every Vercel plan (including the free Hobby tier).

```
GitHub Actions (cron)  ->  python -m agentic scan  ->  public/index.html
                       ->  vercel build + deploy    ->  Thankyouai.ai
                       ->  middleware.ts gates every request with a password
```

The API key and the site password never live in the repo. They live in GitHub
Actions secrets and Vercel environment variables respectively.

---

## One-time setup

### 1. Create the Vercel project

1. Install the CLI locally: `npm i -g vercel`
2. From the repo root, run `vercel link` and follow the prompts to create /
   select a project. This writes `.vercel/project.json` (gitignored).
3. Note the two IDs it prints (also in `.vercel/project.json`):
   - `orgId`     -> `VERCEL_ORG_ID`
   - `projectId` -> `VERCEL_PROJECT_ID`

### 2. Create a Vercel access token

Vercel -> Account Settings -> **Tokens** -> Create. Copy the value once.

### 3. Add the GitHub Actions secrets

Repo -> Settings -> **Secrets and variables -> Actions** -> New repository secret:

| Secret              | Value                                          |
| ------------------- | ---------------------------------------------- |
| `UW_API_KEY`        | your Unusual Whales API key                    |
| `VERCEL_TOKEN`      | the token from step 2                          |
| `VERCEL_ORG_ID`     | `orgId` from step 1                            |
| `VERCEL_PROJECT_ID` | `projectId` from step 1                        |

### 4. Set the site password in Vercel

Vercel -> Project -> Settings -> **Environment Variables** (Production):

| Variable              | Value                     |
| --------------------- | ------------------------- |
| `BASIC_AUTH_USER`     | a username you choose     |
| `BASIC_AUTH_PASSWORD` | a strong password         |

These are read by `middleware.ts` at request time. Change them anytime; the
next deploy (or redeploy) picks them up.

### 5. Point the domain

Vercel -> Project -> Settings -> **Domains** -> add `thankyouai.ai`
(and `www.thankyouai.ai`). Vercel shows the exact DNS records to set at your
registrar (either an A record / CNAME, or move the nameservers to Vercel).

### 6. Activate the schedule

Scheduled workflows only run from the **default branch**, so merge this branch
into `main`. After that, the cron fires on its own. To deploy on demand,
open the repo's **Actions** tab -> *scan-and-deploy* -> **Run workflow**.

---

## Tuning the schedule

Edit the `cron` line in `.github/workflows/deploy.yml`. It is UTC. The default
`*/30 13-21 * * 1-5` is every 30 minutes during US market hours, Mon–Fri.

## Notes

- The dashboard holds your private signals — keep the password strong and never
  commit `.env`, `BASIC_AUTH_*`, or any token.
- A deploy only publishes if the scan succeeds; a failed scan fails the job
  and leaves the live site on its previous version.
- Prefer Vercel's **native** password protection instead of the middleware?
  It's a Pro-plan feature (Project -> Settings -> Deployment Protection). If you
  enable it, you can delete `middleware.ts` and the two `BASIC_AUTH_*` vars.
