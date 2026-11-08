# GitHub publication workflow (Windows PowerShell)

The closeout was assembled from a technical handoff + October 12 terminal output. It is not an extraction of the downloaded 16 MB CHTC review bundle; the detailed biomechanical output remains unreviewed.

## Recommended: publish to a new branch of an existing checked-out repository

1. Download `OpenSimAD_GitHub_Closeout_2026-11-08.zip` from ChatGPT to your Windows Downloads folder.
2. Set `$repo` to the local Git repository. The path below is suggested from the last PowerShell working directory; confirm that it is the correct repository before running.
3. Run the following whole block. It will create a branch and push the closeout files, but will NOT add any CHTC raw data. You need authenticated Git credentials. It does not submit simulation jobs.

```powershell
$repo = 'C:\OpenCapWinTest\opencap-processing-grf-review'
$zip = Join-Path $env:USERPROFILE 'Downloads\OpenSimAD_GitHub_Closeout_2026-11-08.zip'
if (-not (Test-Path $zip)) { throw "Closeout ZIP missing: $zip" }
if (-not (Test-Path (Join-Path $repo '.git'))) { throw "Not a checked-out Git repository: $repo" }
Set-Location $repo
$branch = 'research/opensimad-closeout-2026-11-08'
$old = git status --porcelain
if ($LASTEXITCODE -ne 0) { throw 'git status failed' }
if ($old) { Write-Host 'Existing worktree changes:'; $old; throw 'Please commit/stash existing changes before publication.' }
git remote -v
if (-not (git remote get-url origin 2>$null)) { throw 'No origin remote; configure your intended GitHub repo first.' }
git switch -c $branch
if ($LASTEXITCODE -ne 0) { throw 'Branch creation failed; inspect existing branches.' }
Expand-Archive -Path $zip -DestinationPath $repo -Force
git add -- 'research/OpenSimAD_STS_2026'
git diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'Whitespace/error check failed' }
Write-Host 'Files queued for commit:'
git diff --cached --name-only
Write-Host 'Review staged files, particularly optional source snapshots, before proceeding.'
git commit -m 'docs(research): archive OpenSimAD STS and walking convergence results'
if ($LASTEXITCODE -ne 0) { throw 'Commit failed' }
git push -u origin $branch
if ($LASTEXITCODE -ne 0) { throw 'Push failed; inspect authentication/remote permissions.' }
```

This creates a reviewable branch on GitHub; merge after checking license, privacy, and provenance. If the repository is public, keep the publication limited to scripts and de-identified numerical summary tables unless your lab explicitly permits more.

## Include actual source code, optionally

On the CHTC host run `bash collect_source_on_chtc.sh` from this package's `scripts` directory (copy the script over with scp first), then copy the generated source tar to Windows with `scp`, inspect the contents, and extract under `research/OpenSimAD_STS_2026/source/`. Review and commit on a separate branch/commit if licensing permits. Do not automatically publish the `.env` file, the individual subject dataset, or licensed papers.
