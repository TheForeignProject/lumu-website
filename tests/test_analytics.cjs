const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { test } = require('node:test');
const code = () => fs.readFileSync(require('node:path').join(__dirname, '../site/lumu-analytics.js'), 'utf8');

function setup() {
  const events = [], timers = [];
  const window = { location: { href: 'https://lumu.sg/' },
    gtag: (...args) => events.push(args), setTimeout: fn => timers.push(fn) };
  const document = { currentScript: { getAttribute: () => '["dh"]' } };
  const context = vm.createContext({ window, document });
  vm.runInContext(code(), context);
  let scene = 'home';
  const api = { currentSceneName: () => scene };
  const notify = (type, doc = api) => window.HYPE_eventListeners.filter(l => l.type === type).forEach(l => l.callback(doc));
  notify('HypeDocumentLoad');
  return { events, window, context, notify, flush: () => { while (timers.length) timers.shift()(); },
    load: name => { scene = name; window.location.href = 'https://lumu.sg/#' + name; notify('HypeSceneLoad'); } };
}

test('scene event observes settled URL and does not send manual page views', () => {
  const s = setup();
  s.load('menu');
  assert.equal(s.events.length, 0);
  s.flush();
  assert.equal(s.events.length, 1);
  assert.equal(s.events[0][0], 'event');
  assert.equal(s.events[0][1], 'hype_scene_view');
  assert.equal(s.events[0][2].scene_name, 'menu');
  assert.equal(s.events[0][2].page_location, 'https://lumu.sg/#menu');
});

test('repeat scene and overlay dismissal do not inflate scene views; return navigation counts', () => {
  const s = setup();
  for (const name of ['home', 'home', 'dh', 'home', 'menu', 'home']) { s.load(name); s.flush(); }
  assert.deepEqual(s.events.map(e => e[2].scene_name), ['home', 'menu', 'home']);
});

test('another Hype document and repeated installation do not create duplicate events', () => {
  const s = setup();
  vm.runInContext(code(), s.context);
  s.notify('HypeSceneLoad', { currentSceneName: () => 'widget' });
  s.load('home'); s.flush();
  assert.equal(s.events.length, 1);
  delete s.window.gtag;
  s.load('menu');
  assert.doesNotThrow(s.flush);
});
