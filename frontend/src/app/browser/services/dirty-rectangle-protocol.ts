/**
 * Reader for the worker's changed-tile packets.
 *
 * One websocket message is one canvas update:
 *   frame header: magic "DRJP", version, canvas width, canvas height, patch count
 *   patch*:       x, y, width, height, JPEG byte length, JPEG bytes
 * All fields are big endian, matching `struct` on the worker side.
 */

const MAGIC = "DRJP";
const VERSION = 1;
const FRAME_HEADER_BYTES = 4 + 1 + 2 + 2 + 4;
const PATCH_HEADER_BYTES = 2 + 2 + 2 + 2 + 4;

export interface DirtyRectanglePatch {
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
  readonly jpeg: Blob;
}

export interface DirtyRectangleUpdate {
  readonly canvasWidth: number;
  readonly canvasHeight: number;
  readonly patches: readonly DirtyRectanglePatch[];
  readonly bytes: number;
}

export class DirtyRectangleProtocolError extends Error {}

export function decodeDirtyRectangleUpdate(packet: ArrayBuffer): DirtyRectangleUpdate {
  const view = new DataView(packet);
  if (packet.byteLength < FRAME_HEADER_BYTES) {
    throw new DirtyRectangleProtocolError("Dirty rectangle packet is shorter than its header");
  }

  const magic = String.fromCharCode(...new Uint8Array(packet, 0, 4));
  if (magic !== MAGIC) {
    throw new DirtyRectangleProtocolError(`Unexpected dirty rectangle magic "${magic}"`);
  }
  const version = view.getUint8(4);
  if (version !== VERSION) {
    throw new DirtyRectangleProtocolError(`Unsupported dirty rectangle version ${version}`);
  }

  const canvasWidth = view.getUint16(5);
  const canvasHeight = view.getUint16(7);
  const patchCount = view.getUint32(9);

  const patches: DirtyRectanglePatch[] = [];
  let offset = FRAME_HEADER_BYTES;
  for (let index = 0; index < patchCount; index += 1) {
    if (offset + PATCH_HEADER_BYTES > packet.byteLength) {
      throw new DirtyRectangleProtocolError("Dirty rectangle packet ended inside a patch header");
    }
    const x = view.getUint16(offset);
    const y = view.getUint16(offset + 2);
    const width = view.getUint16(offset + 4);
    const height = view.getUint16(offset + 6);
    const length = view.getUint32(offset + 8);
    offset += PATCH_HEADER_BYTES;
    if (offset + length > packet.byteLength) {
      throw new DirtyRectangleProtocolError("Dirty rectangle packet ended inside a patch payload");
    }
    patches.push({
      x,
      y,
      width,
      height,
      jpeg: new Blob([packet.slice(offset, offset + length)], { type: "image/jpeg" }),
    });
    offset += length;
  }

  return { canvasWidth, canvasHeight, patches, bytes: packet.byteLength };
}
