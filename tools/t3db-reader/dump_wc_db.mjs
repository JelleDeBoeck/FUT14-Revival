import { readFile } from "node:fs/promises";
import { openFifaDatabase } from "fifa-t3db";

const root =
  "D:/Afbeeldingen/FUT14-Revival/extracted/futwc_db";

const databaseBytes = await readFile(
  `${root}/futwc_ng_db.db`
);

const metadataXml = await readFile(
  `${root}/futwc_ng_db-meta.xml`,
  "utf8"
);

const db = openFifaDatabase({
  database: databaseBytes,
  metadataXml,
});

console.log("HEADER");
console.log(db.header);

console.log("\nTABLES");
console.table(db.listTables());

for (const tableName of [
  "players",
  "teamplayerlinks",
  "teams",
  "nations",
]) {
  const table = db.readTable(tableName);

  console.log(
    `\n${tableName}: ${table.info.recordCount} rows`
  );

  console.log(
    table.rows.slice(0, 5)
  );
}