(function () {
  const EDGE = 12;
  const GAP = 8;

  function positionPopover(anchor) {
    const popover = anchor && anchor.querySelector('.context-help-popover');
    if (!anchor || !popover) return;

    const anchorRect = anchor.getBoundingClientRect();
    const previousVisibility = popover.style.visibility;
    const previousOpacity = popover.style.opacity;
    const previousPointerEvents = popover.style.pointerEvents;

    popover.style.visibility = 'hidden';
    popover.style.opacity = '0';
    popover.style.pointerEvents = 'none';
    popover.classList.add('context-help-measuring');

    const popRect = popover.getBoundingClientRect();
    const width = Math.min(popRect.width || 340, window.innerWidth - EDGE * 2);
    const height = popRect.height || 260;

    let left = anchorRect.left + anchorRect.width / 2 - width / 2;
    left = Math.max(EDGE, Math.min(left, window.innerWidth - width - EDGE));

    let top = anchorRect.bottom + GAP;
    if (top + height > window.innerHeight - EDGE) {
      top = anchorRect.top - height - GAP;
    }
    top = Math.max(EDGE, Math.min(top, window.innerHeight - height - EDGE));

    popover.style.setProperty('--context-help-left', `${Math.round(left)}px`);
    popover.style.setProperty('--context-help-top', `${Math.round(top)}px`);
    popover.style.setProperty('--context-help-width', `${Math.round(width)}px`);

    popover.classList.remove('context-help-measuring');
    popover.style.visibility = previousVisibility;
    popover.style.opacity = previousOpacity;
    popover.style.pointerEvents = previousPointerEvents;
  }

  function placeFromEvent(event) {
    const anchor = event.target && event.target.closest
      ? event.target.closest('.context-help-anchor')
      : null;
    if (anchor) positionPopover(anchor);
  }

  document.addEventListener('pointerenter', placeFromEvent, true);
  document.addEventListener('focusin', placeFromEvent, true);
  document.addEventListener('touchstart', function (event) {
    const anchor = event.target && event.target.closest
      ? event.target.closest('.context-help-anchor')
      : null;
    if (!anchor) return;
    positionPopover(anchor);
    if (typeof anchor.focus === 'function') {
      anchor.focus({ preventScroll: true });
    }
  }, { passive: true, capture: true });

  window.addEventListener('resize', function () {
    const active = document.querySelector('.context-help-anchor:hover, .context-help-anchor:focus-within');
    if (active) positionPopover(active);
  });

  window.addEventListener('scroll', function () {
    const active = document.querySelector('.context-help-anchor:hover, .context-help-anchor:focus-within');
    if (active) positionPopover(active);
  }, true);
})();
