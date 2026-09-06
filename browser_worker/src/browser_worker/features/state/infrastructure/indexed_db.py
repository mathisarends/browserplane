import logging

from cdpify import Client
from cdpify.domains.runtime.types import CallArgument

from browser_worker.features.state.application.exceptions import (
    BrowserStateFailedException,
)
from browser_worker.features.state.application.models import OriginIndexedDb
from browser_worker.features.state.infrastructure.origin import loaded_origin

logger = logging.getLogger(__name__)


async def capture_indexed_db(
    client: Client,
    origins: set[str],
) -> tuple[OriginIndexedDb, ...]:
    captured: list[OriginIndexedDb] = []
    for origin in sorted(origins):
        try:
            async with loaded_origin(client, origin) as session:
                result = await session.runtime.evaluate(
                    expression=CAPTURE_INDEXED_DB,
                    await_promise=True,
                    return_by_value=True,
                    silent=True,
                )
                raw = result.result.value
                if not isinstance(raw, list):
                    raise TypeError("IndexedDB capture returned no value")
                captured.append(
                    OriginIndexedDb.model_validate({"origin": origin, "databases": raw})
                )
        except Exception:
            logger.warning("Could not read IndexedDB of %s", origin, exc_info=True)
    return tuple(captured)


async def restore_indexed_db(client: Client, origin: OriginIndexedDb) -> None:
    """Replace an origin's IndexedDB databases from a portable snapshot."""
    payload = origin.model_dump(mode="json", by_alias=True, include={"databases"})
    async with loaded_origin(client, origin.origin) as session:
        global_object = await session.runtime.evaluate(expression="globalThis")
        object_id = global_object.result.object_id
        if object_id is None:
            raise TypeError("Could not address the origin execution context")
        result = await session.runtime.call_function_on(
            object_id=object_id,
            function_declaration=RESTORE_INDEXED_DB,
            arguments=[CallArgument(value=payload)],
            await_promise=True,
            return_by_value=True,
            silent=True,
        )
        if result.exception_details is not None:
            raise BrowserStateFailedException("IndexedDB restore script failed")


CAPTURE_INDEXED_DB = r"""
(async () => {
    const request = (value) => new Promise((resolve, reject) => {
        value.onsuccess = () => resolve(value.result);
        value.onerror = () => reject(value.error);
    });
    const bytes = (value) => {
        let binary = "";
        for (const byte of new Uint8Array(value)) binary += String.fromCharCode(byte);
        return btoa(binary);
    };
    const seen = new Map();
    let nextId = 1;
    const encode = async (value) => {
        if (value === undefined) return {$type: "undefined"};
        if (typeof value === "bigint") return {$type: "bigint", value: String(value)};
        if (typeof value === "number" && !Number.isFinite(value)) {
            return {$type: "number", value: String(value)};
        }
        if (value === null || typeof value !== "object") return value;
        if (seen.has(value)) return {$ref: seen.get(value)};
        const id = nextId++;
        seen.set(value, id);
        if (value instanceof Date) {
            return {$id: id, $type: "date", value: value.getTime()};
        }
        if (value instanceof RegExp) {
            return {$id: id, $type: "regexp", source: value.source, flags: value.flags};
        }
        if (value instanceof ArrayBuffer) {
            return {$id: id, $type: "arrayBuffer", value: bytes(value)};
        }
        if (ArrayBuffer.isView(value)) {
            const buffer = value.buffer.slice(
                value.byteOffset, value.byteOffset + value.byteLength,
            );
            return {
                $id: id, $type: "view", name: value.constructor.name,
                value: bytes(buffer),
            };
        }
        if (value instanceof Blob) {
            return {
                $id: id,
                $type: "blob",
                mimeType: value.type,
                value: bytes(await value.arrayBuffer()),
            };
        }
        if (value instanceof Map) {
            const entries = [];
            for (const [key, item] of value) {
                entries.push([await encode(key), await encode(item)]);
            }
            return {$id: id, $type: "map", value: entries};
        }
        if (value instanceof Set) {
            const items = [];
            for (const item of value) items.push(await encode(item));
            return {$id: id, $type: "set", value: items};
        }
        if (Array.isArray(value)) {
            const items = await Promise.all(value.map(encode));
            return {$id: id, $type: "array", value: items};
        }
        const entries = [];
        for (const key of Object.keys(value)) {
            entries.push([key, await encode(value[key])]);
        }
        return {$id: id, $type: "object", value: entries};
    };

    if (!indexedDB.databases) throw new Error("IndexedDB enumeration is unavailable");
    const databases = [];
    for (const info of await indexedDB.databases()) {
        if (!info.name) continue;
        const db = await request(indexedDB.open(info.name));
        try {
            const names = Array.from(db.objectStoreNames);
            const transaction = names.length ? db.transaction(names, "readonly") : null;
            const objectStores = [];
            for (const name of names) {
                const store = transaction.objectStore(name);
                const [keys, values] = await Promise.all([
                    request(store.getAllKeys()), request(store.getAll()),
                ]);
                const records = [];
                for (let index = 0; index < values.length; index++) {
                    records.push({
                        key: await encode(keys[index]),
                        value: await encode(values[index]),
                    });
                }
                objectStores.push({
                    name,
                    keyPath: store.keyPath,
                    autoIncrement: store.autoIncrement,
                    indexes: Array.from(store.indexNames, (indexName) => {
                        const item = store.index(indexName);
                        return {
                            name: item.name,
                            keyPath: item.keyPath,
                            unique: item.unique,
                            multiEntry: item.multiEntry,
                        };
                    }),
                    records,
                });
            }
            databases.push({name: db.name, version: db.version, objectStores});
        } finally {
            db.close();
        }
    }
    return databases;
})()
"""


RESTORE_INDEXED_DB = r"""
async function(payload) {
    const request = (value) => new Promise((resolve, reject) => {
        value.onsuccess = () => resolve(value.result);
        value.onerror = () => reject(value.error);
        value.onblocked = () => reject(new Error("IndexedDB request was blocked"));
    });
    const transaction = (value) => new Promise((resolve, reject) => {
        value.oncomplete = () => resolve();
        value.onerror = () => reject(value.error);
        value.onabort = () => reject(
            value.error || new Error("IndexedDB transaction aborted"),
        );
    });
    const binary = (value) => {
        const decoded = atob(value);
        const bytes = new Uint8Array(decoded.length);
        for (let index = 0; index < decoded.length; index++) {
            bytes[index] = decoded.charCodeAt(index);
        }
        return bytes;
    };
    const references = new Map();
    const decode = (value) => {
        if (value === null || typeof value !== "object") return value;
        if ("$ref" in value) return references.get(value.$ref);
        if (!("$type" in value)) return value;
        if (value.$type === "undefined") return undefined;
        if (value.$type === "bigint") return BigInt(value.value);
        if (value.$type === "number") return Number(value.value);
        if (value.$type === "date") {
            const result = new Date(value.value);
            references.set(value.$id, result);
            return result;
        }
        if (value.$type === "regexp") {
            const result = new RegExp(value.source, value.flags);
            references.set(value.$id, result);
            return result;
        }
        if (value.$type === "arrayBuffer") {
            const result = binary(value.value).buffer;
            references.set(value.$id, result);
            return result;
        }
        if (value.$type === "view") {
            const buffer = binary(value.value).buffer;
            const constructor = globalThis[value.name];
            const result = value.name === "DataView"
                ? new DataView(buffer)
                : new constructor(buffer);
            references.set(value.$id, result);
            return result;
        }
        if (value.$type === "blob") {
            const result = new Blob([binary(value.value)], {type: value.mimeType});
            references.set(value.$id, result); return result;
        }
        let result;
        if (value.$type === "array") result = [];
        else if (value.$type === "map") result = new Map();
        else if (value.$type === "set") result = new Set();
        else result = {};
        references.set(value.$id, result);
        if (value.$type === "array") {
            value.value.forEach((item) => result.push(decode(item)));
        } else if (value.$type === "map") {
            value.value.forEach(
                ([key, item]) => result.set(decode(key), decode(item)),
            );
        } else if (value.$type === "set") {
            value.value.forEach((item) => result.add(decode(item)));
        } else {
            value.value.forEach(([key, item]) => result[key] = decode(item));
        }
        return result;
    };

    if (indexedDB.databases) {
        for (const info of await indexedDB.databases()) {
            if (info.name) await request(indexedDB.deleteDatabase(info.name));
        }
    }
    for (const database of payload.databases) {
        const opening = indexedDB.open(database.name, database.version);
        opening.onupgradeneeded = () => {
            const db = opening.result;
            for (const definition of database.objectStores) {
                const store = db.createObjectStore(definition.name, {
                    keyPath: definition.keyPath,
                    autoIncrement: definition.autoIncrement,
                });
                for (const index of definition.indexes) {
                    store.createIndex(index.name, index.keyPath, {
                        unique: index.unique,
                        multiEntry: index.multiEntry,
                    });
                }
            }
        };
        const db = await request(opening);
        try {
            const names = database.objectStores.map((store) => store.name);
            if (!names.length) continue;
            const writing = db.transaction(names, "readwrite");
            for (const definition of database.objectStores) {
                const store = writing.objectStore(definition.name);
                for (const record of definition.records) {
                    const value = decode(record.value);
                    if (definition.keyPath === null) {
                        store.put(value, decode(record.key));
                    }
                    else store.put(value);
                }
            }
            await transaction(writing);
        } finally {
            db.close();
        }
    }
    return true;
}
"""
