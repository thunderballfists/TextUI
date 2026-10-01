# Publishing textui-markup

The distribution is `textui-markup`; the import package and console command are `textui`. Releases use `.github/workflows/release.yml`, triggered by a pushed `v*` tag. The tag must exactly match `[project].version`, for example `v0.7.0`. Preparing or merging a PR does not publish a package.

## First-release setup (maintainer)

1. In [GitHub environment settings](https://github.com/thunderballfists/TextUI/settings/environments), create `pypi`. Configure a required reviewer and allow deployment only from selected **tags** matching `v*`. Verify these protections before tagging: merely naming an environment in a workflow does not protect it.
2. In the PyPI account's [Publishing settings](https://pypi.org/manage/account/publishing/), register a pending GitHub trusted publisher:

   | Field | Value |
   | --- | --- |
   | PyPI project | `textui-markup` |
   | GitHub owner | `thunderballfists` |
   | Repository | `TextUI` |
   | Workflow filename | `release.yml` |
   | Environment | `pypi` |

   A pending publisher creates the project on its first successful upload; it does not reserve the name. If the project already exists under your account, add this publisher in its project settings instead. See [PyPI's first-project instructions](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).

No repository API token or password is needed. Only the isolated publish job receives `id-token: write`; it downloads the verified distributions and authenticates through GitHub OIDC. See [PyPI's trusted-publishing guide](https://docs.pypi.org/trusted-publishers/using-a-publisher/).

## Prepare and release (maintainer)

Update the version in `pyproject.toml` and `tests/wheel_smoke.py`, date the release notes in `CHANGELOG.md`, and review the release PR. Use the repository's isolated Poetry flow:

```sh
uvx --python 3.12 --from poetry==2.4.3 poetry check --lock
uvx --python 3.12 --from poetry==2.4.3 poetry run python -m pytest -q
uvx --python 3.12 --from poetry==2.4.3 poetry build
```

Merge only after the Python 3.11/3.12/3.14, lint, visual and clean-wheel checks pass and review feedback is addressed. Confirm publisher and environment configuration, fetch the merged commit, then deliberately create the version tag on that commit:

```sh
git fetch origin main
git tag -a v0.7.0 origin/main -m "Release textui-markup 0.7.0"
git push origin v0.7.0
```

The release workflow checks the name/tag, calls the full reusable test workflow, builds fresh wheel and source archives, and runs a wheel-only smoke check outside the checkout. It then waits for the `pypi` environment approval and publishes those artifacts. The publisher action also supplies PyPI attestations by default. Review the run and approve the protected deployment when ready.

After a successful upload, verify `python -m pip install textui-markup==0.7.0` and `python -c "import textui"` in a fresh environment. Update the README's first-release wording. Investigate any failed release before retrying; published versions cannot be overwritten.
