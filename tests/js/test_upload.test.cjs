const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

// Model the browser's live FileList: clearing the input (or returning from
// a drop event) removes access to the files unless they were copied first.
function uploadPage() {
  const listeners = new Map();
  const selectedFiles = [];
  const requests = [];
  const toasts = [];
  let finishAuthentication;
  const ready = new Promise(resolve => { finishAuthentication = resolve; });
  const element = id => ({
    files: selectedFiles,
    classList: {add() {}, remove() {}},
    addEventListener(event, callback) { listeners.set(`${id}:${event}`, callback); },
    prepend() {},
    querySelector() { return {style: {}}; },
    click() {},
    set value(value) { if (value === "") selectedFiles.length = 0; },
  });
  const elements = Object.fromEntries(["dropzone", "file-input", "upload-queue", "browse-btn"].map(id => [id, element(id)]));
  const sandbox = {
    document: {
      getElementById(id) { return elements[id]; },
      createElement() { return element("created"); },
    },
    window: {
      researchAuth: {ready, csrf: () => "test-csrf"},
      PDFChatToast: {show(message) { toasts.push(message); }},
    },
    FormData: class {
      constructor() { this.entries = []; }
      append(key, file) { this.entries.push({key, file}); }
    },
    XMLHttpRequest: class {
      constructor() { this.upload = {addEventListener() {}}; }
      open(method, url) { this.method = method; this.url = url; }
      setRequestHeader(name, value) { this[name] = value; }
      send(body) { requests.push({method: this.method, url: this.url, body}); }
    },
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../../static/js/upload.js"), "utf8"), sandbox);
  return {listeners, selectedFiles, requests, toasts, finishAuthentication};
}

async function flush() { await new Promise(resolve => setImmediate(resolve)); }

for (const name of ["research.pdf", "RESEARCH.PDF", "notes.docx", "notes.md", "notes.txt"]) {
  test(`file picker preserves ${name} while authentication is pending`, async () => {
    const page = uploadPage();
    const file = {name, size: 150};
    page.selectedFiles.push(file);
    page.listeners.get("file-input:change")();
    assert.equal(page.selectedFiles.length, 0, "Input is cleared so the same file can be selected again");
    page.finishAuthentication();
    await flush();
    assert.equal(page.requests.length, 1, "Supported file must reach the upload API");
    assert.equal(page.requests[0].body.entries[0].file, file);
    assert.equal(page.toasts.length, 0);
  });
}

test("dragged PDF is copied before the drop event loses access to its files", async () => {
  const page = uploadPage();
  const file = {name: "dropped.pdf", size: 150};
  const dropFiles = [file];
  page.listeners.get("dropzone:drop")({dataTransfer: {files: dropFiles}});
  dropFiles.length = 0;
  page.finishAuthentication();
  await flush();
  assert.equal(page.requests.length, 1);
  assert.equal(page.requests[0].body.entries[0].file, file);
});

test("unsupported extension still shows a validation message", async () => {
  const page = uploadPage();
  page.selectedFiles.push({name: "program.exe", size: 150});
  page.listeners.get("file-input:change")();
  page.finishAuthentication();
  await flush();
  assert.equal(page.requests.length, 0);
  assert.match(page.toasts[0], /Select PDF, DOCX, TXT or Markdown/);
});
