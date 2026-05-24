# Site (Docusaurus)

The public learning site for **AP2 from First Principles**.

- Live: https://ap2-getting-started.vercel.app
- Project overview, how to run the lessons, and the design docs are in the
  [repository root README](../README.md).

## Local development

```bash
npm install
npm run start      # dev server with live reload
npm run build      # static build into ./build
```

Lesson pages import real, tested code from `../lessons` and `../ap2_shared` via
`remark-code-import`, so a broken snippet fails the build.
