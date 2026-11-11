/* Regression: an anonymous guest must be allowed to visit /login and use Google. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('login-ui.js', 'utf8');

async function scenario(role) {
  let redirected = null;
  let label = 'Continue with Google';
  const button = {
    value: null,
    getAttribute() {return null;},
    setAttribute() {},
    removeAttribute() {},
    addEventListener() {},
    querySelector() {return {set textContent(v) {label = v;}};}
  };
  const trial = {querySelector(selector) {return {set textContent(v) {}};}};
  const error = {textContent: '', hidden: true};
  const context = {
    document: {
      getElementById(id) {return id === 'googleLogin' ? button : error;},
      querySelector() {return trial;}
    },
    window: {
      addEventListener() {},
      VelaurAccount: {
        ready: Promise.resolve(),
        profile: role ? {user: {role}} : null,
        request: async () => ({})
      }
    },
    URLSearchParams,
    location: {search: '', replace(to) {redirected = to;}}
  };
  vm.runInNewContext(source, context);
  await new Promise(resolve => setImmediate(resolve));
  return redirected;
}

(async () => {
  assert.equal(await scenario('guest'), null, 'guest must remain on Google sign-in');
  assert.equal(await scenario(null), null, 'unsigned visitor must remain on sign-in');
  assert.equal(await scenario('user'), '/dashboard', 'signed-in member should go to dashboard');
  console.log('Login redirect regression tests passed.');
})().catch(error => {console.error(error); process.exitCode=1;});
