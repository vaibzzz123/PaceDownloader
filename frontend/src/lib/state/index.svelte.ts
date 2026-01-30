function loadState() {
  if (typeof localStorage === 'undefined') return {};
  try {
    const saved = localStorage.getItem('app-state');
    return saved ? JSON.parse(saved) : {};
  } catch {
    return {};
  }
}

const defaults = {
  darkMode: false,
  spoilerMode: false
};

export const state = $state({ ...defaults, ...loadState() });

$effect.root(() => {
  $effect(() => {
    // Access each property so Svelte tracks them
    const snapshot = { darkMode: state.darkMode, spoilerMode: state.spoilerMode };
    localStorage.setItem('app-state', JSON.stringify(snapshot));
  });
});