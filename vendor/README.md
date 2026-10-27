# Lit Canon source packages

These MIT-licensed archives contain the unmodified Lit Canon package sources and
compiled JavaScript from revision
[`4fe0827b03bacc3f04008b8300b3e6942593c323`](https://github.com/mathisarends/lit-canon/tree/4fe0827b03bacc3f04008b8300b3e6942593c323).
The packages were not available from the npm registry when this migration was
verified. Local archives keep installation independent of a neighboring checkout
or an unpinned Git branch.

| Package | Version | Source |
| --- | --- | --- |
| `lit-canon-composition` | `0.1.0` | `packages/composition` |
| `lit-canon-fetch` | `1.0.0` | `packages/fetch` |
| `lit-canon-api` | `1.0.0` | `packages/api` |

`lit-canon.json` records each revision, source directory, compiler and archive
SHA-256. `frontend/package-lock.json` records npm's integrity hashes. Package
manifests install the archives through exact local file references.

To rebuild, check out that revision in an isolated directory. Install each
package's declared dependencies and `typescript@6.0.3`; the verified peer versions
are Lit `3.3.3`, `@lit/context@1.1.6`, `@lit-labs/router@0.1.4` and
`@tanstack/lit-query@0.2.25`. Run `tsc -p tsconfig.build.json` in each package,
restore its original manifest if dependency installation changed it, then run
`npm pack --ignore-scripts`. Preserve the original manifest, sources and license
inside the archive. Composition's query integration is an optional entry point.

For an upgrade, review the upstream guides, build one explicit revision, update
the archives and provenance together, and run `npm install --ignore-scripts` in
`frontend` to update its lockfile. Run all documented application checks before
committing. A suitable published release can replace the corresponding archive
with an exact registry version after those checks pass.
