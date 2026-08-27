# Pushing to GitHub

Run these from the project root after unzipping.

```bash
# 1. Verify the key is NOT about to be committed
cat .gitignore | grep -n "^.env"        # must show .env
ls -la .env 2>/dev/null && echo "WARNING: .env exists locally (fine — it's ignored)"

# 2. Init and commit
git init -b main
git add .
git status                               # confirm .env is NOT listed
git commit -m "Agentic Terminal: multi-source signal aggregation + confluence dashboard"

# 3. Push to your repo
git remote add origin https://github.com/jeffczischke/Agentic-Terminal.git
git push -u origin main
```

If the repo doesn't exist yet, create it first at
https://github.com/new  (name: `Agentic-Terminal`, no README/gitignore —
this project already has both).

## First run

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then paste your key into .env
python -m agentic doctor  # <-- run this before anything else
```

`doctor` will tell you definitively whether the token works. That is the
answer we never got from the connector attempts.
