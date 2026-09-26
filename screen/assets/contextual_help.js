(function () {
  'use strict';
  const EDGE = 12, GAP = 8, PORTAL_ID = 'context-help-portal';
  let activeAnchor = null, lastPointer = { x: -1, y: -1 };
  function portal() {
    let node = document.getElementById(PORTAL_ID);
    if (node) return node;
    node = document.createElement('div'); node.id = PORTAL_ID; node.className = 'context-help-portal';
    node.setAttribute('role', 'dialog'); node.setAttribute('aria-live', 'polite'); document.body.appendChild(node); return node;
  }
  function sourcePopover(anchor) { return anchor && anchor.querySelector(':scope > .context-help-popover'); }
  function position(anchor) {
    const layer = portal(); if (!anchor || !anchor.isConnected || !layer.classList.contains('context-help-portal-visible')) return;
    const rect = anchor.getBoundingClientRect(), width = Math.min(layer.offsetWidth || 340, window.innerWidth - EDGE * 2), height = layer.offsetHeight || 260;
    let left = Math.max(EDGE, Math.min(rect.left + rect.width / 2 - width / 2, window.innerWidth - width - EDGE));
    let top = rect.bottom + GAP; if (top + height > window.innerHeight - EDGE) top = rect.top - height - GAP;
    top = Math.max(EDGE, Math.min(top, window.innerHeight - height - EDGE));
    layer.style.left = `${Math.round(left)}px`; layer.style.top = `${Math.round(top)}px`; layer.style.width = `${Math.round(width)}px`;
  }
  function show(anchor) {
    const source = sourcePopover(anchor); if (!source) return; const layer = portal(); activeAnchor = anchor;
    layer.replaceChildren.apply(layer, Array.from(source.childNodes).map(child => child.cloneNode(true)));
    layer.classList.add('context-help-portal-visible'); anchor.setAttribute('aria-expanded', 'true'); position(anchor);
  }
  function hide() {
    const layer = portal(); if (activeAnchor && activeAnchor.isConnected) activeAnchor.setAttribute('aria-expanded', 'false');
    activeAnchor = null; layer.classList.remove('context-help-portal-visible');
  }
  function anchorFromPoint() {
    if (lastPointer.x < 0 || lastPointer.y < 0) return null; const node = document.elementFromPoint(lastPointer.x, lastPointer.y);
    return node && node.closest ? node.closest('.context-help-anchor') : null;
  }
  document.addEventListener('pointermove', event => { lastPointer = { x: event.clientX, y: event.clientY }; }, true);
  document.addEventListener('pointerover', event => { const anchor = event.target && event.target.closest ? event.target.closest('.context-help-anchor') : null; if (anchor) show(anchor); }, true);
  document.addEventListener('pointerout', event => {
    const anchor = event.target && event.target.closest ? event.target.closest('.context-help-anchor') : null;
    if (!anchor || anchor !== activeAnchor) return; const related = event.relatedTarget;
    if (related && (anchor.contains(related) || portal().contains(related))) return;
    window.setTimeout(() => { const replacement = anchorFromPoint(); if (replacement) show(replacement); else if (!portal().matches(':hover')) hide(); }, 0);
  }, true);
  document.addEventListener('focusin', event => { const anchor = event.target && event.target.closest ? event.target.closest('.context-help-anchor') : null; if (anchor) show(anchor); }, true);
  document.addEventListener('focusout', event => { if (!activeAnchor || (event.relatedTarget && portal().contains(event.relatedTarget))) return; window.setTimeout(() => { const focused = document.activeElement; if (!focused || !focused.closest || !focused.closest('.context-help-anchor')) hide(); }, 0); }, true);
  document.addEventListener('touchstart', event => { const anchor = event.target && event.target.closest ? event.target.closest('.context-help-anchor') : null; if (anchor) { event.preventDefault(); if (activeAnchor === anchor && portal().classList.contains('context-help-portal-visible')) hide(); else show(anchor); return; } if (!portal().contains(event.target)) hide(); }, { passive: false, capture: true });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') hide(); });
  window.addEventListener('resize', () => position(activeAnchor)); window.addEventListener('scroll', () => position(activeAnchor), true);
  new MutationObserver(() => { if (!activeAnchor || activeAnchor.isConnected) return; const replacement = anchorFromPoint(); if (replacement) { activeAnchor = replacement; replacement.setAttribute('aria-expanded', 'true'); position(replacement); } }).observe(document.documentElement, { childList: true, subtree: true });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', portal, { once: true }); else portal();
})();
