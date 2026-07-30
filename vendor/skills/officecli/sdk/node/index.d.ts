// Type definitions for @officecli/sdk

/** A single command in officecli's batch-item shape. `command` (or `op`) picks
 * the command, `props` becomes the property map, and every other key is
 * forwarded verbatim as a command argument. */
export interface BatchItem {
  command?: string;
  op?: string;
  path?: string;
  parent?: string;
  type?: string;
  index?: number | string;
  after?: string;
  before?: string;
  to?: string;
  selector?: string;
  props?: Record<string, unknown>;
  [key: string]: unknown;
}

/** Parsed result: the JSON envelope (object/array) for --json commands, or raw
 * text for content commands (view/raw/dump). */
export type Result = Record<string, unknown> | unknown[] | string;

export interface OpenOptions {
  /** CLI binary name or absolute path. Default "officecli". */
  binary?: string;
  /** Command-delivery timeout in ms (connect + retries); the reply read blocks. Default 30000. */
  timeoutMs?: number;
  /** Actively install/download the CLI if missing (bundled binary, then install.sh). Default true. */
  autoInstall?: boolean;
}

export interface BatchOptions {
  force?: boolean;
  stopOnError?: boolean;
  timeoutMs?: number;
}

/** Raised on transport/process failure (could not reach the resident). Business
 * outcomes are NOT errors — they live in the returned envelope's `success` field. */
export class OfficeCliError extends Error {
  code: number;
  constructor(code: number, msg: string);
}

/** A live handle to a resident serving one document. */
export class Document {
  readonly path: string;
  /** Forward ONE batch-shaped command; returns the parsed envelope or raw text. */
  send(item: BatchItem, asJson?: boolean, timeoutMs?: number): Promise<Result>;
  /** Forward a LIST of commands in one round-trip (the fast path for many writes). */
  batch(items: BatchItem[], options?: BatchOptions): Promise<Result>;
  /** True iff a resident is alive AND serving this file. */
  alive(timeoutMs?: number): Promise<boolean>;
  /** Stop the resident (flushes to disk on shutdown). */
  close(): Promise<Result>;
  [Symbol.asyncDispose](): Promise<void>;
}

/** Create a blank Office document and return a live handle. */
export function create(filePath: string, args?: string[], options?: OpenOptions): Promise<Document>;

/** Open an existing document and return a live handle. */
export function open(filePath: string, options?: OpenOptions): Promise<Document>;

/** Install the officecli CLI via its official installer (unix only). */
export function install(): void;

/** [main, ping] pipe addresses for a document path (debug helper). */
export function pipePaths(filePath: string): [string, string];
