import fs from "node:fs/promises";
import path from "node:path";

function temporaryPath(targetPath) {
  const suffix = `${process.pid}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return path.join(path.dirname(targetPath), `.${path.basename(targetPath)}.${suffix}.tmp`);
}

export async function atomicWriteFile(targetPath, content, { validate } = {}) {
  await fs.mkdir(path.dirname(targetPath), { recursive: true });
  const tempPath = temporaryPath(targetPath);
  let handle;
  try {
    handle = await fs.open(tempPath, "wx");
    await handle.writeFile(content);
    await handle.sync();
    await handle.close();
    handle = undefined;

    if (validate) {
      await validate(tempPath);
    }
    await fs.rename(tempPath, targetPath);
  } catch (error) {
    if (handle) {
      await handle.close().catch(() => undefined);
    }
    await fs.rm(tempPath, { force: true }).catch(() => undefined);
    throw error;
  }
}

export async function atomicWriteJson(targetPath, value) {
  const content = `${JSON.stringify(value, null, 2)}\n`;
  await atomicWriteFile(targetPath, content, {
    validate: async (tempPath) => JSON.parse(await fs.readFile(tempPath, "utf8")),
  });
}
