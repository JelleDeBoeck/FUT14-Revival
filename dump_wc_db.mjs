import { readFile } from "node:fs/promises";
import { openFifaDatabase } from "fifa-t3db";

const root =
  "D:/Afbeeldingen/FUT14-Revival/extracted/cards_db";

const db = openFifaDatabase({
  database: await readFile(`${root}/cards_ng_db.db`),
  metadataXml: await readFile(
    `${root}/cards_ng_db-meta.xml`,
    "utf8"
  ),
});

const terms =
  /resource|asset|card|rare|fut|item|subtype|playerid/i;

for (const info of db.listTables()) {
  const name =
    info.name ??
    info.tableName ??
    info.tablename ??
    String(info);

  const table = db.readTable(name);

  if (!table.rows.length) {
    continue;
  }

  const fields = Object.keys(table.rows[0]);

  const interesting = fields.filter(
    field => terms.test(field)
  );

  if (interesting.length) {
    console.log(
      `${name}: ${interesting.join(", ")}`
    );
  }
}