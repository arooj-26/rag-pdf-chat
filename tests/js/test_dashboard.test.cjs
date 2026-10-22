const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

function page(selected = ["document-1"]) {
  const make = () => ({textContent:"", children:[], attributes:{}, disabled:false,
    append(child) { this.children.push(child); },
    replaceChildren(...children) { this.children = children; },
    setAttribute(key, value) { this.attributes[key] = value; },
    removeAttribute(key) { delete this.attributes[key]; },
    scrollIntoView() {},
  });
  const elements = {};
  for (const id of ["library", "library-filter", "status", "study-status", "search-form", "study-form", "study-results", "saved", "kind", "topic", "count", "difficulty", "style", "evaluation-button"]) elements[id] = make();
  Object.assign(elements.kind, {value:"flashcards"});
  Object.assign(elements.topic, {value:"main concepts"});
  Object.assign(elements.count, {value:"5"});
  Object.assign(elements.difficulty, {value:"medium"});
  Object.assign(elements.style, {value:"question-answer"});
  const button = make(); button.textContent = "Generate from selected documents";
  elements["study-form"].querySelector = () => button;
  const requests = [];
  let complete;
  const pending = new Promise(resolve => {complete = resolve;});
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../../static/js/dashboard.js"), "utf8"), {
    document: {getElementById:id=>elements[id], createElement:make, querySelectorAll:()=>selected.map(value=>({value}))},
    window: {researchAuth: {ready: Promise.resolve(null)}},
    fetch: async (url, options) => {
      requests.push({url,options});
      return url === "/api/learning" ? {ok:true,json:async()=>[]} : pending;
    },
  });
  return {elements, button, requests, complete};
}

test("flashcards submit selected sources and display loading and generated cards", async () => {
  const state = page();
  const operation = state.elements["study-form"].onsubmit({preventDefault(){},target:state.elements["study-form"]});
  assert.equal(state.button.disabled, true);
  assert.match(state.elements["study-status"].textContent, /Generating flashcards/i);
  state.complete({ok:true,json:async()=>({id:"material-1",kind:"flashcards",content:{title:"Study",cards:[{front:"Question",back:"Answer",evidence:{source_number:1,quote:"Supporting information"}}]},sources:[]})});
  await operation;
  assert.equal(state.button.disabled, false);
  assert.equal(JSON.parse(state.requests[0].options.body).document_ids[0], "document-1");
  assert.match(state.elements["study-status"].textContent, /ready/i);
  const text = node => node.textContent + node.children.map(text).join(" ");
  assert.match(text(state.elements["study-results"]), /Reveal answer/);
  assert.match(text(state.elements["study-results"]), /Answer/);
});

test("generation errors appear beside the study form", async () => {
  const state = page();
  const operation = state.elements["study-form"].onsubmit({preventDefault(){},target:state.elements["study-form"]});
  state.complete({ok:false,json:async()=>({detail:"Could not validate source evidence."})});
  await operation;
  assert.match(state.elements["study-status"].textContent, /Could not validate source evidence/);
  assert.equal(state.elements["study-status"].attributes.role, "alert");
  assert.equal(state.button.disabled, false);
});

test("missing selection is explained beside the Generate button", async () => {
  const state = page([]);
  await state.elements["study-form"].onsubmit({preventDefault(){},target:state.elements["study-form"]});
  assert.match(state.elements["study-status"].textContent, /Select at least one ready document/);
  assert.equal(state.requests.length, 0);
});
