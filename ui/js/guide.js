/* Onboarding intro sheet (ui/guide.py): Esc or Enter closes it.
 *
 * Closing always goes through the sheet's native button, so the step is
 * marked as seen on the server. Keys pressed inside a text field are left
 * alone. While the sheet is up, ui/js/swipe.js ignores the arrow keys.
 */
(function () {
  if (window.__aaGuide) return;
  window.__aaGuide = 1;
  window.addEventListener('keydown', e => {
    if (e.key !== 'Escape' && e.key !== 'Enter') return;
    const b = document.querySelector('.st-key-guide-ok button');
    if (!b || e.repeat) return;
    if (e.target.closest && e.target.closest('input,textarea,[contenteditable="true"]')) return;
    e.preventDefault(); e.stopImmediatePropagation();
    b.click();
  }, true);
})();
