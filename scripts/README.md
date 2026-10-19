# Repository map

The scheduled workflow uses GitHub's built-in token to refresh a clearly labeled
**public repository map**. No custom secret is needed. This view excludes private
repositories and does not claim an organization-wide total or zero private repos.

To include private repository counts, configure the optional `ORG_MAP_TOKEN`
Actions secret with a fine-grained token owned by this organization, access to all
its repositories, and **Metadata: read** permission. The workflow then uses
`--scope all`; private names and descriptions stay out of both the generated map
and diagnostic logs. Keep checkout/publishing on the built-in token; the map token
does not need content write permission.

```sh
python3 -m unittest discover -s scripts -q
python3 scripts/build_repo_map.py --org aura-lab-wm --scope public --write profile/README.md
```

Full counts require `GITHUB_TOKEN` in the environment and `--scope all`. A token
restricted to selected repositories cannot provide complete organization counts.
The default `--names public` lists only public names even in full-count mode.

Pull requests run the generator tests without publishing. Scheduled, manual, and
repository-dispatch runs test first, then refresh the map. An unchanged map keeps
its generation timestamp and produces no commit. The publishing repository's own
push date is excluded from the table so bot commits cannot perpetuate updates.
API/authentication failures preserve the last committed map and still fail the run.

References: [GitHub organization repository API](https://docs.github.com/en/rest/repos/repos#list-organization-repositories)
and [using Actions secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).
