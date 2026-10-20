/* Scene analytics, maintained independently of the designer's Hype export. */
(function () {
  'use strict';
  if (window.__lumuSceneAnalytics) return;
  window.__lumuSceneAnalytics = true;

  var excluded = JSON.parse(document.currentScript.getAttribute('data-hype-scene-exclude') || '[]');
  var hype = null;
  var lastScene = null;
  var listeners = window.HYPE_eventListeners = window.HYPE_eventListeners || [];
  listeners.push({ type: 'HypeDocumentLoad', callback: function (api) {
    if (!hype) hype = api;
  } });
  listeners.push({ type: 'HypeSceneLoad', callback: function (api) {
    if (api !== hype) return;
    // Scene-load actions update the hash after Hype invokes its listeners.
    window.setTimeout(function () {
      var scene = api.currentSceneName();
      if (excluded.indexOf(scene) >= 0 || scene === lastScene || typeof window.gtag !== 'function') return;
      lastScene = scene;
      // A separate event avoids duplicating Google's automatic page_view.
      window.gtag('event', 'hype_scene_view', {
        scene_name: scene,
        page_location: window.location.href
      });
    }, 0);
  } });
})();
