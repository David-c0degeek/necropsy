# Necropsy desktop

Tauri/React GUI with the existing Python analysis engine. Follow the
[desktop guide](../docs/desktop.md) for first-run usage, prerequisites, engine
bundling, native launch, installer builds and platform verification limits.

After building the engine from the repository root:

```sh
npm ci
npm run desktop
```

Checks: `npm run build`, `npm run format:check`, and in `src-tauri`,
`cargo fmt --check` and `cargo clippy --locked -- -D warnings`.

`npm run dev` previews the interface in a browser; the full workflow needs
`npm run desktop`. The GUI has no hosted backend; Warcraft Logs access stays
in the Python engine.
