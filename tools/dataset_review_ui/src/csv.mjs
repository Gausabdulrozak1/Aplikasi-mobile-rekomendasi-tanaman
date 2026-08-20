import fs from "node:fs/promises";

export function parseCsv(input) {
  const text = String(input).replace(/^\uFEFF/, "");
  const records = [];
  let record = [];
  let field = "";
  let quoted = false;

  const finishField = () => {
    record.push(field);
    field = "";
  };
  const finishRecord = () => {
    finishField();
    records.push(record);
    record = [];
  };

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (quoted) {
      if (character === '"') {
        if (text[index + 1] === '"') {
          field += '"';
          index += 1;
        } else {
          quoted = false;
        }
      } else {
        field += character;
      }
      continue;
    }

    if (character === '"' && field.length === 0) {
      quoted = true;
    } else if (character === ",") {
      finishField();
    } else if (character === "\n") {
      finishRecord();
    } else if (character === "\r") {
      if (text[index + 1] === "\n") {
        index += 1;
      }
      finishRecord();
    } else {
      field += character;
    }
  }

  if (quoted) {
    throw new Error("CSV contains an unterminated quoted field");
  }
  if (field.length > 0 || record.length > 0) {
    finishRecord();
  }
  while (records.length && records.at(-1).every((value) => value === "")) {
    records.pop();
  }
  if (!records.length) {
    return { headers: [], rows: [] };
  }

  const headers = records[0];
  if (!headers.length || headers.some((header) => !header)) {
    throw new Error("CSV header contains an empty column name");
  }
  if (new Set(headers).size !== headers.length) {
    throw new Error("CSV header contains duplicate column names");
  }

  const rows = records.slice(1).map((values, index) => {
    if (values.length !== headers.length) {
      throw new Error(
        `CSV row ${index + 2} has ${values.length} fields; expected ${headers.length}`,
      );
    }
    return Object.fromEntries(headers.map((header, column) => [header, values[column]]));
  });
  return { headers, rows };
}

function encodeField(value) {
  const text = value === null || value === undefined ? "" : String(value);
  if (/[,"\r\n]/.test(text) || /^\s|\s$/.test(text)) {
    return `"${text.replaceAll('"', '""')}"`;
  }
  return text;
}

export function serializeCsv(headers, rows) {
  if (!Array.isArray(headers) || !headers.length) {
    throw new Error("Cannot serialize CSV without headers");
  }
  const lines = [headers.map(encodeField).join(",")];
  for (const row of rows) {
    lines.push(headers.map((header) => encodeField(row[header] ?? "")).join(","));
  }
  return `${lines.join("\r\n")}\r\n`;
}

export async function readCsvFile(filePath, { optional = false } = {}) {
  try {
    return parseCsv(await fs.readFile(filePath, "utf8"));
  } catch (error) {
    if (optional && error?.code === "ENOENT") {
      return { headers: [], rows: [] };
    }
    throw error;
  }
}
