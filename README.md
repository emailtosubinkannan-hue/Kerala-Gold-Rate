# Kerala Gold Rate – automatic website

A free website that updates the Kerala 22K gold rate by itself, 5 times a day
(about 9:35, 11:35, 14:35, 17:35 and 20:35 India time). No one has to type anything.

## What is in this folder

| File | What it does |
|---|---|
| `index.html` | The page people open (rate, charts, buy/wait signals, calculator) |
| `data.json` | The saved rates and history. The robot updates this file |
| `update_rates.py` | Reads the rate from a public rates website |
| `.github/workflows/update.yml` | The schedule that runs the script on GitHub |

---

## Step 1: Create a free GitHub account (about 2 minutes)

1. Go to **github.com** and click **Sign up**.
2. Enter your email, a password and a username. Verify the email code.
3. Choose the **Free** plan.

## Step 2: Create the repository

1. Click the **+** at the top right, then **New repository**.
2. Name it, for example `kerala-gold-rate`.
3. Choose **Public** (needed for free GitHub Pages).
4. Tick **Add a README file**, then click **Create repository**.

## Step 3: Upload the files

1. In the repository, click **Add file → Upload files**.
2. Unzip this package on your phone or computer and drag in **index.html, data.json, update_rates.py**.
3. Click **Commit changes**.

**The workflow file needs its own folder path:**

1. Click **Add file → Create new file**.
2. In the name box type exactly: `.github/workflows/update.yml`
   (typing the `/` creates the folders).
3. Open `update.yml` from this package, copy everything and paste it into the big box.
4. Click **Commit changes**.

## Step 4: Allow the robot to save data

1. **Settings → Actions → General**.
2. Scroll to **Workflow permissions**, choose **Read and write permissions**, click **Save**.

## Step 5: Turn on the website

1. **Settings → Pages**.
2. Under **Branch**, choose **main** and folder **/ (root)**, click **Save**.
3. After about a minute your link appears at the top of that page:
   `https://YOUR-USERNAME.github.io/kerala-gold-rate/`

## Step 6: Run it once to test

1. Open the **Actions** tab. If asked, click **I understand my workflows, enable them**.
2. Click **Update gold rate** on the left, then **Run workflow**.
3. A green tick means it worked. Open your website link and refresh.
   The date and rate should be today's.

After this it runs on its own.

---

## Good to know

- **Timing:** GitHub can start scheduled jobs 5 to 30 minutes late. That is normal.
- **If a run shows a red cross:** the rates website changed its layout or was down.
  The page keeps showing the last good rate and warns if it is not today's.
  Open the failed run in the Actions tab and send me the log text; the fix is usually one line.
- **Inactive repositories:** GitHub may pause scheduled jobs on a repository with no
  activity for 60 days. The daily data commits normally count as activity, but if the
  schedule ever stops, open Actions and click **Enable workflow**.
- **Sources:** the script reads keralagold.org first and keralagoldrates.com as a backup.
  These republish the official AKGSMA rate. Please check their terms of use.
- **Safety checks:** the script ignores any value outside 3,000 to 100,000 per gram or
  more than 15% away from the previous day, so a wrong read does not corrupt the history.
- The purchase guide and broker-style view are simple rules on the last 8 days of prices.
  They are not financial advice.

## Search (SEO) and custom domain

- `seo.py` keeps the page title, description, share tags, structured data, the rate summary sentence and the FAQ in step with `data.json`, and writes `sitemap.xml` and `robots.txt`. The bot runs it after every new rate. To run it by hand: `python3 seo.py`.
- The site address used in those files is taken from a file named `CNAME` (a custom domain). With no `CNAME`, the GitHub Pages address is used.
- To move to a custom domain: add a `CNAME` file containing only the domain (for example `keralagoldrate.in`), run `python3 seo.py`, commit, then set the same domain in the repository's Settings > Pages and tick "Enforce HTTPS".
