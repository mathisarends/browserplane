import type { KeyParams, MouseParams } from "@browsertunnel/browser-rpc-client";

export type MousePoint = Pick<MouseParams, "x" | "y">;

const MOUSE_BUTTONS = ["left", "middle", "right", "back", "forward"] as const;

export function mouseButtonOf(event: MouseEvent): MouseParams["button"] {
  return MOUSE_BUTTONS[event.button] ?? "none";
}

export function mouseParams(
  type: MouseParams["type"],
  point: MousePoint,
  button: MouseParams["button"],
  event: MouseEvent,
): MouseParams {
  return {
    type,
    ...point,
    button,
    buttons: event.buttons,
    modifiers: modifiers(event),
    clickCount: type === "mouseMove" ? 0 : event.detail,
  };
}

export function releaseMouseParams(point: MousePoint, button: MouseParams["button"]): MouseParams {
  return { type: "mouseUp", ...point, button, buttons: 0, clickCount: 0 };
}

export function keyParams(event: KeyboardEvent, direction: "down" | "up"): KeyParams {
  const text = direction === "down" ? keyText(event) : undefined;
  const virtualKeyCode = windowsVirtualKeyCode(event);
  return {
    type: direction === "up" ? "keyUp" : text === undefined ? "rawKeyDown" : "keyDown",
    key: event.key,
    code: event.code,
    text,
    unmodifiedText: text,
    modifiers: modifiers(event),
    autoRepeat: event.repeat,
    windowsVirtualKeyCode: virtualKeyCode,
    nativeVirtualKeyCode: virtualKeyCode,
    location: event.location,
    isKeypad: event.location === KeyboardEvent.DOM_KEY_LOCATION_NUMPAD,
    isSystemKey: event.altKey,
  };
}

export function isClipboardShortcut(event: KeyboardEvent, key: "c" | "v"): boolean {
  return (event.ctrlKey || event.metaKey) && !event.altKey && event.key.toLowerCase() === key;
}

function modifiers(event: MouseEvent | KeyboardEvent): number {
  return (
    Number(event.altKey) +
    Number(event.ctrlKey) * 2 +
    Number(event.metaKey) * 4 +
    Number(event.shiftKey) * 8
  );
}

function keyText(event: KeyboardEvent): string | undefined {
  const hasAccelerator = event.altKey || event.ctrlKey || event.metaKey;
  if (event.key === "Enter" && !hasAccelerator) return "\r";
  if (event.key.length === 1 && (!hasAccelerator || event.getModifierState("AltGraph"))) {
    return event.key;
  }
  return undefined;
}

const VIRTUAL_KEY: Readonly<Record<string, number>> = {
  Backspace: 8,
  Tab: 9,
  Enter: 13,
  NumpadEnter: 13,
  ShiftLeft: 16,
  ShiftRight: 16,
  ControlLeft: 17,
  ControlRight: 17,
  AltLeft: 18,
  AltRight: 18,
  Pause: 19,
  CapsLock: 20,
  Escape: 27,
  Space: 32,
  PageUp: 33,
  PageDown: 34,
  End: 35,
  Home: 36,
  ArrowLeft: 37,
  ArrowUp: 38,
  ArrowRight: 39,
  ArrowDown: 40,
  Insert: 45,
  Delete: 46,
  MetaLeft: 91,
  MetaRight: 92,
  ContextMenu: 93,
  NumpadMultiply: 106,
  NumpadAdd: 107,
  NumpadSubtract: 109,
  NumpadDecimal: 110,
  NumpadDivide: 111,
  NumLock: 144,
  ScrollLock: 145,
  Semicolon: 186,
  Equal: 187,
  Comma: 188,
  Minus: 189,
  Period: 190,
  Slash: 191,
  Backquote: 192,
  BracketLeft: 219,
  Backslash: 220,
  BracketRight: 221,
  Quote: 222,
};

function windowsVirtualKeyCode(event: KeyboardEvent): number {
  const mapped = VIRTUAL_KEY[event.code];
  if (mapped !== undefined) return mapped;
  if (/^Key[A-Z]$/.test(event.code)) return event.code.charCodeAt(3);
  if (/^Digit[0-9]$/.test(event.code)) return event.code.charCodeAt(5);
  if (/^Numpad[0-9]$/.test(event.code)) return 96 + Number(event.code.at(-1));
  if (/^F(?:[1-9]|1[0-9]|2[0-4])$/.test(event.code)) return 111 + Number(event.code.slice(1));
  return event.keyCode;
}
