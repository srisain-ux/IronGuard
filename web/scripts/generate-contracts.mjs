import { compile } from "json-schema-to-typescript";
import { readdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const schemaDir = path.resolve(here, "../../contracts/schemas");
const outputDir = path.resolve(here, "../src/contracts");
for (const name of (await readdir(schemaDir)).filter((file) => file.endsWith(".schema.json"))) {
  const schema = JSON.parse(await readFile(path.join(schemaDir, name), "utf8"));
  const result = await compile(schema, schema.title, {
    bannerComment: "/* Generated from contracts/schemas. Run pnpm contracts:generate when contracts change. */",
    ignoreMinAndMaxItems: true,
  });
  await writeFile(path.join(outputDir, name.replace(".schema.json", ".ts")), result);
}
