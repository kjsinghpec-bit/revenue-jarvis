const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/revenue_jarvis/web/app.js', 'utf8');

test('old answer citation opens that answer evidence after a newer answer', () => {
  const messages = [];
  const modal = { classList: { remove() {} } };
  const elements = { transcript: { append(d) { messages.push(d); } }, modal,
    modalTitle: {}, modalReview: {}, modalText: {}, modalImg: { style: {}, removeAttribute() { delete this.src; } } };
  const context = vm.createContext({
    $: id => elements[id], status: { page_images: true }, scrollDown() {},
    esc: s => String(s), lastEvidence: [{ sid: 'B1', text: 'NEW PAGE', pdf_page: 20, citation: 'page 20', source_type: 'book' }],
    document: { createElement() { return {
      dataset: {},
      querySelectorAll() { return [...this.innerHTML.matchAll(/data-sid="([^"]+)"/g)].map(m => ({ dataset: { sid: m[1] } })); },
    }; } },
  });
  // Execute the production rendering/click functions with only DOM adapters.
  vm.runInContext(source.slice(source.indexOf('function ocrLabel'), source.indexOf('function addUser')), context);
  vm.runInContext(source.slice(source.indexOf('function addJarvis'), source.indexOf('function scrollDown')), context);
  vm.runInContext(source.slice(source.indexOf('async function openEvidence'), source.indexOf('$("closeModal")')), context);
  context.document.createElement = () => {
    const buttons = [];
    return { dataset: {}, set innerHTML(html) { this.html = html; buttons.push(...[...html.matchAll(/data-sid="([^"]+)"/g)].map(m => ({ dataset: { sid: m[1] } }))); },
      querySelectorAll() { return buttons; }, buttons };
  };
  context.addJarvis({ answer_id: 'old', spoken: 'Old answer', claims: [{ text: 'Old claim', source_ids: ['B1'] }],
    evidence: [{ sid: 'B1', text: 'OLD PAGE', pdf_page: 10, citation: 'page 10', source_type: 'book' }] });
  messages[0].buttons[0].onclick();
  assert.equal(elements.modalText.textContent, 'OLD PAGE');
  assert.equal(elements.modalImg.src, '/api/page/10.png');
  assert.match(elements.modalReview.textContent, /unverified/);
  messages[0].buttons[1].onclick();  // scan control also keeps the old answer's identity
  assert.equal(elements.modalImg.src, '/api/page/10.png');
});
