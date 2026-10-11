# Initial GitHub import

Use a small set of coherent commits for the initial import. These commits organize an existing project; they are not a reconstruction of its historical development. Keep their real dates. Push them together after validation so the first public version includes its code, data, evidence and documentation.

## What belongs in the repository

| Include | Reason |
|---|---|
| `src/`, `scripts/`, `tests/` | Implementation, reproducible entry points and checks |
| `ontology/`, `data/` | Target vocabulary, SHACL, synthetic source passages and gold labels |
| Dependency and formatting configuration, `Modelfile` | Environment setup and supplied model configuration |
| Rule outputs and the audited complete LLM run | Evidence for reported results, including raw synthetic responses |
| Research reports, README and guides | Methods, limitations and reproduction instructions |
| `.github/workflows/validate.yml` | Automated checks |

Keep the completed run's `responses.jsonl`, predictions, RDF, metrics, manifest, run status, summary and paired analyses. These files are small research artifacts, not disposable logs. Do not ignore all JSONL, CSV, TTL or `results/` files.

## What stays local

The `.gitignore` excludes:

- `.venv/`, other virtual environments, Python bytecode and caches.
- Coverage reports, package builds and editor/OS files.
- `.env` files, key files, secrets and local agent configuration.
- Logs, scratch files, backups and downloaded model weights.
- `PROJECT_REVIEW.md` and `results/CV_BULLETS.md`, which are personal preparation notes.
- `results/local_model_smoke.json` and `results/api_calls.jsonl`, which are one-off endpoint diagnostics.
- Every inference-run directory except the audited `challenge_20261011T181352Z`.

The last rule excludes both incomplete historical attempts and future unreviewed runs. To publish a future complete run, audit it first and add its directory as an explicit exception. Ignoring files does not remove files that are already tracked; use `git rm --cached <file>` for individual mistakenly tracked files. If a credential was published, removing it from the latest commit does not remove it from history.

## Prepare the local repository

Open PowerShell in the project root. Check Git and configure your actual author identity. Replace the identity placeholders before executing them:

```powershell
git --version
git init -b main
git config --local user.name "YOUR_NAME"
git config --local user.email "YOUR_GITHUB_EMAIL_OR_NOREPLY_EMAIL"
```

Choose a project license before releasing the code if you want to grant reuse rights. No license is selected automatically in this project. If you create `LICENSE`, include it in the first commit.

Before each commit, use `git diff --cached --stat` and, where useful, `git diff --cached` to inspect what will be included. Avoid `git add -f` for ignored files.

## Commit 1: environment and repository conventions

```powershell
git add .gitignore .gitattributes requirements.txt requirements-dev.txt pyproject.toml pytest.ini
git diff --cached --stat
git commit -m "chore: configure dependencies and repository conventions"
```

## Commit 2: ontology and synthetic benchmark

```powershell
git add ontology data
git diff --cached --stat
git commit -m "feat: add legal ontology and synthetic benchmark annotations"
```

This includes the dataset card, all source/annotation files, the gold graph, conflict labels and SHACL/SPARQL files.

## Commit 3: extraction pipeline and experiment tooling

```powershell
git add src scripts Modelfile tests/test_project.py tests/test_integrity_extended.py tests/test_edge_cases.py
git diff --cached --stat
git commit -m "feat: implement extraction validation and paired experiment tooling"
```

## Commit 4: measured results and saved-run checks

```powershell
git add results tests/test_saved_run.py
git diff --cached --stat
git commit -m "research: add audited paired results and error analysis"
```

`git add results` respects `.gitignore`: personal CV notes, smoke output and other run directories remain local. This commit includes both rule evidence and the audited complete LLM experiment. The saved-run tests are added here because they depend on that experiment.

## Commit 5: documentation and continuous integration

```powershell
git add README.md QUICKSTART.md LOCAL_EXPERIMENT.md EXPERIMENT_PROTOCOL.md PUBLISHING.md .github
git diff --cached --stat
git commit -m "docs: document reproduction findings and CI checks"
```

## Validate the complete import

```powershell
.\.venv\Scripts\python.exe -m black --check src scripts tests
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.verify_standard_shacl
.\.venv\Scripts\python.exe -m scripts.audit_artifacts --run-dir results/llm_runs/challenge_20261011T181352Z
git status --short
git status --short --ignored
git ls-files
git log --oneline
```

All tests and the artifact audit should pass. `git status --short` should be empty; the ignored view should still show local environments and excluded notes. Review `git ls-files` before pushing. If a verification command regenerates tracked reports, inspect the diff and commit the update.

## Connect to GitHub and push

These commands assume an empty remote repository. Create it on GitHub without adding a README, `.gitignore` or license through the web interface. Copy its HTTPS URL and replace `<REPOSITORY_URL>` below. Authenticate through Git Credential Manager or another supported GitHub method when prompted.

```powershell
git remote add origin '<REPOSITORY_URL>'
git remote -v
git push -u origin main
```

If the repository mentioned in your CV already has commits, do not treat it as an empty remote and do not force-push. Clone that repository into a separate directory, copy the prepared publication files into it, inspect the changes, and commit/push an update on its existing branch. If `origin` is already configured locally, check `git remote -v` before changing it.

GitHub's [official import instructions](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github) cover the empty-remote workflow.

After pushing, check the README rendering, report links, file list and Actions results. A suitable description is:

> Provenance-aware text-to-RDF extraction with ontology/SHACL guidance and an audited synthetic legal benchmark.

Suggested topics: `knowledge-graph`, `rdf`, `shacl`, `ontology`, `llm`, `information-extraction`.
